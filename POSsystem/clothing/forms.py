from django import forms
from .models import Offer
from pos.models import Item, Category, ItemVariant


class OfferForm(forms.ModelForm):
    """Form for creating and editing clothing offers"""
    
    OFFER_NAME_CHOICES = [
        ('', 'Select Offer Name'),
        ('Dashain Sale', 'Dashain Sale'),
        ('Tihar Offer', 'Tihar Offer'),
        ('New Year Sale', 'New Year Sale'),
        ('Summer Sale', 'Summer Sale'),
        ('Winter Sale', 'Winter Sale'),
        ('Clearance Sale', 'Clearance Sale'),
        ('Flash Sale', 'Flash Sale'),
        ('Weekend Special', 'Weekend Special'),
        ('Buy 1 Get 1', 'Buy 1 Get 1'),
        ('Flat Discount', 'Flat Discount'),
    ]
    
    offer_name = forms.ChoiceField(
        choices=OFFER_NAME_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        })
    )
    
    variants = forms.ModelMultipleChoiceField(
        queryset=ItemVariant.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Select Variants (Size/Color)"
    )
    
    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        
        if business:
            self.fields['product'].queryset = Item.objects.filter(
                business=business,
                is_active=True
            )
            self.fields['category'].queryset = Category.objects.filter(
                business=business,
                is_active=True
            )
            
            # Load variants for the selected product
            if self.instance and self.instance.pk and self.instance.product:
                variants_qs = ItemVariant.objects.filter(
                    item=self.instance.product,
                    is_active=True
                ).select_related('clothing_detail__size', 'clothing_detail__color')
                self.fields['variants'].queryset = variants_qs
                self.fields['variants'].label_from_instance = self._variant_label
            elif self.data.get('product'):
                try:
                    product_id = int(self.data.get('product'))
                    variants_qs = ItemVariant.objects.filter(
                        item_id=product_id,
                        is_active=True
                    ).select_related('clothing_detail__size', 'clothing_detail__color')
                    self.fields['variants'].queryset = variants_qs
                    self.fields['variants'].label_from_instance = self._variant_label
                except (ValueError, TypeError):
                    self.fields['variants'].queryset = ItemVariant.objects.none()
            else:
                self.fields['variants'].queryset = ItemVariant.objects.none()
        else:
            self.fields['product'].queryset = Item.objects.none()
            self.fields['category'].queryset = Category.objects.none()
            self.fields['variants'].queryset = ItemVariant.objects.none()
        
        self.fields['product'].required = False
        self.fields['category'].required = False
        self.fields['variants'].required = False
    
    def _variant_label(self, obj):
        """Custom label for variant display"""
        try:
            detail = obj.clothing_detail
            size_name = detail.size.name if detail.size else "N/A"
            color_name = detail.color.name if detail.color else "N/A"
            return f"{size_name} / {color_name} (Stock: {obj.stock_qty})"
        except:
            return f"{obj.name} (Stock: {obj.stock_qty})"
    
    class Meta:
        model = Offer
        fields = [
            'offer_name',
            'offer_type',
            'description',
            'discount_value',
            'start_date',
            'end_date',
            'product',
            'variants',
            'category',
            'minimum_purchase',
            'status',
        ]
        widgets = {
            'offer_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'id': 'id_offer_type'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'e.g., 10 for 10% or 500 for Rs 500',
                'step': '0.01'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'date'
            }),
            'product': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'id': 'id_product'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'id': 'id_category'
            }),
            'minimum_purchase': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': '0',
                'step': '0.01'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        product = cleaned_data.get('product')
        variants = cleaned_data.get('variants')
        category = cleaned_data.get('category')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        discount_value = cleaned_data.get('discount_value')
        
        if offer_type == 'PRODUCT' and not product:
            self.add_error('product', 'Product is required for Product Wise Offer')
        
        if offer_type == 'VARIANT':
            if not product:
                self.add_error('product', 'Product is required for Variant Wise Offer')
            if not variants or variants.count() == 0:
                self.add_error('variants', 'At least one variant is required for Variant Wise Offer')
        
        if offer_type == 'CATEGORY' and not category:
            self.add_error('category', 'Category is required for Category Wise Offer')
        
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', 'End date must be after start date')
        
        if discount_value:
            if offer_type in ['PERCENTAGE', 'SEASONAL', 'LOYALTY', 'CATEGORY', 'VARIANT']:
                if discount_value > 100:
                    self.add_error('discount_value', 'Percentage discount cannot exceed 100%')
                if discount_value <= 0:
                    self.add_error('discount_value', 'Discount value must be greater than 0')
            elif discount_value <= 0:
                self.add_error('discount_value', 'Discount value must be greater than 0')
        
