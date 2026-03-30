# from django.contrib import admin
# from .models import BusinessType, BusinessRequest

# admin.site.register(BusinessType)


# @admin.action(description="Approve selected businesses")
# def approve_business(modeladmin, request, queryset):
#     for obj in queryset:
#         obj.approve(request.user)

# @admin.register(BusinessRequest)
# class BusinessRequestAdmin(admin.ModelAdmin):
#     list_display = ("business_name", "owner_name", "status")
#     actions = [approve_business]

from django.contrib import admin
from .models import BusinessType, BusinessRequest, Business

admin.site.register(BusinessType)


@admin.action(description="Approve selected businesses")
def approve_business(modeladmin, request, queryset):
    for obj in queryset:
        obj.approve(request.user)


@admin.register(BusinessRequest)
class BusinessRequestAdmin(admin.ModelAdmin):
    list_display = ("business_name", "owner_name", "status")
    actions = [approve_business]


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("business_name", "business_code", "business_type", "status")
    search_fields = ("business_name", "business_code")
    list_filter = ("business_type", "status")
