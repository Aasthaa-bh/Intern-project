from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
import re

from pos.models import Brand, Category, Item, ItemVariant, Purchase, PurchaseItem, Supplier

from .models import ClothingItem, ClothingVariantDetail, Color, Size


def _variant_descriptor(variant):
    detail = getattr(variant, "clothing_detail", None)
    parts = []

    if detail and getattr(detail, "color_id", None):
        parts.append(detail.color.name)
    if detail and getattr(detail, "size_id", None):
        parts.append(detail.size.name)

    if parts:
        return " / ".join(parts)
    return (variant.name or "").strip() or f"Variant {variant.pk}"


class ClothingVariantChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.item.name} / {_variant_descriptor(obj)}"


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
            "description",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)
        self.business = business
        self.has_variants = bool(
            self.instance
            and self.instance.pk
            and self.instance.variants.exists()
        )

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

        if self.has_variants:
            self.fields["track_stock"].disabled = True
            self.fields["stock_qty"].disabled = True
            self.fields["min_stock_qty"].disabled = True
            self.fields["track_stock"].help_text = "Parent product stock is disabled because this product uses variants."
            self.fields["stock_qty"].help_text = "Stock is managed on variants for this product."
            self.fields["min_stock_qty"].help_text = "Minimum stock is managed on variants for this product."

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

        # Keep selected values when no new text is entered.
        cleaned_data["category"] = category
        cleaned_data["brand"] = brand

        if self.has_variants:
            cleaned_data["track_stock"] = False
            cleaned_data["stock_qty"] = Decimal("0")
            cleaned_data["min_stock_qty"] = Decimal("0")
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
        product = kwargs.pop("product", None)
        super().__init__(*args, **kwargs)
        self.business = business
        self.product = product or getattr(self.instance, "item", None)

        creating = not (self.instance and self.instance.pk)
        if creating:
            self.fields["name"].required = False
            self.fields["sku"].required = False

        if business:
            self.fields["size"].queryset = Size.objects.filter(
                business=business,
                is_active=True,
            ).order_by("sort_order", "name")
            self.fields["color"].queryset = Color.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")

        detail = getattr(self.instance, "clothing_detail", None) if self.instance and self.instance.pk else None
        if detail:
            self.fields["size"].initial = detail.size_id
            self.fields["color"].initial = detail.color_id

        if creating and self.product:
            self.fields["name"].initial = self._build_variant_name(self.product.name)
            self.fields["sku"].initial = self._build_variant_sku(self.product.sku)
            self.fields["price"].initial = self.product.price
            self.fields["cost_price"].initial = self.product.cost_price

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

    def _build_variant_name(self, base_name):
        if not self.product:
            return (base_name or "Variant").strip() or "Variant"

        base = (base_name or self.product.name or "Variant").strip()
        candidate = base
        counter = 1
        while ItemVariant.objects.filter(item=self.product, name__iexact=candidate).exists():
            counter += 1
            candidate = f"{base} {counter}"
        return candidate

    def _build_variant_sku(self, base_sku):
        base_source = (base_sku or "").strip()
        if not base_source and self.product:
            base_source = (self.product.sku or "").strip()
        if not base_source and self.product:
            base_source = f"ITEM{self.product.id or ''}"
        if not base_source:
            base_source = "SKU"

        candidate = base_source
        counter = 1
        business = self.business or (self.product.business if self.product else None)
        lookup = ItemVariant.objects.filter(sku__iexact=candidate)
        if business:
            lookup = lookup.filter(business=business)
        while lookup.exists():
            counter += 1
            candidate = f"{base_source}-{counter}"
            lookup = ItemVariant.objects.filter(sku__iexact=candidate)
            if business:
                lookup = lookup.filter(business=business)
        return candidate

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

        creating = not (self.instance and self.instance.pk)
        if creating and self.product:
            if not (cleaned_data.get("name") or "").strip():
                cleaned_data["name"] = self._build_variant_name(self.product.name)
            if not (cleaned_data.get("sku") or "").strip():
                cleaned_data["sku"] = self._build_variant_sku(self.product.sku)

            if cleaned_data.get("price") is None:
                cleaned_data["price"] = self.product.price
            if cleaned_data.get("cost_price") is None:
                cleaned_data["cost_price"] = self.product.cost_price

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
            "notes",
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
    variant = ClothingVariantChoiceField(queryset=ItemVariant.objects.none(), required=False)

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
            ).select_related(
                "item",
                "clothing_detail__size",
                "clothing_detail__color",
            ).order_by("item__name", "name")

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get("item")
        variant = cleaned_data.get("variant")

        if variant and item and variant.item_id != item.id:
            raise forms.ValidationError("Selected variant does not belong to selected item.")
        if item and item.variants.exists() and not variant:
            raise forms.ValidationError("Select a variant for products that manage stock by variant.")

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
    variant = ClothingVariantChoiceField(queryset=ItemVariant.objects.none(), required=False)
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
            ).select_related(
                "item",
                "clothing_detail__size",
                "clothing_detail__color",
            ).order_by("item__name", "name")

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get("item")
        variant = cleaned_data.get("variant")
        if variant and item and variant.item_id != item.id:
            raise forms.ValidationError("Selected variant does not belong to selected item.")
        if item and item.variants.exists() and not variant:
            raise forms.ValidationError("Select a variant for products that manage stock by variant.")
        return cleaned_data


# ── Cashier Forms ─────────────────────────────────────────────────────────────

from django.contrib.auth import get_user_model, authenticate

User = get_user_model()


class CashierProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = field.name in ("username",)

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email:
            qs = User.objects.filter(email=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This email is already in use.")
        return email


class CashierChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        pwd = self.cleaned_data.get("current_password")
        if self.user and not self.user.check_password(pwd):
            raise forms.ValidationError("Current password is incorrect.")
        return pwd

    def clean(self):
        cleaned_data = super().clean()
        new = cleaned_data.get("new_password")
        confirm = cleaned_data.get("confirm_password")
        if new and confirm and new != confirm:
            raise forms.ValidationError("New passwords do not match.")
        return cleaned_data
