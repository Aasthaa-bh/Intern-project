from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    ROLE_CHOICES = (
        ("SUPERADMIN", "Super Admin"),
        ("OWNER", "Owner"),
        ("MANAGER", "Manager"),
        ("CASHIER", "Cashier"),
        ("WAITER", "Waiter"),
        ("KITCHEN", "Kitchen"),
    )

    business = models.ForeignKey(
        "core.Business",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        db_constraint=False
    )

    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    full_name = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_first_login = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username