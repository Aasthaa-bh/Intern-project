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
from subscription.models import BusinessSubscription, Package



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

    

    total_business = Business.objects.count()
    total_packages = Package.objects.count()
    total_subscriptions = BusinessSubscription.objects.count()
    active_subscriptions = BusinessSubscription.objects.filter(status="ACTIVE").count()

    context = {
        "total_business": total_business,
        "total_packages": total_packages,
        "total_subscriptions": total_subscriptions,
        "active_subscriptions": active_subscriptions,
    }

    return render(request, "core/superadmin_dashboard.html", context)


@login_required
def superadmin_requests(request):
    if request.user.role != "SUPERADMIN":
        return redirect("login")

    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    requests = BusinessRequest.objects.all()

    if search_query:
        requests = requests.filter(
            Q(business_name__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if status_filter:
        requests = requests.filter(status=status_filter)

    context = {
        "pending_requests": requests.filter(status="PENDING"),
        "approved_requests": requests.filter(status="APPROVED"),
        "rejected_requests": requests.filter(status="REJECTED"),
        "search_query": search_query,
        "status_filter": status_filter,
    }

    return render(request, "core/superadmin_requests.html", context)
    




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

            # 🔹 Generate unique business code
            while True:
                business_code = "BIZ" + str(random.randint(1000, 9999))
                if not Business.objects.filter(business_code=business_code).exists():
                    break

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
def owner_dashboard(request):

    if request.user.role != "OWNER":
        return redirect("login")

    business = request.user.business

    subscription = BusinessSubscription.objects.filter(
        business=business,
        is_current=True
    ).first()

    days_remaining = None

    if subscription and subscription.end_date:
        days_remaining = (subscription.end_date - timezone.now()).days

    context = {
        "business": business,
        "subscription": subscription,
        "days_remaining": days_remaining
    }

@login_required
def owner_dashboard(request):

    if request.user.role != "OWNER":
        return redirect("login")

    business = request.user.business

    total_staff = User.objects.filter(
        business=business
    ).exclude(role="OWNER").count()

    active_staff = User.objects.filter(
        business=business,
        is_active=True
    ).exclude(role="OWNER").count()

    total_categories = Category.objects.filter(
        business=business
    ).count()

    total_items = Item.objects.filter(
        business=business
    ).count()

    active_items = Item.objects.filter(
        business=business,
        is_active=True
    ).count()

    total_tables = DiningTable.objects.filter(
        business=business
    ).count()

    context = {
        "total_staff": total_staff,
        "active_staff": active_staff,
        "total_categories": total_categories,
        "total_items": total_items,
        "active_items": active_items,
        "total_tables": total_tables,
    }

    return render(request, "owner/dashboard.html", context)