from django.forms import inlineformset_factory
import re
from decimal import Decimal

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
    category_name = forms.CharField(max_length=100, required=False)
    brand_name = forms.CharField(max_length=100, required=False)

    class Meta:
        model = Item
        fields = [
            "name",
            "sku",
            "barcode",
            "category",
            "brand",
            "price",
            "description",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)
        self.business = business
        self.fields["price"].required = False
        self.fields["price"].widget = forms.HiddenInput()
        if self.instance and self.instance.pk and self.instance.price is not None:
            self.fields["price"].initial = self.instance.price
        else:
            self.fields["price"].initial = Decimal("0.00")
        self.fields["category_name"].widget.attrs.update({"placeholder": "Select or type category"})
        self.fields["brand_name"].widget.attrs.update({"placeholder": "Select or type brand"})
        self.category_name_options = []
        self.brand_name_options = []

        if business:
            self.fields["category"].queryset = Category.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")
            self.fields["brand"].queryset = Brand.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")
            self.category_name_options = list(self.fields["category"].queryset.values_list("name", flat=True))
            self.brand_name_options = list(self.fields["brand"].queryset.values_list("name", flat=True))

        self.fields["category"].required = False
        self.fields["brand"].required = False

        if self.instance and self.instance.pk:
            self.fields["category_name"].initial = self.instance.category.name if self.instance.category_id else ""
            self.fields["brand_name"].initial = self.instance.brand.name if self.instance.brand_id else ""

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
        category_name = (cleaned_data.get("category_name") or "").strip()
        brand_name = (cleaned_data.get("brand_name") or "").strip()

        if category_name:
            if not self.business:
                raise forms.ValidationError("Business is required to create a category.")
            category = Category.objects.filter(
                business=self.business,
                name__iexact=category_name,
            ).first()
            if category is None:
                category = Category.objects.create(
                    business=self.business,
                    name=category_name,
                    is_active=True,
                )
            cleaned_data["category"] = category

        if brand_name:
            if not self.business:
                raise forms.ValidationError("Business is required to create a brand.")
            brand = Brand.objects.filter(
                business=self.business,
                name__iexact=brand_name,
            ).first()
            if brand is None:
                brand = Brand.objects.create(
                    business=self.business,
                    name=brand_name,
                    is_active=True,
                )
            cleaned_data["brand"] = brand

        cleaned_data["category"] = category
        cleaned_data["brand"] = brand
        if cleaned_data.get("price") in (None, ""):
            if self.instance and self.instance.pk and self.instance.price is not None:
                cleaned_data["price"] = self.instance.price
            else:
                cleaned_data["price"] = Decimal("0.00")
        return cleaned_data


