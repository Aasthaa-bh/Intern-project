from django.db import models
from django.utils import timezone


class Category(models.Model):
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name



class Item(models.Model):

    ITEM_TYPE = (
        ("MENU", "Menu"),
        ("PRODUCT", "Product"),
        ("SERVICE", "Service"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    track_stock = models.BooleanField(default=False)
    stock_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Customer(models.Model):

    STATUS = (
        ("ACTIVE", "Active"),
        ("BLOCKED", "Blocked"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="ACTIVE")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Order(models.Model):

    STATUS = (
        ("OPEN", "Open"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    ORDER_TYPE = (
        ("DINE_IN", "Dine In"),
        ("TAKEAWAY", "Takeaway"),
        ("DELIVERY", "Delivery"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    order_no = models.CharField(max_length=50)

    customer = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.SET_NULL
    )
    table = models.ForeignKey(
        "restaurant.DiningTable", null=True, blank=True, on_delete=models.SET_NULL
    )

    order_type = models.CharField(max_length=20, choices=ORDER_TYPE)
    status = models.CharField(max_length=20, choices=STATUS, default="OPEN")

    notes = models.CharField(max_length=255, blank=True)

    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="orders_created"
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders_updated",
    )

    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    def confirm(self):
        self.status = "COMPLETED"
        self.closed_at = timezone.now()
        self.save()


class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)

    item_name_snapshot = models.CharField(max_length=255)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Invoice(models.Model):

    STATUS = (
        ("UNPAID", "Unpaid"),
        ("PAID", "Paid"),
        ("VOID", "Void"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    order = models.OneToOneField(Order, on_delete=models.CASCADE)

    invoice_no = models.CharField(max_length=50)

    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS, default="UNPAID")
    issued_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)


class Payment(models.Model):

    STATUS = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )

    method = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS)
    reference_no = models.CharField(max_length=255, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)


class LoyaltySetting(models.Model):

    business = models.OneToOneField("core.Business", on_delete=models.CASCADE)

    amount_required = models.DecimalField(max_digits=10, decimal_places=2)
    points_per_amount = models.IntegerField()
    min_redeem_points = models.IntegerField()
    max_redeem_percent = models.DecimalField(max_digits=5, decimal_places=2)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LoyaltyTransaction(models.Model):

    TYPE = (
        ("EARN", "Earn"),
        ("REDEEM", "Redeem"),
        ("ADJUST", "Adjust"),
        ("REFUND", "Refund"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)

    points_earned = models.IntegerField(default=0)
    points_redeemed = models.IntegerField(default=0)

    type = models.CharField(max_length=20, choices=TYPE)
    description = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
