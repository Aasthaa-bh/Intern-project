from django.shortcuts import render, redirect
from django.contrib import messages
from core.decorators import owner_required
from .models import LoyaltySetting
from .forms import LoyaltySettingForm


@owner_required
def loyalty_settings(request):
    business = request.user.business

    loyalty = LoyaltySetting.objects.filter(business=business).first()

    if request.method == "POST":
        form = LoyaltySettingForm(request.POST, instance=loyalty)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.business = business  # important for create case
            obj.save()
            messages.success(request, "Loyalty settings saved successfully.")
            return redirect("loyalty_settings")
    else:
        form = LoyaltySettingForm(instance=loyalty)

    return render(request, "owner/loyalty/settings.html", {"form": form, "loyalty": loyalty})