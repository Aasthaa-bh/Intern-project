from django.contrib import admin
from .models import (
    DiningTable, 
    Ingredient, 
    InventoryStockHistory,
)


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'capacity', 'category', 'status', 'business', 'created_at']
    list_filter = ['status', 'category', 'business']
    search_fields = ['number']
    list_editable = ['status']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'quantity', 'min_stock', 'business', 'created_at']
    list_filter = ['unit', 'business']
    search_fields = ['name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Highlight low stock items
        return qs


@admin.register(InventoryStockHistory)
class InventoryStockHistoryAdmin(admin.ModelAdmin):
    list_display = ['ingredient', 'change_type', 'quantity_change', 'changed_by', 'changed_at', 'business']
    list_filter = ['change_type', 'changed_at', 'business']
    search_fields = ['ingredient__name', 'note']
    readonly_fields = ['created_at']
    date_hierarchy = 'changed_at'
