from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import UserPreference

User = get_user_model()


class StaffCreateForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text=_("Leave blank to auto-generate a temporary password.")
    )

    class Meta:
        model = User
        fields = ["full_name", "username", "email", "phone_no", "address", "role", "password"]

    def __init__(self, *args, **kwargs):
        business_type = kwargs.pop("business_type", None)
        super().__init__(*args, **kwargs)

        if business_type == "restaurant":
            self.fields["role"].choices = [
                ("CASHIER", _("Cashier")),
                ("WAITER", _("Waiter")),
                ("KITCHEN", _("Kitchen")),
            ]
        else:
            self.fields["role"].choices = [
                ("CASHIER", _("Cashier")),
            ]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("This username is already taken."))
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("This email is already in use."))
        return email


class StaffUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "email", "phone_no", "address", "role", "is_active"]

    def __init__(self, *args, **kwargs):
        business_type = kwargs.pop("business_type", None)
        super().__init__(*args, **kwargs)

        if business_type == "restaurant":
            self.fields["role"].choices = [
                ("CASHIER", _("Cashier")),
                ("WAITER", _("Waiter")),
                ("KITCHEN", _("Kitchen")),
            ]
        else:
            self.fields["role"].choices = [
                ("CASHIER", _("Cashier")),
            ]


class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = [
            "theme",
            "language",
            "timezone",
            "date_format",
            "time_format",
            "compact_mode",
            "sidebar_collapsed",
            "email_notifications",
            "in_app_notifications",
            "sound_notifications",
            "new_order_alert",
            "low_stock_alert",
            "payment_alert",
            "rows_per_page",
            "auto_print_receipt",
        ]
        widgets = {
            "theme": forms.Select(attrs={"class": "form-select"}),
            "language": forms.Select(attrs={"class": "form-select"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
            "date_format": forms.Select(attrs={"class": "form-select"}),
            "time_format": forms.Select(attrs={"class": "form-select"}),
            "compact_mode": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sidebar_collapsed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "email_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "in_app_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sound_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "new_order_alert": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "low_stock_alert": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "payment_alert": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "rows_per_page": forms.NumberInput(attrs={"class": "form-control", "min": 5, "max": 100}),
            "auto_print_receipt": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_rows_per_page(self):
        rows = self.cleaned_data["rows_per_page"]
        allowed_values = [10, 25, 50, 100]
        if rows not in allowed_values:
            raise forms.ValidationError(_("Rows per page must be one of: 10, 25, 50, 100."))
        return rows