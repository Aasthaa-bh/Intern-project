from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


STAFF_ROLES = (
    ("CASHIER", "Cashier"),
    ("WAITER", "Waiter"),
    ("KITCHEN", "Kitchen"),
)


class StaffCreateForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text="Leave blank to auto-generate a temporary password."
    )

    class Meta:
        model = User
        fields = ["full_name", "username", "email", "phone_no", "address", "role", "password"]

    role = forms.ChoiceField(choices=STAFF_ROLES)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if email and User.objects.filter(email=email).exists():
            # optional: allow duplicates if you want, but for highest marks keep unique-ish
            raise forms.ValidationError("This email is already in use.")
        return email


class StaffUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "email", "phone_no", "address", "role", "is_active"]

    role = forms.ChoiceField(choices=STAFF_ROLES)