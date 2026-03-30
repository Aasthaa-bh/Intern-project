from multiprocessing import context

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import get_user_model
from pos.models import Item, Category
from .models import BusinessRequest, Business
from restaurant.models import DiningTable
from .forms import BusinessRequestForm
import random
import string
from django.db import models
from django.db.models import Q
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings

from core.models import Business
from subscription.models import Package, BusinessSubscription
from subscription.utils import get_active_subscription, get_business_user_limit
from .utils import get_business_type_code



User = get_user_model()



def home_view(request):
    return render(request, "core/home.html")



def get_started_view(request):
    if request.method == "POST":
        form = BusinessRequestForm(request.POST, request.FILES)
        if form.is_valid():
            business_request = form.save(commit=False)
            business_request.status = "PENDING"
            business_request.save()

            messages.success(request, "Your request has been submitted successfully.")
            return redirect("get_started")
    else:
        form = BusinessRequestForm()

    return render(request, "core/get_started.html", {"form": form})




@login_required
def superadmin_dashboard(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    total_businesses = Business.objects.count()
    total_packages = Package.objects.count()
    total_subscriptions = BusinessSubscription.objects.count()
    active_subscriptions = BusinessSubscription.objects.filter(status="ACTIVE").count()

    return render(request, "core/superadmin_dashboard.html", {
        "total_businesses": total_businesses,
        "total_packages": total_packages,
        "total_subscriptions": total_subscriptions,
        "active_subscriptions": active_subscriptions,
    })


@login_required
def superadmin_requests(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "PENDING").strip().upper()

    qs = BusinessRequest.objects.all().order_by("-created_at")

    if status in ["PENDING", "APPROVED", "REJECTED"]:
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(
            Q(business_name__icontains=q) |
            Q(owner_name__icontains=q) |
            Q(email__icontains=q)
        )

    # TEMP DEBUG (watch your terminal)
    print("GET status =", status, "| Count =", qs.count())

    return render(request, "core/superadmin_requests.html", {
        "requests": qs,
        "q": q,
        "status": status,
    })


    
@login_required
def approve_request(request, request_id):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    business_request = get_object_or_404(BusinessRequest, id=request_id)

    if business_request.status != "PENDING":
        messages.warning(request, "This request has already been processed.")
        return redirect("superadmin_dashboard")

    try:
        with transaction.atomic():

            # Generate business code based on business type
            prefix = (business_request.business_type.code or "BUS").upper()

            last_business = Business.objects.filter(
                business_code__startswith=prefix
            ).order_by("-id").first()

            next_number = 1
            if last_business and last_business.business_code:
                try:
                    last_number = int(last_business.business_code.replace(prefix, ""))
                    next_number = last_number + 1
                except ValueError:
                    next_number = 1

            business_code = f"{prefix}{next_number:03d}"

            # 🔹 Create Business
            business = Business.objects.create(
                business_type=business_request.business_type,
                business_name=business_request.business_name,
                business_code=business_code,
                address=business_request.address,
                status="ACTIVE"
            )

            # 🔹 Generate temporary password
            temp_password = ''.join(
                random.choices(string.ascii_letters + string.digits, k=8)
            )

            # Generate clean username from email
            base_username = business_request.owner_name.split(" ")[0].lower()
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # 🔹 Create Owner user
            owner_user = User.objects.create_user(
                username=username,
                email=business_request.email,
                password=temp_password,
                role="OWNER",
                business=business,
                full_name=business_request.owner_name,
                phone_no=business_request.phone_no,
                is_first_login=True
            )

            # 🔹 Update request status
            business_request.status = "APPROVED"
            business_request.reviewed_by = request.user
            business_request.reviewed_at = timezone.now()
            business_request.save()

    except Exception as e:
        messages.error(request, f"Error approving request: {str(e)}")
        return redirect("superadmin_dashboard")

    # 🔥 SEND EMAIL
    subject = "Your FlexiPOS Business Account Has Been Approved"

    message = f"""
Hello {business_request.owner_name},

Congratulations! Your business has been approved.

Business Name: {business.business_name}
Business Code: {business.business_code}

Login Credentials:
Username: {username}
Temporary Password: {temp_password}

Please login and change your password immediately.

Login Here:
http://127.0.0.1:8000/login/

Thank you,
FlexiPOS Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [business_request.email],
        fail_silently=False,
    )

    messages.success(
        request,
        f"Business Approved Successfully! "
        f"Username: {username} | "
        f"Temporary Password: {temp_password}"
    )

    return redirect("superadmin_dashboard")
   
@login_required
def business_dashboard_router(request):
    user = request.user
    business = getattr(user, "business", None)

    if not business or not business.business_type:
        messages.error(request, "No business or business type assigned.")
        return redirect("login")

    business_type_code = (business.business_type.code or "").upper()

    # OWNER routing
    if user.role == "OWNER":
        if business_type_code == "REST":
            return redirect("owner_dashboard")   # current restaurant owner dashboard
        elif business_type_code == "CLTH":
            return redirect("clothing_owner_dashboard")
        elif business_type_code == "MART":
            return redirect("mart_owner_dashboard")
        else:
            return redirect("owner_dashboard")

    # CASHIER routing
    if user.role == "CASHIER":
        if business_type_code == "REST":
            return redirect("reception_dashboard")
        elif business_type_code == "CLTH":
            return redirect("clothing_cashier_dashboard")
        elif business_type_code == "MART":
            return redirect("mart_cashier_dashboard")
        else:
            return redirect("login")

    # Restaurant-only roles
    if user.role == "WAITER":
        if business_type_code == "REST":
            return redirect("waiter_dashboard")
        messages.error(request, "Waiter role is only available for restaurant business.")
        return redirect("login")

    if user.role == "KITCHEN":
        if business_type_code == "REST":
            return redirect("restaurant_kitchen_dashboard")
        messages.error(request, "Kitchen role is only available for restaurant business.")
        return redirect("login")

    return redirect("login")     
   
@login_required
def reject_request(request, request_id):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    business_request = get_object_or_404(BusinessRequest, id=request_id)

    # Do NOT allow rejecting already approved request
    if business_request.status == "APPROVED":
        messages.warning(request, "Approved request cannot be rejected.")
        return redirect("superadmin_dashboard")

    # ✅ If form submitted
    if request.method == "POST":
        rejection_reason = request.POST.get("reason")

        if not rejection_reason:
            messages.error(request, "Rejection reason is required.")
            return render(request, "core/reject_form.html", {"req": business_request})

        # Update status
        business_request.status = "REJECTED"
        business_request.reviewed_by = request.user
        business_request.reviewed_at = timezone.now()
        business_request.rejection_reason = rejection_reason
        business_request.save()

        # Send rejection email
        subject = "Your FlexiPOS Business Request Has Been Rejected"

        message = f"""
Hello {business_request.owner_name},

We regret to inform you that your business request has been rejected.

Reason:
{rejection_reason}

You may correct the issue and submit a new request.

Thank you,
FlexiPOS Team
"""

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [business_request.email],
            fail_silently=False,
        )

        messages.success(request, "Business request rejected and email sent.")
        return redirect("superadmin_dashboard")

    # ✅ If GET request → just show form
    return render(request, "core/reject_form.html", {"req": business_request})


@login_required
def request_detail(request, request_id):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    business_request = get_object_or_404(BusinessRequest, id=request_id)

    return render(request, "core/request_detail.html", {
        "req": business_request
    })




@login_required
def owner_dashboard_redirect(request):
    if request.user.role != "OWNER":
        return redirect("login")

    business_type = get_business_type_code(request.user)

    if business_type == "restaurant":
        return redirect("restaurant_owner_dashboard")
    elif business_type == "clothing":
        return redirect("clothing_owner_dashboard")
    elif business_type == "mart":
        return redirect("mart_owner_dashboard")

    return redirect("login")


@login_required
def restaurant_owner_dashboard(request):
    if request.user.role != "OWNER":
        return redirect("login")

    business = request.user.business
    if get_business_type_code(request.user) != "restaurant":
        return redirect("login")

    total_staff = User.objects.filter(business=business).exclude(role="OWNER").count()
    active_staff = User.objects.filter(business=business, is_active=True).exclude(role="OWNER").count()
    total_categories = Category.objects.filter(business=business).count()
    total_items = Item.objects.filter(business=business).count()
    active_items = Item.objects.filter(business=business, is_active=True).count()
    total_tables = DiningTable.objects.filter(business=business).count()

    active_subscription = get_active_subscription(business)
    days_remaining = None
    max_users = active_subscription.package.max_users if active_subscription else 3
    max_tables = active_subscription.package.max_tables if active_subscription else 5
    current_users = User.objects.filter(business=business).count()
    current_tables = DiningTable.objects.filter(business=business).count()

    remaining_users = max(max_users - current_users, 0)
    remaining_tables = max(max_tables - current_tables, 0)

    if active_subscription and active_subscription.end_date:
        days_remaining = (active_subscription.end_date - timezone.now()).days

    context = {
        "total_staff": total_staff,
        "active_staff": active_staff,
        "total_categories": total_categories,
        "total_items": total_items,
        "active_items": active_items,
        "total_tables": total_tables,
        "active_subscription": active_subscription,
        "days_remaining": days_remaining,
        "max_users": max_users,
        "max_tables": max_tables,
        "current_users": current_users,
        "remaining_users": remaining_users,
        "remaining_tables": remaining_tables,
    }
    return render(request, "owner/dashboard_restaurant.html", context)


@login_required
def clothing_owner_dashboard(request):
    if request.user.role != "OWNER":
        return redirect("login")

    if get_business_type_code(request.user) != "clothing":
        return redirect("login")

    business = request.user.business

    total_staff = User.objects.filter(business=business).exclude(role="OWNER").count()

    context = {
        "total_staff": total_staff,
    }
    return render(request, "owner/dashboard_clothing.html", context)


@login_required
def mart_owner_dashboard(request):
    if request.user.role != "OWNER":
        return redirect("login")

    if get_business_type_code(request.user) != "mart":
        return redirect("login")

    business = request.user.business

    total_staff = User.objects.filter(business=business).exclude(role="OWNER").count()

    context = {
        "total_staff": total_staff,
    }
    return render(request, "owner/dashboard_mart.html", context)
