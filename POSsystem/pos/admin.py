from django.contrib import admin
from .models import (
    Category,
    Customer,
    Item,
    ItemVariant,
    LoyaltySetting,
    LoyaltyTransaction,
    Order,
    Purchase,
    PurchaseItem,
    StockMovement,
    Supplier,
)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_no', 'email', 'status', 'business', 'created_at']
    list_filter = ['status', 'business']
    search_fields = ['full_name', 'phone_no', 'email']
    list_editable = ['status']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs

@admin.register(LoyaltySetting)
class LoyaltySettingAdmin(admin.ModelAdmin):
    list_display = ['business', 'amount_required', 'points_per_amount', 'min_redeem_points', 'max_redeem_percent', 'is_active']
    list_filter = ['is_active', 'business']
    list_editable = ['is_active']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "business" and not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                kwargs["queryset"] = db_field.related_model.objects.filter(id=request.user.business.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'type', 'points_earned', 'points_redeemed', 'business', 'created_at']
    list_filter = ['type', 'business', 'created_at']
    search_fields = ['customer__full_name', 'customer__phone_no', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "business" and not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                kwargs["queryset"] = db_field.related_model.objects.filter(id=request.user.business.id)
        if db_field.name == "customer" and not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                kwargs["queryset"] = db_field.related_model.objects.filter(business=request.user.business)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'business', 'created_at']
    list_filter = ['is_active', 'business']
    search_fields = ['name']
    list_editable = ['is_active']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'item_type', 'price', 'stock_qty', 'is_active', 'business']
    list_filter = ['item_type', 'is_active', 'business', 'category']
    search_fields = ['name', 'sku']
    list_editable = ['is_active', 'price']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, 'business') and request.user.business:
                qs = qs.filter(business=request.user.business)
        return qs

@admin.register(ItemVariant)
class ItemVariantAdmin(admin.ModelAdmin):
    list_display = ['item', 'name', 'sku', 'stock_qty', 'is_active', 'business']
    list_filter = ['is_active', 'business', 'item']
    search_fields = ['item__name', 'name', 'sku']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone_no', 'is_active', 'business']
    list_filter = ['is_active', 'business']
    search_fields = ['name', 'contact_person', 'phone_no']


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['purchase_no', 'supplier', 'purchase_date', 'status', 'total_amount', 'business']
    list_filter = ['status', 'purchase_date', 'business']
    search_fields = ['purchase_no', 'supplier__name']
    inlines = [PurchaseItemInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['item', 'variant', 'movement_type', 'quantity', 'business', 'created_at']
    list_filter = ['movement_type', 'business', 'created_at']
    search_fields = ['item__name', 'variant__name', 'note']

admin.site.register(Order)
