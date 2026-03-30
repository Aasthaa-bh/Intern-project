import random
import string

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import StaffCreateForm, StaffUpdateForm
from core.decorators import owner_required
from subscription.utils import get_active_subscription, get_business_user_limit

User = get_user_model()


def _generate_temp_password(length=8):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def _get_business_type(request):
    if not request.user.business or not request.user.business.business_type:
        return None
    return request.user.business.business_type.name.strip().lower()


def _get_allowed_roles(request):
    business_type = _get_business_type(request)

    if business_type == "restaurant":
        return ["CASHIER", "WAITER", "KITCHEN"]

    elif business_type in ["clothing", "mart"]:
        return ["CASHIER"]

    return []


@owner_required
def staff_list(request):
    business = request.user.business
    allowed_roles = _get_allowed_roles(request)

    staff_qs = User.objects.filter(
        business=business,
        role__in=allowed_roles,
    ).order_by("-created_at")

    return render(request, "owner/staff/staff_list.html", {
        "staff_list": staff_qs,
        "business_type": _get_business_type(request),
    })


@owner_required
def staff_create(request):
    business = request.user.business
    business_type = _get_business_type(request)
    allowed_roles = _get_allowed_roles(request)

    active_subscription = get_active_subscription(business)
    max_users = get_business_user_limit(business)
    current_users = User.objects.filter(business=business).count()

    if current_users >= max_users:
        messages.error(
            request,
            f"User limit reached. Your current package allows only {max_users} users."
        )
        return redirect("business_package_list")

    if request.method == "POST":
        form = StaffCreateForm(request.POST, business_type=business_type)
        if form.is_valid():
            selected_role = form.cleaned_data.get("role")

            if selected_role not in allowed_roles:
                messages.error(request, "Selected role is not allowed for this business type.")
                return render(request, "owner/staff/staff_form.html", {
                    "form": form,
                    "mode": "create",
                    "max_users": max_users,
                    "current_users": current_users,
                    "active_subscription": active_subscription,
                    "business_type": business_type,
                })

            temp_password = form.cleaned_data.get("password") or _generate_temp_password()

            user = form.save(commit=False)
            user.business = business
            user.is_first_login = True
            user.is_active = True
            user.set_password(temp_password)
            user.save()

            messages.success(
                request,
                f"Staff created successfully. Temporary password for {user.username}: {temp_password}"
            )
            return redirect("staff_list")
    else:
        form = StaffCreateForm(business_type=business_type)

    return render(request, "owner/staff/staff_form.html", {
        "form": form,
        "mode": "create",
        "max_users": max_users,
        "current_users": current_users,
        "active_subscription": active_subscription,
        "business_type": business_type,
    })


@owner_required
def staff_edit(request, staff_id):
    business = request.user.business
    business_type = _get_business_type(request)
    allowed_roles = _get_allowed_roles(request)

    staff = get_object_or_404(
        User,
        id=staff_id,
        business=business,
        role__in=allowed_roles,
    )

    if request.method == "POST":
        form = StaffUpdateForm(request.POST, instance=staff, business_type=business_type)
        if form.is_valid():
            selected_role = form.cleaned_data.get("role")

            if selected_role not in allowed_roles:
                messages.error(request, "Selected role is not allowed for this business type.")
                return render(request, "owner/staff/staff_form.html", {
                    "form": form,
                    "mode": "edit",
                    "staff": staff,
                    "business_type": business_type,
                })

            form.save()
            messages.success(request, "Staff updated successfully.")
            return redirect("staff_list")
    else:
        form = StaffUpdateForm(instance=staff, business_type=business_type)

    return render(request, "owner/staff/staff_form.html", {
        "form": form,
        "mode": "edit",
        "staff": staff,
        "business_type": business_type,
    })


@owner_required
def staff_delete(request, staff_id):
    business = request.user.business
    allowed_roles = _get_allowed_roles(request)

    staff = get_object_or_404(
        User,
        id=staff_id,
        business=business,
        role__in=allowed_roles,
    )

    if request.method == "POST":
        staff.delete()
        messages.success(request, "Staff deleted successfully.")
        return redirect("staff_list")

    return render(request, "owner/staff/staff_delete.html", {
        "staff": staff,
        "business_type": _get_business_type(request),
    })


@require_POST
@owner_required
def staff_toggle_active(request, staff_id):
    business = request.user.business
    allowed_roles = _get_allowed_roles(request)

    staff = get_object_or_404(
        User,
        id=staff_id,
        business=business,
        role__in=allowed_roles,
    )

    staff.is_active = not staff.is_active
    staff.save(update_fields=["is_active"])

    messages.success(
        request,
        f"{staff.username} is now {'Active' if staff.is_active else 'Inactive'}."
    )
    return redirect("staff_list")


@require_POST
@owner_required
def staff_reset_password(request, staff_id):
    business = request.user.business
    allowed_roles = _get_allowed_roles(request)

    staff = get_object_or_404(
        User,
        id=staff_id,
        business=business,
        role__in=allowed_roles,
    )

    new_password = _generate_temp_password()
    staff.set_password(new_password)
    staff.is_first_login = True
    staff.save(update_fields=["password", "is_first_login"])

    messages.success(
        request,
        f"Password reset done. Temporary password for {staff.username}: {new_password}"
    )
    return redirect("staff_list")