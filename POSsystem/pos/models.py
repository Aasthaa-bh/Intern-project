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

class Brand(models.Model):
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "name")

    def __str__(self):
        return self.name
    
class Supplier(models.Model):
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True)
    phone_no = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    pan_vat_no = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "name")

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
    brand = models.ForeignKey("pos.Brand", null=True, blank=True, on_delete=models.SET_NULL)

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, null=True, blank=True)
    barcode = models.CharField(max_length=100, null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE)
    
    description = models.TextField(blank=True)

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

    def __str__(self):
        if self.sku:
            return f"{self.name} ({self.sku})"
        return self.name

class ItemVariant(models.Model):
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="variants")

    name = models.CharField(max_length=100)  # e.g. Black / M, 500ml, Large
    sku = models.CharField(max_length=100)
    barcode = models.CharField(max_length=100, null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    

    track_stock = models.BooleanField(default=True)
    stock_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            ("business", "sku"),
            ("item", "name"),
        )

    def save(self, *args, **kwargs):
        if self.item_id and not self.business_id:
            self.business = self.item.business
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} / {self.name}"

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
        ("COUNTER", "Counter"),
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

    business_date = models.DateField(null=True, blank=True)  # to track sales by business date instead of calendar date
    
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def confirm(self):
        self.status = "COMPLETED"
        self.closed_at = timezone.now()
        self.save()
        
    class Meta:
        indexes = [
            models.Index(fields=["business", "status", "opened_at"]),
            models.Index(fields=["business", "order_type", "opened_at"]),
        ]


class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    variant = models.ForeignKey("pos.ItemVariant", null=True, blank=True, on_delete=models.PROTECT)

    item_name_snapshot = models.CharField(max_length=255)
    variant_name_snapshot = models.CharField(max_length=100, blank=True)
    sku_snapshot = models.CharField(max_length=100, blank=True)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["item"]),
            models.Index(fields=["variant"]),
        ]
    
class Purchase(models.Model):

    STATUS = (
        ("DRAFT", "Draft"),
        ("RECEIVED", "Received"),
        ("CANCELLED", "Cancelled"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    purchase_no = models.CharField(max_length=50)
    purchase_date = models.DateField()

    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    notes = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchases_received",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "purchase_no")

    def __str__(self):
        return self.purchase_no
        
class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    variant = models.ForeignKey("pos.ItemVariant", null=True, blank=True, on_delete=models.PROTECT)

    item_name_snapshot = models.CharField(max_length=255)
    variant_name_snapshot = models.CharField(max_length=100, blank=True)
    sku_snapshot = models.CharField(max_length=100, blank=True)

    expected_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchase_items_received",
    )

    @property
    def remaining_quantity(self):
        return (self.quantity or 0) - (self.received_quantity or 0)

    def __str__(self):
        return f"{self.purchase.purchase_no} - {self.item_name_snapshot}"
    
class StockMovement(models.Model):

    MOVEMENT_TYPE = (
        ("PURCHASE_IN", "Purchase In"),
        ("SALE_OUT", "Sale Out"),
        ("SALE_RETURN_IN", "Sale Return In"),
        ("PURCHASE_RETURN_OUT", "Purchase Return Out"),
        ("ADJUSTMENT_IN", "Adjustment In"),
        ("ADJUSTMENT_OUT", "Adjustment Out"),
        ("DAMAGE_OUT", "Damage Out"),
    )

    RETURN_CONDITION = (
        ("RESELLABLE", "Resellable"),
        ("DAMAGED", "Damaged"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    variant = models.ForeignKey("pos.ItemVariant", null=True, blank=True, on_delete=models.PROTECT)

    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.PositiveIntegerField(null=True, blank=True)

    return_condition = models.CharField(max_length=20, choices=RETURN_CONDITION, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["item"]),
            models.Index(fields=["variant"]),
            models.Index(fields=["business", "movement_type", "created_at"]),
        ]
    
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["business", "status", "issued_at"]),   
        ]

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

    created_at = models.DateTimeField(auto_now_add=True)
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
