from django import forms
from .models import BusinessRequest

class BusinessRequestForm(forms.ModelForm):
    class Meta:
        model = BusinessRequest
        fields = [
            "business_name",
            "owner_name",
            "email",
            "phone_no",
            "business_type",
            "address",
            "pan_image",
            "citizenship_image",
        ]