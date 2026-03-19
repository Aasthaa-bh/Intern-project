from django.contrib import admin
from .models import ClothingItem, ClothingVariantDetail, Color, Size


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "size_type", "is_active", "business"]
    list_filter = ["size_type", "is_active", "business"]
    search_fields = ["name", "code"]


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "hex_code", "is_active", "business"]
    list_filter = ["is_active", "business"]
    search_fields = ["name", "code"]


@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    list_display = ["item", "gender", "material", "fit", "updated_at"]
    list_filter = ["gender"]
    search_fields = ["item__name", "material", "fit"]


@admin.register(ClothingVariantDetail)
class ClothingVariantDetailAdmin(admin.ModelAdmin):
    list_display = ["variant", "size", "color"]
    search_fields = ["variant__item__name", "variant__name", "size__name", "color__name"]
