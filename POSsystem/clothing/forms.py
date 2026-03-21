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
            'class': 'form-control',
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
                'class': 'form-control',
                'id': 'id_offer_type'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 10 for 10% or 500 for Rs 500',
                'step': '0.01'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'product': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_product'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_category'
            }),
            'minimum_purchase': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'step': '0.01'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
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
        
        return cleaned_data
