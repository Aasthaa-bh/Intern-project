from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from core.utils import get_business_type_code


def login_view(request):
    if request.method == "GET":
        next_url = request.GET.get("next")
        if next_url:
            request.session["login_next"] = next_url

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password")
        business_code = (request.POST.get("business_code") or "").strip()

        user = authenticate(request, username=username, password=password)

        if not user:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

        # SUPERADMIN login
        if user.role == "SUPERADMIN":
            login(request, user)
            return redirect("superadmin_dashboard")

        if not user.business:
            messages.error(request, "User is not linked to any business.")
            return redirect("login")

        # business code verify for non-superadmin
        if not business_code:
            messages.error(request, "Business code is required.")
            return redirect("login")

        if user.business.business_code != business_code:
            messages.error(request, "Invalid business code.")
            return redirect("login")

        login(request, user)

        request.session["business_id"] = user.business.id
        request.session["business_code"] = user.business.business_code
        request.session["business_type"] = get_business_type_code(user)

        if user.is_first_login:
            return redirect("change_password")

        business_type = get_business_type_code(user)

        if user.role == "OWNER":
            if business_type == "restaurant":
                return redirect("restaurant_owner_dashboard")
            elif business_type == "clothing":
                return redirect("clothing_inventory_dashboard")
            elif business_type == "mart":
                return redirect("mart_owner_dashboard")

        elif user.role == "CASHIER":
            if business_type == "restaurant":
                return redirect("reception_dashboard")
            elif business_type == "clothing":
                return redirect("clothing_cashier_dashboard")
            elif business_type == "mart":
                return redirect("mart_cashier_dashboard")

        elif user.role == "WAITER":
            if business_type == "restaurant":
                return redirect("waiter_dashboard")
            messages.error(request, "Waiter role is only valid for restaurant business.")
            logout(request)
            return redirect("login")

        elif user.role == "KITCHEN":
            if business_type == "restaurant":
                return redirect("restaurant_kitchen_dashboard")
            messages.error(request, "Kitchen role is only valid for restaurant business.")
            logout(request)
            return redirect("login")

        messages.error(request, "No dashboard configured for this account.")
        logout(request)
        return redirect("login")

    return render(request, "core/login.html")


@login_required
def change_password(request):
    if request.method == "POST":
        new_password = request.POST.get("new_password")

        if not new_password or len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect("change_password")

        request.user.set_password(new_password)
        request.user.is_first_login = False
        request.user.save()

        messages.success(request, "Password changed successfully. Please login again.")
        return redirect("login")

    return render(request, "accounts/change_password.html")


def logout_view(request):
    logout(request)
    return redirect("login")
