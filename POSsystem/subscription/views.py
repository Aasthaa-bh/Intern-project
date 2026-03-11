from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Package, BusinessSubscription, SubscriptionPayment
from restaurant.esewa_utils import (
    prepare_esewa_form_data,
    generate_transaction_uuid,
    verify_esewa_payment,
    verify_esewa_response_signature,
    decode_esewa_callback_data,
)


# -----------------------------
# Helpers
# -----------------------------
def _require_role(request, role: str, redirect_name: str = "login"):
    if not request.user.is_authenticated:
        return False, redirect(redirect_name)
    if request.user.role != role:
        return False, redirect(redirect_name)
    return True, None


def _activate_subscription(subscription: BusinessSubscription, payment: SubscriptionPayment):
    """
    Activate current subscription and mark payment verified.
    """
    BusinessSubscription.objects.filter(
        business=subscription.business,
        is_current=True
    ).exclude(id=subscription.id).update(is_current=False)

    now = timezone.now()

    subscription.status = "ACTIVE"
    subscription.is_current = True
    subscription.start_date = now
    subscription.end_date = now + timedelta(days=30 * subscription.package.duration_months)
    subscription.save(update_fields=["status", "is_current", "start_date", "end_date"])

    payment.status = "VERIFIED"
    payment.paid_at = now
    payment.save(update_fields=["status", "paid_at"])