class ClothingVariantForm(forms.ModelForm):
    size = forms.ModelChoiceField(queryset=Size.objects.none(), required=False)
    color = forms.ModelChoiceField(queryset=Color.objects.none(), required=False)
    size_name = forms.CharField(max_length=50, required=False)
    color_name = forms.CharField(max_length=50, required=False)

    class Meta:
        model = ItemVariant
        fields = [
            "name",
            "sku",
            "barcode",
            "price",
            "track_stock",
            "min_stock_qty",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        product = kwargs.pop("product", None)
        super().__init__(*args, **kwargs)
        self.business = business
        self.product = product or getattr(self.instance, "item", None)
        self.fields["size_name"].widget.attrs.update({
            "placeholder": "Select or type size",
            "list": "size-name-options",
        })
        self.fields["color_name"].widget.attrs.update({
            "placeholder": "Select or type color",
            "list": "color-name-options",
        })
        self.size_name_options = []
        self.color_name_options = []

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
            self.size_name_options = list(self.fields["size"].queryset.values_list("name", flat=True))
            self.color_name_options = list(self.fields["color"].queryset.values_list("name", flat=True))

        detail = getattr(self.instance, "clothing_detail", None) if self.instance and self.instance.pk else None
        if detail:
            self.fields["size"].initial = detail.size_id
            self.fields["color"].initial = detail.color_id
            self.fields["size_name"].initial = detail.size.name if detail.size_id else ""
            self.fields["color_name"].initial = detail.color.name if detail.color_id else ""

        if creating and self.product:
            self.fields["name"].initial = self._build_variant_name(self.product.name)
            self.fields["sku"].initial = self._build_variant_sku(self.product.sku)
            self.fields["price"].initial = self.product.price
            self.fields["cost_price"].initial = self.product.cost_price
            self.fields["barcode"].help_text = "Leave blank to auto-generate barcode."
                    
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
        size_name = (cleaned_data.get("size_name") or "").strip()
        color_name = (cleaned_data.get("color_name") or "").strip()

        if size_name:
            if not self.business:
                raise forms.ValidationError("Business is required to create a size.")

            size = Size.objects.filter(
                business=self.business,
                name__iexact=size_name,
            ).first()
            if size is None:
                size = Size.objects.create(
                    business=self.business,
                    name=size_name,
                    code=self._build_size_code(size_name),
                    size_type="ALPHA",
                    is_active=True,
                )
            cleaned_data["size"] = size
        else:
            cleaned_data["size"] = None

        if color_name:
            if not self.business:
                raise forms.ValidationError("Business is required to create a color.")

            color = Color.objects.filter(
                business=self.business,
                name__iexact=color_name,
            ).first()
            if color is None:
                color = Color.objects.create(
                    business=self.business,
                    name=color_name,
                    code=(color_name[:20]).upper(),
                    is_active=True,
                )
            cleaned_data["color"] = color
        else:
            cleaned_data["color"] = None

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

        business = self.business or getattr(self.product, "business", None) or getattr(self.instance, "business", None)

        barcode = (cleaned_data.get("barcode") or "").strip() or None
        sku = (cleaned_data.get("sku") or "").strip()
        name = (cleaned_data.get("name") or "").strip()

        cleaned_data["barcode"] = barcode
        cleaned_data["sku"] = sku
        cleaned_data["name"] = name

        if business and barcode:
            barcode_qs = ItemVariant.objects.filter(
                business=business,
                barcode__iexact=barcode,
            )
            if self.instance and self.instance.pk:
                barcode_qs = barcode_qs.exclude(pk=self.instance.pk)

            if barcode_qs.exists():
                self.add_error("barcode", "This barcode already exists for another variant.")

        if business and sku:
            sku_qs = ItemVariant.objects.filter(
                business=business,
                sku__iexact=sku,
            )
            if self.instance and self.instance.pk:
                sku_qs = sku_qs.exclude(pk=self.instance.pk)

            if sku_qs.exists():
                self.add_error("sku", "This SKU already exists for another variant.")

        if self.product and name:
            name_qs = ItemVariant.objects.filter(
                item=self.product,
                name__iexact=name,
            )
            if self.instance and self.instance.pk:
                name_qs = name_qs.exclude(pk=self.instance.pk)

            if name_qs.exists():
                self.add_error("name", "This variant name already exists for this product.")

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone_no"].required = True
        self.fields["pan_vat_no"].required = True


class ClothingPurchaseForm(forms.ModelForm):
    new_supplier_name = forms.CharField(max_length=150, required=False)
    new_supplier_phone = forms.CharField(max_length=20, required=False)
    new_supplier_pan = forms.CharField(max_length=50, required=False)

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
        self.business = business
        self.fields["supplier"].required = False

        # Ensure HTML date input always gets ISO value while still accepting DD/MM/YYYY on submit.
        initial_purchase_date = self.initial.get("purchase_date")
        if initial_purchase_date and hasattr(initial_purchase_date, "strftime"):
            self.initial["purchase_date"] = initial_purchase_date.strftime("%Y-%m-%d")

        if business:
            self.fields["supplier"].queryset = Supplier.objects.filter(
                business=business,
                is_active=True,
            ).order_by("name")

    def clean_purchase_no(self):
        purchase_no = (self.cleaned_data.get("purchase_no") or "").strip()
        if not purchase_no:
            return purchase_no

        lookup = Purchase.objects.filter(purchase_no__iexact=purchase_no)
        if self.business is not None:
            lookup = lookup.filter(business=self.business)

        if self.instance and self.instance.pk:
            lookup = lookup.exclude(pk=self.instance.pk)

        if lookup.exists():
            raise forms.ValidationError("Invoice No is already used. Please enter a different one.")

        return purchase_no

    def clean(self):
        cleaned_data = super().clean()
        supplier = cleaned_data.get("supplier")
        new_supplier_name = (cleaned_data.get("new_supplier_name") or "").strip()
        new_supplier_phone = (cleaned_data.get("new_supplier_phone") or "").strip()
        new_supplier_pan = (cleaned_data.get("new_supplier_pan") or "").strip()

        if new_supplier_name:
            if not self.business:
                raise forms.ValidationError("Business is required to create a supplier.")

            if not new_supplier_phone:
                self.add_error("new_supplier_phone", "Phone is required for new supplier.")

            if not new_supplier_pan:
                self.add_error("new_supplier_pan", "PAN/VAT is required for new supplier.")

            if self.errors:
                return cleaned_data

            supplier = Supplier.objects.filter(
                business=self.business,
                name__iexact=new_supplier_name,
            ).first()

            if supplier is None:
                supplier = Supplier.objects.create(
                    business=self.business,
                    name=new_supplier_name,
                    phone_no=new_supplier_phone,
                    pan_vat_no=new_supplier_pan,
                    is_active=True,
                )

            cleaned_data["supplier"] = supplier

        if not cleaned_data.get("supplier"):
            raise forms.ValidationError("Select a supplier or enter a new supplier name.")

        return cleaned_data


class ClothingPurchaseItemForm(forms.ModelForm):
    variant = ClothingVariantChoiceField(queryset=ItemVariant.objects.none(), required=False)

    class Meta:
        model = PurchaseItem
        fields = ["item", "variant", "quantity", "unit_cost", "selling_price"]

    def __init__(self, *args, **kwargs):
        business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)
        self.fields["variant"].required = False
        self.fields["selling_price"].required = False

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

        if not (self.instance and self.instance.pk):
            initial_item = self.initial.get("item")
            initial_variant = self.initial.get("variant")
            if initial_variant and getattr(initial_variant, "price", None) is not None:
                self.fields["selling_price"].initial = initial_variant.price
            elif initial_item and getattr(initial_item, "price", None) is not None:
                self.fields["selling_price"].initial = initial_item.price

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
    fields=["item", "variant", "quantity", "unit_cost", "selling_price"],
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
