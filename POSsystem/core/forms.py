from django import forms
from .models import BusinessRequest

INPUT_CLASS = (
    "w-full h-11 rounded-lg border border-black bg-white px-4 text-sm text-black "
    "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-black"
)

SELECT_CLASS = (
    "w-full h-11 rounded-lg border border-black bg-white px-4 text-sm text-black "
    "focus:outline-none focus:ring-2 focus:ring-black focus:border-black"
)

TEXTAREA_CLASS = (
    "w-full min-h-[140px] rounded-lg border border-black bg-white px-4 py-3 text-sm text-black "
    "placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black focus:border-black resize-none"
)

FILE_CLASS = (
    "w-full rounded-lg border border-black bg-white px-3 py-2 text-sm text-black "
    "file:mr-4 file:rounded-md file:border-0 file:bg-black file:px-4 file:py-2 file:text-white "
    "hover:file:bg-gray-800"
)


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
        widgets = {
            "business_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "owner_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "phone_no": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "maxlength": "10",
                "placeholder": "Enter 10-digit phone number",
            }),
            "business_type": forms.Select(attrs={"class": SELECT_CLASS}),
            "address": forms.Textarea(attrs={"class": TEXTAREA_CLASS, "rows": 5}),
            "pan_image": forms.ClearableFileInput(attrs={"class": FILE_CLASS}),
            "citizenship_image": forms.ClearableFileInput(attrs={"class": FILE_CLASS}),
        }

    def clean_phone_no(self):
        phone_no = self.cleaned_data.get("phone_no")

        if not phone_no:
            raise forms.ValidationError("Phone number is required.")

        phone_no = str(phone_no).strip()

        if not phone_no.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

        if len(phone_no) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        return phone_no