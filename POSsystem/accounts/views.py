from django.shortcuts import render,redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            # 🔥 SUPERADMIN login (no business_code)
            if user.role == "SUPERADMIN":
                login(request, user)
                return redirect("superadmin_dashboard")

            # 🔥 For OWNER and staff, automatically use user's business
            if not user.business:
                messages.error(request, "User is not linked to any business.")
                return redirect("login")

            login(request, user)

            # 🔥 First login password change
            if user.is_first_login:
                return redirect("change_password")

            # Redirect based on business type + role
            return redirect("business_dashboard_router")

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

