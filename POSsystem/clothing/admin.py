from django.contrib import admin
from pos.models import Purchase, PurchaseItem, StockMovement

# Register your models here.

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['purchase_no', 'supplier', 'business', 'purchase_date', 'status', 'total_amount']
    list_filter = ['status', 'business', 'purchase_date']
    search_fields = ['purchase_no', 'supplier__name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs

@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ['purchase', 'item', 'quantity', 'expected_quantity', 'unit_cost', 'line_total']
    search_fields = ['purchase__purchase_no', 'item__name']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['item', 'movement_type', 'quantity', 'business', 'created_at']
    list_filter = ['movement_type', 'business']
    search_fields = ['item__name', 'note']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs
