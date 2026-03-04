from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseBadRequest
from django.urls import reverse
from decimal import Decimal
from datetime import timedelta
from .models import Package, BusinessSubscription, SubscriptionPayment
from django.core.paginator import Paginator
from django.db.models import Q
from subscription.models import SubscriptionPayment, BusinessSubscription


# Reuse eSewa from restaurant
from restaurant.esewa_utils import (
    prepare_esewa_form_data,
    generate_transaction_uuid,
    verify_esewa_payment,
)


# -----------------------------
# Helpers: role checks
# -----------------------------
def _require_role(request, role: str, redirect_name: str = "login"):
    if not request.user.is_authenticated:
        return False, redirect(redirect_name)
    if request.user.role != role:
        return False, redirect(redirect_name)
    return True, None


def _activate_subscription(subscription: BusinessSubscription, payment: SubscriptionPayment):
    """
    Activate subscription + mark payment verified.
    """
    # Mark old current subscriptions not current
    BusinessSubscription.objects.filter(
        business=subscription.business,
        is_current=True
    ).exclude(id=subscription.id).update(is_current=False)

    now = timezone.now()

    subscription.status = "ACTIVE"
    subscription.is_current = True
    subscription.start_date = now
    subscription.end_date = now + timedelta(days=30 * subscription.package.duration_months)
    subscription.save()

    payment.status = "VERIFIED"
    payment.paid_at = now
    payment.save()


# ============================================================
# SUPERADMIN: PACKAGE CRUD
# ============================================================

@login_required
def package_list(request):
    ok, resp = _require_role(request, "SUPERADMIN", redirect_name="login")
    if not ok:
        return resp

    packages = Package.objects.all().order_by("-created_at")
    return render(request, "subscription/package_list.html", {"packages": packages})


@login_required
def package_create(request):
    ok, resp = _require_role(request, "SUPERADMIN", redirect_name="login")
    if not ok:
        return resp

    if request.method == "POST":
        Package.objects.create(
            name=request.POST.get("name", "").strip(),
            duration_months=int(request.POST.get("duration_months") or 1),
            max_users=int(request.POST.get("max_users") or 1),
            price=Decimal(request.POST.get("price") or "0"),
            is_active=True if request.POST.get("is_active") else False
        )
        messages.success(request, "Package created.")
        return redirect("package_list")

    return render(request, "subscription/package_form.html")


@login_required
def package_update(request, pk):
    ok, resp = _require_role(request, "SUPERADMIN", redirect_name="login")
    if not ok:
        return resp

    package = get_object_or_404(Package, pk=pk)

    if request.method == "POST":
        package.name = request.POST.get("name", "").strip()
        package.duration_months = int(request.POST.get("duration_months") or package.duration_months)
        package.max_users = int(request.POST.get("max_users") or package.max_users)
        package.price = Decimal(request.POST.get("price") or package.price)
        package.is_active = True if request.POST.get("is_active") else False
        package.save()

        messages.success(request, "Package updated.")
        return redirect("package_list")

    return render(request, "subscription/package_form.html", {"package": package})


@login_required
def package_delete(request, pk):
    ok, resp = _require_role(request, "SUPERADMIN", redirect_name="login")
    if not ok:
        return resp

    package = get_object_or_404(Package, pk=pk)
    package.delete()
    messages.success(request, "Package deleted.")
    return redirect("package_list")


# ============================================================
# OWNER: VIEW PACKAGES + CHOOSE PACKAGE
# ============================================================

@login_required
def business_package_list(request):
    ok, resp = _require_role(request, "OWNER", redirect_name="owner_dashboard")
    if not ok:
        return resp

    packages = Package.objects.filter(is_active=True).order_by("price")

    current_sub = BusinessSubscription.objects.filter(
        business=request.user.business,
        status="ACTIVE",
        is_current=True
    ).select_related("package").first()

    return render(request, "subscription/business_package_list.html", {
        "packages": packages,
        "current_sub": current_sub
    })


@login_required
def choose_package(request, pk):
    ok, resp = _require_role(request, "OWNER", redirect_name="owner_dashboard")
    if not ok:
        return resp

    business = request.user.business
    if not business:
        messages.error(request, "Business not linked to your account.")
        return redirect("owner_dashboard")

    package = get_object_or_404(Package, pk=pk, is_active=True)

    # Deactivate old "current" subscription
    BusinessSubscription.objects.filter(
        business=business,
        is_current=True
    ).update(is_current=False)

    # Cancel old pending payments
    SubscriptionPayment.objects.filter(
        subscription__business=business,
        status="PENDING"
    ).update(status="CANCELLED")  # make sure CANCELLED exists in model choices

    # Create new pending subscription
    subscription = BusinessSubscription.objects.create(
        business=business,
        package=package,
        status="PENDING",
        is_current=True
    )

    # Create payment record with UUID
    txn = generate_transaction_uuid()
    SubscriptionPayment.objects.create(
        subscription=subscription,
        amount=package.price,
        method="ESEWA",
        transaction_ref=txn,
        status="PENDING",
    )

    return redirect("payment_page", subscription.id)


# ============================================================
# OWNER: PAYMENT PAGE (posts to eSewa)
# ============================================================

