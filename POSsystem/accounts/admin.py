from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Extra Information", {
            "fields": (
                "role",
                "business",
                "full_name",
                "phone_no",
                "address",
                "is_first_login",
            )
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Extra Information", {
            "fields": (
                "role",
                "business",
                "full_name",
                "phone_no",
                "address",
            )
        }),
    )

    list_display = (
        "username",
        "email",
        "role",
        "business",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_superuser",
        "is_active",
    )