from django.contrib import admin
from .models import Package, BusinessSubscription, SubscriptionPayment

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_months", "max_users", "max_tables", "max_products", "price", "is_active")