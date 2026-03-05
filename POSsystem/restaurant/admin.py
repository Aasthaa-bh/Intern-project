from django.contrib import admin
from .models import DiningTable

@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'capacity', 'category', 'status', 'business', 'created_at']
    list_filter = ['status', 'category', 'business']
    search_fields = ['number', 'name']
    list_editable = ['status']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is not superadmin, show only their business tables
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filter business field for non-superusers
        if db_field.name == "business" and not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                kwargs["queryset"] = db_field.related_model.objects.filter(id=request.user.business.id)
        # Filter category based on business
        if db_field.name == "category":
            if hasattr(request.user, 'business') and request.user.business:
                kwargs["queryset"] = db_field.related_model.objects.filter(business=request.user.business)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

