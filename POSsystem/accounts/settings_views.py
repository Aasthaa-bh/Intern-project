from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import UserPreference
from django.utils import translation



@login_required
def user_settings_view(request):
    preferences, created = UserPreference.objects.get_or_create(user=request.user)

    if request.method == "POST":
        preferences.theme = request.POST.get("theme", "light")
        preferences.language = request.POST.get("language", "en")
        preferences.timezone = request.POST.get("timezone", "Asia/Kathmandu")
        preferences.date_format = request.POST.get("date_format", "YYYY-MM-DD")
        preferences.time_format = request.POST.get("time_format", "24h")
        preferences.rows_per_page = request.POST.get("rows_per_page", 10)

        preferences.compact_mode = "compact_mode" in request.POST
        preferences.sidebar_collapsed = "sidebar_collapsed" in request.POST

        preferences.email_notifications = "email_notifications" in request.POST
        preferences.in_app_notifications = "in_app_notifications" in request.POST
        preferences.sound_notifications = "sound_notifications" in request.POST

        preferences.new_order_alert = "new_order_alert" in request.POST
        preferences.low_stock_alert = "low_stock_alert" in request.POST
        preferences.payment_alert = "payment_alert" in request.POST

        preferences.auto_print_receipt = "auto_print_receipt" in request.POST

        preferences.save()

        language = preferences.language
        translation.activate(language)
        request.session["django_language"] = language

        messages.success(request, "Your settings have been updated successfully.")
        return redirect("owner_dashboard")

    return render(request, "accounts/settings.html", {"preferences": preferences})
