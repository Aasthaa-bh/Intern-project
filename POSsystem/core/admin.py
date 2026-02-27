from django.contrib import admin
from .models import BusinessType, BusinessRequest

admin.site.register(BusinessType)



@admin.action(description="Approve selected businesses")
def approve_business(modeladmin, request, queryset):
    for obj in queryset:
        obj.approve(request.user)

@admin.register(BusinessRequest)
class BusinessRequestAdmin(admin.ModelAdmin):
    list_display = ("business_name", "owner_name", "status")
    actions = [approve_business]