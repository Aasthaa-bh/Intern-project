# subscription/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class Package(models.Model):
    name = models.CharField(max_length=50)
    duration_months = models.IntegerField()
    max_users = models.IntegerField()
    max_tables = models.IntegerField()  # added field for max tables
    max_products = models.IntegerField(null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class BusinessSubscription(models.Model):
    STATUS = (
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    )

    business = models.ForeignKey("core.Business", on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    is_current = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def activate(self):
        # expire old current subscriptions
        BusinessSubscription.objects.filter(
            business=self.business, is_current=True
        ).exclude(id=self.id).update(is_current=False)

        now = timezone.now()
        self.start_date = now
        self.end_date = now + timedelta(days=30 * self.package.duration_months)
        self.status = "ACTIVE"
        self.is_current = True
        self.save()

    def __str__(self):
        return f"{self.business.business_name} - {self.package.name}"


class SubscriptionPayment(models.Model):
    STATUS = (
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("REJECTED", "Rejected"),
    )

    subscription = models.ForeignKey(BusinessSubscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20)  # e.g. "KHALTI", "ESEWA", "BANK"
    transaction_ref = models.CharField(max_length=255, blank=True)

    payment_proof = models.ImageField(upload_to="payments/proofs/", null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    paid_at = models.DateTimeField(auto_now_add=True)

    verified_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subscription.business.business_name} - {self.amount}"