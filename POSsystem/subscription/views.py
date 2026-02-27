from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Package, BusinessSubscription, SubscriptionPayment
from django.utils import timezone
from django.contrib import messages
import hmac
import hashlib
import base64
from django.conf import settings
from decimal import Decimal


# 🔹 LIST
@login_required
def package_list(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    packages = Package.objects.all()
    return render(request, "subscription/package_list.html", {"packages": packages})


# 🔹 CREATE
@login_required
def package_create(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    if request.method == "POST":
        Package.objects.create(
            name=request.POST.get("name"),
            duration_months=request.POST.get("duration_months"),
            max_users=request.POST.get("max_users"),
            price=request.POST.get("price"),
            is_active=True if request.POST.get("is_active") else False
        )
        return redirect("package_list")

    return render(request, "subscription/package_form.html")


# 🔹 UPDATE
@login_required
def package_update(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    package = get_object_or_404(Package, pk=pk)

    if request.method == "POST":
        package.name = request.POST.get("name")
        package.duration_months = request.POST.get("duration_months")
        package.max_users = request.POST.get("max_users")
        package.price = request.POST.get("price")
        package.is_active = True if request.POST.get("is_active") else False
        package.save()

        return redirect("package_list")

    return render(request, "subscription/package_form.html", {"package": package})


# 🔹 DELETE
@login_required
def package_delete(request, pk):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    package = get_object_or_404(Package, pk=pk)
    package.delete()
    return redirect("package_list")



@login_required
def business_package_list(request):
    if request.user.role != "OWNER":
        return redirect("owner_dashboard")

    packages = Package.objects.filter(is_active=True)

    return render(request, "subscription/business_package_list.html", {
        "packages": packages
    })

@login_required
def choose_package(request, pk):
    print("AUTH:", request.user.is_authenticated, "USER:", request.user)
    if request.user.role != "OWNER":
        return redirect("owner_dashboard")

    package = get_object_or_404(Package, pk=pk)
    business = request.user.business  # assuming OneToOne relation

    # deactivate old subscriptions
    BusinessSubscription.objects.filter(
        business=business,
        is_current=True
    ).update(is_current=False)

    # ✅ cancel old pending payments
    SubscriptionPayment.objects.filter(
        subscription__business=business,
        status="PENDING"
    ).update(status="CANCELLED")

    # create new subscription
    subscription = BusinessSubscription.objects.create(
        business=business,
        package=package,
        start_date=timezone.now(),
        status="PENDING",
        is_current=True
    )

    # create payment record
    SubscriptionPayment.objects.create(
        subscription=subscription,
        amount=package.price,
        method="ONLINE",
        status="PENDING"
    )

    return redirect("payment_page", subscription.id)

@login_required
def payment_success(request, subscription_id):
    subscription = get_object_or_404(BusinessSubscription, id=subscription_id)

    if request.user.role != "OWNER":
        return redirect("owner_dashboard")

    if subscription.business != request.user.business:
        return redirect("owner_dashboard")

    # activate subscription
    subscription.status = "ACTIVE"
    subscription.start_date = timezone.now()
    subscription.save()

    payment = SubscriptionPayment.objects.filter(subscription=subscription).order_by("-id").first()
    payment.status = "VERIFIED"

    payment.transaction_ref = f"TXN-{subscription.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    payment.paid_at = timezone.now()
    payment.save()


    messages.success(request, "Payment Successful! Your subscription has been activated.")

    return redirect("owner_dashboard")

@login_required
def subscription_list(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    subscriptions = BusinessSubscription.objects.select_related(
        "business", "package"
    ).all()

    return render(request, "subscription/subscription_list.html", {
        "subscriptions": subscriptions
    })



def payment_page(request, subscription_id):

    subscription = get_object_or_404(BusinessSubscription, id=subscription_id)

    total_amount = format(subscription.package.price, ".2f")
    transaction_uuid = str(subscription.id)
    product_code = "EPAYTEST"

    signature = generate_esewa_signature(
        total_amount,
        transaction_uuid,
        product_code
    )

    return render(request, "subscription/payment_page.html", {
        "subscription": subscription,
        "total_amount": total_amount,
        "transaction_uuid": transaction_uuid,
        "product_code": product_code,
        "signature": signature,
    })

    




@login_required
def payment_list(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    payments = SubscriptionPayment.objects.select_related(
        "subscription__business",
        "subscription__package"
    ).order_by("-paid_at")

    return render(request, "subscription/payment_list.html", {
        "payments": payments
    })


def generate_esewa_signature(total_amount, transaction_uuid, product_code):

    secret_key = "8gBm/:&EnhH.1/q("

    message = (
        "total_amount=" + total_amount +
        ",transaction_uuid=" + transaction_uuid +
        ",product_code=" + product_code
    )

    hmac_sha256 = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    )

    signature = base64.b64encode(hmac_sha256.digest()).decode("utf-8")

    print("MESSAGE SENT TO ESEWA:", message)
    print("GENERATED SIGNATURE:", signature)

    return signature