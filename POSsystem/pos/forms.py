from django import forms
from .models import Category, Item, LoyaltySetting


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "is_active"]

    def __init__(self, *args, **kwargs):
        self.business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Category name is required.")

        if self.business:
            qs = Category.objects.filter(
                business=self.business,
                name__iexact=name
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "A menu category with this name already exists."
                )

        return name


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "category",
            "price",
            "image",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        self.business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)

        if self.business:
            self.fields["category"].queryset = Category.objects.filter(
                business=self.business,
                is_active=True
            )

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Item name is required.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        name = (cleaned_data.get("name") or "").strip()
        category = cleaned_data.get("category")

        if self.business and name and category:
            qs = Item.objects.filter(
                business=self.business,
                category=category,
                name__iexact=name,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "name",
                    f"Menu item '{name}' already exists in this category."
                )

        return cleaned_data


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