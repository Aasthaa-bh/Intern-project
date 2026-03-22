from django.db import models


from django.db import models

class TableCategory(models.Model):
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE, related_name="table_categories")

    name = models.CharField(max_length=50)        # Cabin, Inside, Outside
    code_prefix = models.CharField(max_length=2)  # C, T, O

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "code_prefix")

    def __str__(self):
        return f"{self.business.business_name} - {self.name}"
    
class DiningTable(models.Model):
    STATUS = (
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)     
    category = models.ForeignKey(TableCategory, on_delete=models.CASCADE)

    number = models.PositiveIntegerField()   # 1,2,3,4
    name = models.CharField(max_length=10, blank=True)  # C1, T1, O1
    capacity = models.PositiveIntegerField(default=4)

    status = models.CharField(max_length=20, choices=STATUS, default="AVAILABLE")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business", "name")

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"{self.category.code_prefix}{self.number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.category.name})"
    



class Ingredient(models.Model):
    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)

    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    min_stock = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class InventoryStockHistory(models.Model):

    CHANGE_TYPE = (
        ("ADD", "Add"),
        ("CONSUME", "Consume"),
        ("WASTE", "Waste"),
        ("ADJUST", "Adjust"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    ingredient_name = models.CharField(max_length=100, blank=True, default="")
    unit = models.CharField(max_length=20, blank=True, default="")

    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    changed_at = models.DateTimeField()
#     created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-changed_at", "-id")
    created_at = models.DateTimeField(auto_now_add=True)
    

class KitchenOrder(models.Model):

    STATUS = (
        ("PENDING", "Pending"),
        ("SENT_TO_KITCHEN", "Sent to Kitchen"),
        ("PREPARING", "Preparing"),
        ("READY", "Ready"),
        ("SENT_TO_CASHIER", "Sent to Cashier"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    order = models.OneToOneField(
        "pos.Order", on_delete=models.CASCADE, related_name="kitchen_order"
    )

    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    sent_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    sent_to_cashier_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Kitchen Order #{self.order.order_no} - {self.status}"

class ReceptionInvoice(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    )
    business = models.ForeignKey('core.Business', on_delete=models.CASCADE)
    table = models.ForeignKey(DiningTable, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('pos.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reception_invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_uuid = models.CharField(max_length=200, blank=True, help_text="eSewa transaction UUID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Invoice {self.invoice_number} - {self.status}'


class ReceptionPayment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('ESEWA', 'eSewa'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )
    business = models.ForeignKey('core.Business', on_delete=models.CASCADE)
    invoice = models.ForeignKey(ReceptionInvoice, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True)
    transaction_uuid = models.CharField(max_length=200, blank=True, help_text="eSewa transaction UUID")
    payer_ref_code = models.CharField(max_length=100, blank=True, help_text="Customer's transaction/reference ID for payments")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    note = models.TextField(blank=True)
    processed_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    processed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Payment {self.payment_method} - Rs. {self.amount}'


class ReceptionLoyaltyTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('EARN', 'Earn Points'),
        ('REDEEM', 'Redeem Points'),
        ('EXPIRE', 'Expire Points'),
        ('ADJUST', 'Adjust Points'),
    )
    business = models.ForeignKey('core.Business', on_delete=models.CASCADE)
    invoice = models.ForeignKey(ReceptionInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    customer_phone = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    points = models.IntegerField()
    balance_after = models.IntegerField()
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.customer_name} - {self.transaction_type} {self.points} points'
