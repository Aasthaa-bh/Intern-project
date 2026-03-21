from django.contrib import admin
from .models import Size, Color, ClothingItem, ClothingVariantDetail, Offer, OfferUsage
from .models import ClothingItem, ClothingVariantDetail, Color, Size


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'size_type', 'sort_order', 'is_active', 'business']
    list_filter = ['size_type', 'is_active', 'business']
    search_fields = ['name', 'code']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'hex_code', 'is_active', 'business']
    list_filter = ['is_active', 'business']
    search_fields = ['name', 'code']


@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    list_display = ["item", "gender", "material", "fit", "updated_at"]
    list_filter = ["gender"]
    search_fields = ["item__name", "material", "fit"]


@admin.register(ClothingVariantDetail)
class ClothingVariantDetailAdmin(admin.ModelAdmin):
    list_display = ['variant', 'size', 'color']
    list_filter = ['size', 'color']


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ['offer_name', 'offer_type', 'discount_value', 'start_date', 'end_date', 'status', 'business']
    list_filter = ['offer_type', 'status', 'business', 'start_date']
    search_fields = ['offer_name', 'description']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    date_hierarchy = 'start_date'
    filter_horizontal = ['variants']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('business', 'offer_name', 'offer_type', 'description', 'status')
        }),
        ('Discount Details', {
            'fields': ('discount_value', 'minimum_purchase')
        }),
        ('Validity Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Conditions', {
            'fields': ('product', 'variants', 'category'),
            'description': 'Select product first, then choose specific variants for variant-wise offers'
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(OfferUsage)
class OfferUsageAdmin(admin.ModelAdmin):
    list_display = ['offer', 'order', 'discount_amount', 'applied_at']
    list_filter = ['offer', 'applied_at']
    search_fields = ['offer__offer_name', 'order__order_no']
    readonly_fields = ['applied_at']
    date_hierarchy = 'applied_at'
