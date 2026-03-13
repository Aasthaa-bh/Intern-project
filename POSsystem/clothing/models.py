from django.db import models
from django.contrib.auth import get_user_model
from pos.models import Item, ItemVariant

class Size(models.Model):
    SIZE_TYPE = (
        ("ALPHA", "Alpha"),      # S, M, L, XL
        ("NUMERIC", "Numeric"),  # 28, 30, 32, 46
        ("SHOE", "Shoe"),        # 40, 41, 42
        ("FREE", "Free Size"),   # Free Size
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=50)   # Small, 46, 42 EU
    code = models.CharField(max_length=20)   # S, 46, 42EU
    size_type = models.CharField(max_length=20, choices=SIZE_TYPE, default="ALPHA")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "code")
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name


class Color(models.Model):
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=50)   # Black, White, Blue
    code = models.CharField(max_length=20, blank=True)   # BLK, WHT
    hex_code = models.CharField(max_length=7, blank=True)  # optional: #000000
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "name")

    def __str__(self):
        return self.name


class ClothingItem(models.Model):
    GENDER = (
        ("MEN", "Men"),
        ("WOMEN", "Women"),
        ("UNISEX", "Unisex"),
        ("BOYS", "Boys"),
        ("GIRLS", "Girls"),
        ("KIDS", "Kids"),
    )

    item = models.OneToOneField("pos.Item", on_delete=models.CASCADE, related_name="clothing")
    gender = models.CharField(max_length=20, choices=GENDER, default="UNISEX")
    material = models.CharField(max_length=100, blank=True)
    fit = models.CharField(max_length=50, blank=True)   # Slim Fit, Regular Fit
    care_note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.item.name
    
class ClothingVariantDetail(models.Model):
    variant = models.OneToOneField("pos.ItemVariant", on_delete=models.CASCADE, related_name="clothing_detail")
    size = models.ForeignKey("clothing.Size", null=True, blank=True, on_delete=models.SET_NULL)
    color = models.ForeignKey("clothing.Color", null=True, blank=True, on_delete=models.SET_NULL)