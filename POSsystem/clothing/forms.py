from turtle import color

from django import forms
from django.forms import inlineformset_factory
import re

from pos.models import Brand, Category, Item, ItemVariant, Purchase, PurchaseItem, Supplier

from .models import ClothingItem, ClothingVariantDetail, Color, Size


class ClothingProductForm(forms.ModelForm):
    gender = forms.ChoiceField(choices=ClothingItem.GENDER, required=False)
    material = forms.CharField(max_length=100, required=False)
    fit = forms.CharField(max_length=50, required=False)
    care_note = forms.CharField(max_length=255, required=False)
    new_category = forms.CharField(max_length=100, required=False)
    new_brand = forms.CharField(max_length=100, required=False)

    class Meta:
        model = Item
        fields = [
            "name",
            "sku",
            "barcode",
            "category",
            "brand",
            "price",
            "cost_price",
            "track_stock",
            "stock_qty",
            "min_stock_qty",
            "has_variants",
            "description",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)
        self.business = business

        if business:
            self.fields["category"].queryset = Category.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")
            self.fields["brand"].queryset = Brand.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")

        self.fields["category"].required = False
        self.fields["brand"].required = False

        clothing = getattr(self.instance, "clothing", None) if self.instance and self.instance.pk else None
        if clothing:
            self.fields["gender"].initial = clothing.gender
            self.fields["material"].initial = clothing.material
            self.fields["fit"].initial = clothing.fit
            self.fields["care_note"].initial = clothing.care_note

    def clean(self):
        cleaned_data = super().clean()

        category = cleaned_data.get("category")
        brand = cleaned_data.get("brand")
        new_category = (cleaned_data.get("new_category") or "").strip()
        new_brand = (cleaned_data.get("new_brand") or "").strip()
        has_variants = cleaned_data.get("has_variants")
        barcode = (cleaned_data.get("barcode") or "").strip()

        if new_category:
            if not self.business:
                raise forms.ValidationError("Business is required to create a category.")
            category = Category.objects.filter(
                business=self.business,
                name__iexact=new_category,
            ).first()
            if category is None:
                category = Category.objects.create(
                    business=self.business,
                    name=new_category,
                    is_active=True,
                )
            cleaned_data["category"] = category

        if new_brand:
            if not self.business:
                raise forms.ValidationError("Business is required to create a brand.")
            brand = Brand.objects.filter(
                business=self.business,
                name__iexact=new_brand,
            ).first()
            if brand is None:
                brand = Brand.objects.create(
                    business=self.business,
                    name=new_brand,
                    is_active=True,
                )
            cleaned_data["brand"] = brand

        cleaned_data["category"] = category
        cleaned_data["brand"] = brand

        # ❗ important validation
        if self.instance.pk and self.instance.variants.exists() and not has_variants:
            self.add_error("has_variants", "This product already has variants.")

        if has_variants and barcode:
            self.add_error("barcode", "Leave barcode blank for products with variants.")

        if has_variants:
            cleaned_data["track_stock"] = False
            cleaned_data["stock_qty"] = 0
            cleaned_data["min_stock_qty"] = 0

        return cleaned_data
    
class ClothingVariantForm(forms.ModelForm):
    size = forms.ModelChoiceField(queryset=Size.objects.none(), required=False)
    color = forms.ModelChoiceField(queryset=Color.objects.none(), required=False)
    new_size = forms.CharField(max_length=50, required=False)
    new_color = forms.CharField(max_length=50, required=False)

    class Meta:
        model = ItemVariant
        fields = [
            "name",
            "sku",
            "barcode",
            "price",
            "cost_price",
            "track_stock",
            "stock_qty",
            "min_stock_qty",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)
        self.business = business

        if business:
            self.fields["size"].queryset = Size.objects.filter(
                business=business,
                is_active=True,
            ).order_by("sort_order", "name")
            self.fields["color"].queryset = Color.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")
            self.fields["barcode"].required = False
            self.fields["barcode"].help_text = "Leave blank to auto-generate barcode."

        detail = getattr(self.instance, "clothing_detail", None) if self.instance and self.instance.pk else None
        if detail:
            self.fields["size"].initial = detail.size_id
            self.fields["color"].initial = detail.color_id

    def _build_size_code(self, base_name):
        raw = re.sub(r"[^A-Za-z0-9]+", "", (base_name or "").upper())
        base_code = (raw or "SIZE")[:20]

        code = base_code
        counter = 1
        while Size.objects.filter(business=self.business, code=code).exists():
            suffix = str(counter)
            code = f"{base_code[:20 - len(suffix)]}{suffix}"
            counter += 1
        return code

    def clean(self):
        cleaned_data = super().clean()

        size = cleaned_data.get("size")
        color = cleaned_data.get("color")
        new_size = (cleaned_data.get("new_size") or "").strip()
        new_color = (cleaned_data.get("new_color") or "").strip()

        if new_size:
            if not self.business:
                raise forms.ValidationError("Business is required to create a size.")

            size = Size.objects.filter(
                business=self.business,
                name__iexact=new_size,
            ).first()
            if size is None:
                size = Size.objects.create(
                    business=self.business,
                    name=new_size,
                    code=self._build_size_code(new_size),
                    size_type="ALPHA",
                    is_active=True,
                )
            cleaned_data["size"] = size

        if new_color:
            if not self.business:
                raise forms.ValidationError("Business is required to create a color.")

            color = Color.objects.filter(
                business=self.business,
                name__iexact=new_color,
            ).first()
            if color is None:
                color = Color.objects.create(
                    business=self.business,
                    name=new_color,
                    code=(new_color[:20]).upper(),
                    is_active=True,
                )
            cleaned_data["color"] = color

        cleaned_data["size"] = size
        cleaned_data["color"] = color
        return cleaned_data


class ClothingSupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "contact_person",
            "phone_no",
            "email",
            "address",
            "pan_vat_no",
            "is_active",
        ]


class ClothingPurchaseForm(forms.ModelForm):
    purchase_date = forms.DateField(
        input_formats=["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"],
        widget=forms.DateInput(
            attrs={"type": "date"},
            format="%Y-%m-%d",
        ),
    )

    class Meta:
        model = Purchase
        fields = ["supplier", "purchase_no", "purchase_date", "notes"]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)

        # Ensure HTML date input always gets ISO value while still accepting DD/MM/YYYY on submit.
        initial_purchase_date = self.initial.get("purchase_date")
        if initial_purchase_date and hasattr(initial_purchase_date, "strftime"):
            self.initial["purchase_date"] = initial_purchase_date.strftime("%Y-%m-%d")

        if business:
            self.fields["supplier"].queryset = Supplier.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")


class ClothingPurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ["item", "variant", "quantity", "unit_cost"]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)
        self.fields["variant"].required = False

        if business:
            self.fields["item"].queryset = Item.objects.filter(
                business=business,
                item_type="PRODUCT",
                is_active=True,
            ).order_by("name")
            self.fields["variant"].queryset = ItemVariant.objects.filter(
                business=business,
                is_active=True,
            ).select_related("item").order_by("item__name", "name")

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get("item")
        variant = cleaned_data.get("variant")

        if not item:
            return cleaned_data

        if variant and variant.item_id != item.id:
            raise forms.ValidationError("Selected variant does not belong to selected item.")

        if item.has_variants and not variant:
            raise forms.ValidationError("This product requires a variant.")

        if not item.has_variants and variant:
            raise forms.ValidationError("This product does not use variants.")

        return cleaned_data


ClothingPurchaseItemFormSet = inlineformset_factory(
    Purchase,
    PurchaseItem,
    form=ClothingPurchaseItemForm,
    fields=["item", "variant", "quantity", "unit_cost"],
    extra=1,
    can_delete=True,
)


class ClothingStockAdjustmentForm(forms.Form):
    MOVEMENT_CHOICES = [
        ("ADJUSTMENT_IN", "Adjustment In"),
        ("ADJUSTMENT_OUT", "Adjustment Out"),
        ("DAMAGE_OUT", "Damage Out"),
    ]

    item = forms.ModelChoiceField(queryset=Item.objects.none())
    variant = forms.ModelChoiceField(queryset=ItemVariant.objects.none(), required=False)
    movement_type = forms.ChoiceField(choices=MOVEMENT_CHOICES)
    quantity = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)
        if business:
            self.fields["item"].queryset = Item.objects.filter(
                business=business,
                item_type="PRODUCT",
                is_active=True,
            ).order_by("name")
            self.fields["variant"].queryset = ItemVariant.objects.filter(
                business=business,
                is_active=True,
            ).select_related("item").order_by("item__name", "name")

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get("item")
        variant = cleaned_data.get("variant")
        if not item:
            return cleaned_data

        if variant and variant.item_id != item.id:
            raise forms.ValidationError("Selected variant does not belong to selected item.")

        if item.has_variants and not variant:
            raise forms.ValidationError("This product requires a variant.")

        if not item.has_variants and variant:
            raise forms.ValidationError("This product does not use variants.")
