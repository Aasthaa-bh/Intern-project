from django import forms
from .models import Category, Item, LoyaltySetting 

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "is_active"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Category name is required.")
        return name
    
class ItemForm(forms.ModelForm):

    class Meta:
        model = Item
        fields = [
            "name",
            "category",
            "price",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)

        # Only show categories of this business
        if business:
            self.fields["category"].queryset = Category.objects.filter(
                business=business,
                is_active=True
            )
            
class LoyaltySettingForm(forms.ModelForm):

    class Meta:
        model = LoyaltySetting
        fields = [
            "amount_required",
            "points_per_amount",
            "min_redeem_points",
            "max_redeem_percent",
            "is_active",
        ]
