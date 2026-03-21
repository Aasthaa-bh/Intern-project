from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
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


# ==================== OFFER MODELS ====================

class Offer(models.Model):
    """Sales Offer Model for Clothing Store"""
    
    OFFER_TYPE_CHOICES = (
        ('PERCENTAGE', 'Percentage Discount'),
        ('FLAT', 'Flat Discount'),
        ('PRODUCT', 'Product Wise Offer'),
        ('VARIANT', 'Variant Wise Offer'),
        ('CATEGORY', 'Category Wise Offer'),
        ('SEASONAL', 'Seasonal/Festival Offer'),
        ('LOYALTY', 'Customer Loyalty Discount'),
    )
    
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('EXPIRED', 'Expired'),
    )
    
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    offer_name = models.CharField(max_length=200)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)
    description = models.TextField(blank=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    product = models.ForeignKey("pos.Item", null=True, blank=True, on_delete=models.CASCADE, related_name="product_offers")
    variants = models.ManyToManyField("pos.ItemVariant", blank=True, related_name="variant_offers")
    category = models.ForeignKey("pos.Category", null=True, blank=True, on_delete=models.CASCADE)
    minimum_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="clothing_offers_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'status', 'start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.offer_name} ({self.get_offer_type_display()})"
    
    def is_valid(self):
        today = timezone.now().date()
        return self.status == 'ACTIVE' and self.start_date <= today <= self.end_date
    
    def calculate_discount(self, subtotal, item=None, variant=None, category=None):
        if not self.is_valid() or subtotal < self.minimum_purchase:
            return Decimal('0.00')
        
        if self.offer_type == 'PRODUCT':
            if item and self.product and item.id == self.product.id:
                if self.offer_type in ['PERCENTAGE']:
                    return (subtotal * self.discount_value) / Decimal('100')
                return self.discount_value
        elif self.offer_type == 'VARIANT':
            if variant and self.variants.filter(id=variant.id).exists():
                if self.discount_value <= 100:
                    return (subtotal * self.discount_value) / Decimal('100')
                return self.discount_value
        elif self.offer_type == 'CATEGORY':
            if category and self.category and category.id == self.category.id:
                return (subtotal * self.discount_value) / Decimal('100')
        elif self.offer_type in ['PERCENTAGE', 'SEASONAL', 'LOYALTY']:
            return (subtotal * self.discount_value) / Decimal('100')
        elif self.offer_type == 'FLAT':
            return min(self.discount_value, subtotal)
        
        return Decimal('0.00')
    
    def get_discount_display(self):
        if self.offer_type in ['PERCENTAGE', 'SEASONAL', 'LOYALTY', 'CATEGORY', 'VARIANT']:
            return f"{self.discount_value}%"
        return f"Rs {self.discount_value}"
    
    def get_variants_display(self):
        """Get display text for selected variants"""
        if self.offer_type == 'VARIANT' and self.variants.exists():
            variant_list = []
            for variant in self.variants.all()[:5]:
                try:
                    detail = variant.clothing_detail
                    size_name = detail.size.name if detail.size else "N/A"
                    color_name = detail.color.name if detail.color else "N/A"
                    variant_list.append(f"{size_name}/{color_name}")
                except:
                    variant_list.append(variant.sku or f"ID:{variant.id}")
            
            display = ", ".join(variant_list)
            if self.variants.count() > 5:
                display += f" (+{self.variants.count() - 5} more)"
            return display
        return "All variants"


class OfferUsage(models.Model):
    """Track offer usage"""
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='usages')
    order = models.ForeignKey("pos.Order", on_delete=models.CASCADE)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.offer.offer_name} - Rs {self.discount_amount}"