def _safe_decimal(value, default="0.00"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


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
            max_tables=int(request.POST.get("max_tables") or 1),   
            price=Decimal(request.POST.get("price") or "0"),
            is_active=True if request.POST.get("is_active") else False,
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
        package.max_tables = int(request.POST.get("max_tables") or package.max_tables)  

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

    business = getattr(request.user, "business", None)
    if not business:
        messages.error(request, "Business not linked to your account.")
        return redirect("owner_dashboard")

    packages = Package.objects.filter(is_active=True).order_by("price")

    current_sub = BusinessSubscription.objects.filter(
        business=business,
        status="ACTIVE",
        is_current=True
    ).select_related("package").first()

    return render(request, "subscription/business_package_list.html", {
        "packages": packages,
        "current_sub": current_sub,
    })


@login_required
def choose_package(request, pk):
    ok, resp = _require_role(request, "OWNER", redirect_name="owner_dashboard")
    if not ok:
        return resp

    business = getattr(request.user, "business", None)
    if not business:
        messages.error(request, "Business not linked to your account.")
        return redirect("owner_dashboard")

    package = get_object_or_404(Package, pk=pk, is_active=True)

    # old current subscriptions -> not current
    BusinessSubscription.objects.filter(
        business=business,
        is_current=True
    ).update(is_current=False)

    # old pending payments -> cancelled
    SubscriptionPayment.objects.filter(
        subscription__business=business,
        status="PENDING"
    ).update(status="CANCELLED")

    # create pending subscription
    subscription = BusinessSubscription.objects.create(
        business=business,
        package=package,
        status="PENDING",
        is_current=True,
    )

    # create pending payment
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
# OWNER: PAYMENT PAGE
# ============================================================

@login_required
def payment_page(request, subscription_id):
    ok, resp = _require_role(request, "OWNER", redirect_name="owner_dashboard")
    if not ok:
        return resp

    subscription = get_object_or_404(
        BusinessSubscription.objects.select_related("package", "business"),
        id=subscription_id
    )

    business = getattr(request.user, "business", None)
    if not business or subscription.business != business:
        messages.error(request, "Unauthorized access.")
        return redirect("owner_dashboard")

    payment = SubscriptionPayment.objects.filter(
        subscription=subscription
    ).order_by("-id").first()

    if not payment:
        return HttpResponseBadRequest("Payment record not found.")

    if payment.status == "VERIFIED":
        return render(request, "subscription/payment_success.html", {
            "subscription": subscription
        })

    if payment.status != "PENDING":
        return render(request, "subscription/payment_failed.html", {
            "reason": f"Payment is already {payment.status}."
        })


    success_url = request.build_absolute_uri(reverse("esewa_success"))
    failure_url = request.build_absolute_uri(reverse("esewa_failure"))

    form_data = prepare_esewa_form_data(
        total_amount=payment.amount,
        transaction_uuid=payment.transaction_ref,
        success_url=success_url,
        failure_url=failure_url,
        product_code=settings.ESEWA_PRODUCT_CODE,
    )

    return render(request, "subscription/payment_page.html", {
        "subscription": subscription,
        "payment": payment,
        "form_data": form_data,
        "debug": settings.DEBUG,
    })


# ============================================================
# ESEWA CALLBACKS
# ============================================================

def esewa_success(request):
    """
    eSewa redirects here after a successful payment attempt.
    We still must verify the payload signature and confirm via status API.
    """
    encoded_data = request.GET.get("data") or request.POST.get("data")

    callback_payload = None
    txn = None
    callback_total_amount = None

    if encoded_data:
        try:
            callback_payload = decode_esewa_callback_data(encoded_data)
            txn = callback_payload.get("transaction_uuid")
            callback_total_amount = callback_payload.get("total_amount")
        except Exception:
            return HttpResponseBadRequest("Invalid eSewa callback data.")

    # fallback if data is absent
    txn = txn or request.GET.get("transaction_uuid") or request.GET.get("pid") or request.GET.get("oid")

    if not txn:
        return HttpResponseBadRequest("Missing transaction id.")

    payment = SubscriptionPayment.objects.filter(
        transaction_ref=txn
    ).select_related("subscription__package", "subscription__business").first()

    if not payment:
        return HttpResponseBadRequest("Transaction not found.")

    # already completed previously
    if payment.status == "VERIFIED":
        return render(request, "subscription/payment_success.html", {
            "subscription": payment.subscription
        })

    # if not pending, don't reactivate
    if payment.status != "PENDING":
        return render(request, "subscription/payment_failed.html", {
            "reason": f"Payment status: {payment.status}"
        })

    # 1. verify callback signature if callback payload exists
    if callback_payload:
        is_valid_signature = verify_esewa_response_signature(callback_payload)
        if not is_valid_signature:
            payment.status = "REJECTED"
            payment.save(update_fields=["status"])
            return render(request, "subscription/payment_failed.html", {
                "reason": "Invalid eSewa response signature."
            })

    # 2. verify with status check API
    verify_amount = _safe_decimal(callback_total_amount, default=str(payment.amount))
    verify_result = verify_esewa_payment(
        transaction_uuid=txn,
        total_amount=verify_amount,
        product_code=settings.ESEWA_PRODUCT_CODE,
    )

    if not verify_result.get("success"):
        payment.status = "REJECTED"
        payment.save(update_fields=["status"])
        return render(request, "subscription/payment_failed.html", {
            "reason": verify_result.get("message", "Verification failed.")
        })

    esewa_data = verify_result.get("data", {})
    esewa_status = str(esewa_data.get("status", "")).upper()
    esewa_total = _safe_decimal(esewa_data.get("total_amount"), default=str(payment.amount))

    if esewa_status != "COMPLETE":
        payment.status = "REJECTED"
        payment.save(update_fields=["status"])
        return render(request, "subscription/payment_failed.html", {
            "reason": f"eSewa status: {esewa_status or 'UNKNOWN'}"
        })

    # 3. amount check
    if esewa_total != _safe_decimal(payment.amount):
        payment.status = "REJECTED"
        payment.save(update_fields=["status"])
        return render(request, "subscription/payment_failed.html", {
            "reason": "Amount mismatch detected."
        })

    # 4. activate
    _activate_subscription(payment.subscription, payment)

    return render(request, "subscription/payment_success.html", {
        "subscription": payment.subscription
    })


def esewa_failure(request):
    """
    eSewa redirects here on failure / cancel / pending-like failure.
    """
    encoded_data = request.GET.get("data") or request.POST.get("data")
    txn = None

    if encoded_data:
        try:
            payload = decode_esewa_callback_data(encoded_data)
            txn = payload.get("transaction_uuid")
        except Exception:
            txn = None

    txn = txn or request.GET.get("transaction_uuid") or request.GET.get("pid") or request.GET.get("oid")

    if txn:
        payment = SubscriptionPayment.objects.filter(transaction_ref=txn).first()
        if payment and payment.status == "PENDING":
            payment.status = "REJECTED"
            payment.save(update_fields=["status"])

    return render(request, "subscription/payment_failed.html", {
        "reason": "Payment failed or cancelled."
    })


# ============================================================
# SUPERADMIN: LIST SUBSCRIPTIONS + PAYMENTS
# ============================================================

@login_required
def subscription_list(request):
    ok, resp = _require_role(request, "SUPERADMIN", redirect_name="login")
    if not ok:
        return resp

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip().upper()
    page_number = request.GET.get("page", 1)

    qs = BusinessSubscription.objects.select_related(
        "business", "package"
    ).order_by("-created_at", "-id")

    if status in ["ACTIVE", "PENDING", "EXPIRED", "CANCELLED"]:
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(
            Q(business__business_name__icontains=q) |
            Q(package__name__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, "subscription/subscription_list.html", {
        "page_obj": page_obj,
        "q": q,
        "status": status,
    })


@login_required
def payment_list(request):
    ok, resp = _require_role(request, "SUPERADMIN", redirect_name="login")
    if not ok:
        return resp

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip().upper()
    page_number = request.GET.get("page", 1)

    qs = SubscriptionPayment.objects.select_related(
        "subscription__business",
        "subscription__package"
    ).order_by("-paid_at", "-id")

    if status in ["PENDING", "VERIFIED", "CANCELLED", "REJECTED"]:
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(
            Q(subscription__business__business_name__icontains=q) |
            Q(transaction_ref__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, "subscription/payment_list.html", {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "debug": settings.DEBUG,
    })








      


