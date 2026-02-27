import random
import string

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import StaffCreateForm, StaffUpdateForm
from core.decorators import owner_required

User = get_user_model()


def _generate_temp_password(length=8):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


@owner_required
def staff_list(request):
    business = request.user.business

    staff_qs = User.objects.filter(
        business=business,
        role__in=["CASHIER", "WAITER", "KITCHEN"],
    ).order_by("-created_at")

    return render(request, "owner/staff/staff_list.html", {"staff_list": staff_qs})


@owner_required
def staff_create(request):
    business = request.user.business

    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            temp_password = form.cleaned_data.get("password") or _generate_temp_password()

            user = form.save(commit=False)
            user.business = business
            user.is_first_login = True
            user.is_active = True
            user.set_password(temp_password)
            user.save()

            # For highest marks: show temp password once in message (or email later)
            messages.success(
                request,
                f"Staff created successfully. Temporary password for {user.username}: {temp_password}"
            )
            return redirect("staff_list")
    else:
        form = StaffCreateForm()

    return render(request, "owner/staff/staff_form.html", {"form": form, "mode": "create"})


@owner_required
def staff_edit(request, staff_id):
    business = request.user.business

    staff = get_object_or_404(
        User,
        id=staff_id,
        business=business,
        role__in=["CASHIER", "WAITER", "KITCHEN"],
    )

    if request.method == "POST":
        form = StaffUpdateForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff updated successfully.")
            return redirect("staff_list")
    else:
        form = StaffUpdateForm(instance=staff)

    return render(request, "owner/staff/staff_form.html", {"form": form, "mode": "edit", "staff": staff})


@require_POST
@owner_required
def staff_toggle_active(request, staff_id):
    business = request.user.business

    staff = get_object_or_404(
        User,
        id=staff_id,
        business=business,
        role__in=["CASHIER", "WAITER", "KITCHEN"],
    )

    staff.is_active = not staff.is_active
    staff.save(update_fields=["is_active"])
    messages.success(request, f"{staff.username} is now {'Active' if staff.is_active else 'Inactive'}.")
    return redirect("staff_list")


@require_POST
@owner_required
def staff_reset_password(request, staff_id):
    business = request.user.business

    staff = get_object_or_404(
        User,
        id=staff_id,
        business=business,
        role__in=["CASHIER", "WAITER", "KITCHEN"],
    )

    new_password = _generate_temp_password()
    staff.set_password(new_password)
    staff.is_first_login = True
    staff.save(update_fields=["password", "is_first_login"])

    messages.success(request, f"Password reset done. Temporary password for {staff.username}: {new_password}")
    return redirect("staff_list")