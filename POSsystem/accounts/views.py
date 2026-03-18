from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme

def login_view(request):
    if request.method == "GET":
        next_url = request.GET.get("next")
        if next_url:
            request.session["login_next"] = next_url

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        next_url = request.POST.get("next") or request.GET.get("next") or request.session.pop("login_next", None)

        user = authenticate(request, username=username, password=password)

        if user:
            # 🔥 SUPERADMIN login (no business_code)
            if user.role == "SUPERADMIN":
                login(request, user)
                if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                    return redirect(next_url)
                return redirect("superadmin_dashboard")

            # 🔥 For OWNER and staff, automatically use user's business
            if not user.business:
                messages.error(request, "User is not linked to any business.")
                return redirect("login")

            login(request, user)

            # 🔥 First login password change
            if user.is_first_login:
                return redirect("change_password")

            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)

            # 🔥 Redirect based on role
            if user.role == "OWNER":
                return redirect("inventory_dashboard")
            elif user.role == "CASHIER":
                return redirect("reception_dashboard")
            elif user.role == "WAITER":
                return redirect("waiter_dashboard")
            elif user.role == "KITCHEN":
                return redirect("restaurant_kitchen_dashboard")
            else:
                # fallback
                return redirect("login")

        else:
            messages.error(request, "Invalid username or password.")

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