@login_required
def payment_page(request, subscription_id):
    ok, resp = _require_role(request, "OWNER", redirect_name="owner_dashboard")
    if not ok:
        return resp

    subscription = get_object_or_404(BusinessSubscription, id=subscription_id)

    # ensure owner owns the business
    if subscription.business != request.user.business:
        return redirect("owner_dashboard")

    payment = SubscriptionPayment.objects.filter(subscription=subscription).order_by("-id").first()
    if not payment:
        return HttpResponseBadRequest("Payment record not found.")

    success_url = request.build_absolute_uri(reverse("esewa_success"))
    failure_url = request.build_absolute_uri(reverse("esewa_failure"))

    form_data = prepare_esewa_form_data(
        total_amount=subscription.package.price,
        transaction_uuid=payment.transaction_ref,
        success_url=success_url,
        failure_url=failure_url,
        product_code="EPAYTEST",
    )

    return render(request, "subscription/payment_page.html", {
        "subscription": subscription,
        "payment": payment,
        "form_data": form_data,
    })


# ============================================================
# ESEWA CALLBACKS (SUCCESS / FAILURE)
# ============================================================

def esewa_success(request):
    """
    eSewa redirects here. We must VERIFY server-to-server before activating.
    Expected v2: it may send data (base64 JSON) OR transaction_uuid in query.
    We'll try both.
    """
    data = request.GET.get("data") or request.POST.get("data")

    txn = None
    total_amount = None

    if data:
        try:
            import json, base64
            decoded_json_str = base64.b64decode(data).decode("utf-8")
            payload = json.loads(decoded_json_str)
            txn = payload.get("transaction_uuid")
            total_amount = payload.get("total_amount")
        except Exception:
            pass

    # fallback (some redirects may include these)
    txn = txn or request.GET.get("transaction_uuid") or request.GET.get("pid") or request.GET.get("oid")

    if not txn:
        return HttpResponseBadRequest("Missing transaction id")

    payment = SubscriptionPayment.objects.filter(transaction_ref=txn).select_related("subscription__package").first()
    if not payment:
        return HttpResponseBadRequest("Transaction not found")

    # already processed
    if payment.status == "VERIFIED":
        return render(request, "subscription/payment_success.html", {"subscription": payment.subscription})

    if payment.status != "PENDING":
        return render(request, "subscription/payment_failed.html", {"reason": f"Payment status: {payment.status}"})

    # verify from eSewa server
    verify_amount = total_amount or payment.amount
    verify_result = verify_esewa_payment(transaction_uuid=txn, total_amount=verify_amount, product_code="EPAYTEST")

    if not verify_result.get("success"):
        payment.status = "REJECTED"
        payment.save()
        return render(request, "subscription/payment_failed.html", {"reason": verify_result.get("message", "Verification failed")})

    esewa_data = verify_result.get("data", {})
    esewa_status = str(esewa_data.get("status", "")).upper()

    # Typically COMPLETE means success
    if esewa_status not in ["COMPLETE", "COMPLETED", "SUCCESS"]:
        payment.status = "REJECTED"
        payment.save()
        return render(request, "subscription/payment_failed.html", {"reason": f"eSewa status: {esewa_status}"})

    # Activate subscription
    _activate_subscription(payment.subscription, payment)

    return render(request, "subscription/payment_success.html", {"subscription": payment.subscription})


def esewa_failure(request):
    data = request.GET.get("data") or request.POST.get("data")

    txn = None
    if data:
        try:
            import json, base64
            decoded_json_str = base64.b64decode(data).decode("utf-8")
            payload = json.loads(decoded_json_str)
            txn = payload.get("transaction_uuid")
        except Exception:
            pass

    txn = txn or request.GET.get("transaction_uuid") or request.GET.get("pid") or request.GET.get("oid")

    if txn:
        payment = SubscriptionPayment.objects.filter(transaction_ref=txn).first()
        if payment and payment.status == "PENDING":
            payment.status = "REJECTED"
            payment.save()

    return render(request, "subscription/payment_failed.html")


# ============================================================
# SUPERADMIN: LIST SUBSCRIPTIONS + PAYMENTS
# ============================================================


@login_required
def subscription_list(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip().upper()  # ACTIVE / PENDING / EXPIRED / CANCELLED
    page_number = request.GET.get("page", 1)

    qs = BusinessSubscription.objects.select_related("business", "package").order_by("-created_at", "-id")

    # Status filter
    if status in ["ACTIVE", "PENDING", "EXPIRED", "CANCELLED"]:
        qs = qs.filter(status=status)

    # Search
    if q:
        qs = qs.filter(
            Q(business__business_name__icontains=q) |
            Q(package__name__icontains=q)
        )

    paginator = Paginator(qs, 10)  # 10 rows per page
    page_obj = paginator.get_page(page_number)

    return render(request, "subscription/subscription_list.html", {
        "page_obj": page_obj,
        "q": q,
        "status": status,
    })



@login_required
def payment_list(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip().upper()   # VERIFIED / PENDING / CANCELLED
    page_number = request.GET.get("page", 1)

    qs = SubscriptionPayment.objects.select_related(
        "subscription__business",
        "subscription__package"
    ).order_by("-paid_at", "-id")

    # Status filter
    if status in ["PENDING", "VERIFIED", "CANCELLED", "REJECTED"]:
        qs = qs.filter(status=status)

    # Search
    if q:
        qs = qs.filter(
            Q(subscription__business__business_name__icontains=q) |
            Q(transaction_ref__icontains=q)
        )

    paginator = Paginator(qs, 10)  # 10 rows per page
    page_obj = paginator.get_page(page_number)

    return render(request, "subscription/payment_list.html", {
        "page_obj": page_obj,
        "q": q,
        "status": status,
    })