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


# Cashier Models for POS System

class CashierCustomer(models.Model):
    """Customer model for cashier operations"""
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)

    loyalty_points = models.PositiveIntegerField(default=0)
    total_purchases = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_purchase_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("business", "phone")

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def add_loyalty_points(self, purchase_amount):
        """Add loyalty points based on purchase amount (1 point per Rs. 100)"""
        points = int(purchase_amount // 100)
        if points > 0:
            self.loyalty_points += points
            self.save()
        return points

    def redeem_loyalty_points(self, points):
        """Calculate discount for redeeming loyalty points (1 point = Rs. 1)"""
        if points > self.loyalty_points:
            points = self.loyalty_points

        discount = Decimal(points)
        self.loyalty_points -= points
        self.save()

        return discount


class CashierPromoCode(models.Model):
    """Promo code model for discounts"""
    DISCOUNT_TYPE = (
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=200)

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE, default='PERCENTAGE')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)

    minimum_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    usage_limit = models.PositiveIntegerField(default=0)  # 0 = unlimited
    usage_count = models.PositiveIntegerField(default=0)

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'PERCENTAGE' else 'Rs.'}"

    def can_apply(self, subtotal):
        """Check if promo code can be applied"""
        if not self.is_active:
            return False

        now = timezone.now()
        if now < self.valid_from or now > self.valid_until:
            return False

        if subtotal < self.minimum_purchase:
            return False

        if self.usage_limit > 0 and self.usage_count >= self.usage_limit:
            return False

        return True

    def apply_discount(self, subtotal):
        """Calculate discount amount"""
        if self.discount_type == 'PERCENTAGE':
            discount = subtotal * (self.discount_value / 100)
        else:
            discount = min(self.discount_value, subtotal)

        return discount

    def mark_used(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save()


class CashierLoyaltyTransaction(models.Model):
    """Transaction log for loyalty points"""
    TRANSACTION_TYPE = (
        ('EARNED', 'Earned'),
        ('REDEEMED', 'Redeemed'),
    )

    customer = models.ForeignKey(CashierCustomer, on_delete=models.CASCADE, related_name='loyalty_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE)
    points = models.IntegerField()  # Positive for earned, negative for redeemed
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Purchase amount for earned, discount for redeemed
    invoice_number = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type} {self.points} points"

    def get_description(self):
        """Get human-readable description of the transaction"""
        if self.transaction_type == 'EARNED':
            return f"Earned {self.points} points for purchase of Rs. {self.amount}"
        else:
            return f"Redeemed {abs(self.points)} points for Rs. {self.amount} discount"