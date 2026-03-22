from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = (
        ("SUPERADMIN", "Super Admin"),
        ("OWNER", "Owner"),
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


class UserPreference(models.Model):
    THEME_CHOICES = (
        ("light", "Light"),
        ("dark", "Dark"),
    )

    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("ne", "Nepali"),
    )

    DATE_FORMAT_CHOICES = (
        ("YYYY-MM-DD", "YYYY-MM-DD"),
        ("DD-MM-YYYY", "DD-MM-YYYY"),
        ("MM-DD-YYYY", "MM-DD-YYYY"),
    )

    TIME_FORMAT_CHOICES = (
        ("12h", "12 Hour"),
        ("24h", "24 Hour"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preferences"
    )

    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default="light"
    )
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default="en"
    )
    timezone = models.CharField(
        max_length=100,
        default="Asia/Kathmandu"
    )
    date_format = models.CharField(
        max_length=20,
        choices=DATE_FORMAT_CHOICES,
        default="YYYY-MM-DD"
    )
    time_format = models.CharField(
        max_length=10,
        choices=TIME_FORMAT_CHOICES,
        default="24h"
    )

    compact_mode = models.BooleanField(default=False)
    sidebar_collapsed = models.BooleanField(default=False)

    email_notifications = models.BooleanField(default=True)
    in_app_notifications = models.BooleanField(default=True)
    sound_notifications = models.BooleanField(default=True)

    new_order_alert = models.BooleanField(default=True)
    low_stock_alert = models.BooleanField(default=True)
    payment_alert = models.BooleanField(default=True)

    rows_per_page = models.PositiveIntegerField(default=10)
    auto_print_receipt = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Preferences"
    
    from django.db import models
from django.conf import settings

class UserSettings(models.Model):
    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
    ]

    LANGUAGE_CHOICES = [
        ("english", "English"),
        ("nepali", "Nepali"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="light")
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default="english")
    timezone = models.CharField(max_length=100, default="Asia/Kathmandu")
    rows_per_page = models.PositiveIntegerField(default=10)

    email_notifications = models.BooleanField(default=False)
    in_app_notifications = models.BooleanField(default=False)
    sound_alerts = models.BooleanField(default=False)
    new_order_alert = models.BooleanField(default=False)
    low_stock_alert = models.BooleanField(default=False)
    auto_print_receipt = models.BooleanField(default=False)
    compact_mode = models.BooleanField(default=False)
    collapse_sidebar = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} Settings"