from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django import forms
from decimal import Decimal

from .models import Offer, OfferUsage
from pos.models import Item, Category
from core.decorators import business_required


# ==================== FORMS ====================

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ['offer_name', 'offer_type', 'description', 'discount_value', 
                  'start_date', 'end_date', 'product', 'category', 'minimum_purchase', 'status']
        widgets = {
            'offer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Dashain Sale'}),
            'offer_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_offer_type'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'minimum_purchase': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        if business:
            self.fields['product'].queryset = Item.objects.filter(business=business, is_active=True)
            self.fields['category'].queryset = Category.objects.filter(business=business, is_active=True)
        self.fields['product'].required = False
        self.fields['category'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        if offer_type == 'PRODUCT' and not cleaned_data.get('product'):
            self.add_error('product', 'Product is required for Product Wise Offer')
        if offer_type == 'CATEGORY' and not cleaned_data.get('category'):
            self.add_error('category', 'Category is required for Category Wise Offer')
        return cleaned_data


# ==================== VIEWS ====================

@login_required
@business_required
def offer_list(request):
    business = request.user.business
    status_filter = request.GET.get('status', '')
    offer_type_filter = request.GET.get('offer_type', '')
    search = request.GET.get('search', '')
    
    offers = Offer.objects.filter(business=business)
    
    if status_filter:
        offers = offers.filter(status=status_filter)
    if offer_type_filter:
        offers = offers.filter(offer_type=offer_type_filter)
    if search:
        offers = offers.filter(Q(offer_name__icontains=search) | Q(description__icontains=search))
    
    # Auto-update expired offers
    today = timezone.now().date()
    offers.filter(status='ACTIVE', end_date__lt=today).update(status='EXPIRED')
    
    offers = offers.select_related('product', 'category', 'created_by')
    
    context = {
        'offers': offers,
        'active_count': offers.filter(status='ACTIVE').count(),
        'inactive_count': offers.filter(status='INACTIVE').count(),
        'expired_count': offers.filter(status='EXPIRED').count(),
        'status_filter': status_filter,
        'offer_type_filter': offer_type_filter,
        'search': search,
        'offer_types': Offer.OFFER_TYPE_CHOICES,
        'status_choices': Offer.STATUS_CHOICES,
    }
    return render(request, 'clothing/offer_list.html', context)


@login_required
@business_required
def offer_create(request):
    business = request.user.business
    if request.method == 'POST':
        form = OfferForm(request.POST, business=business)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.business = business
            offer.created_by = request.user
            offer.save()
            messages.success(request, f'Offer "{offer.offer_name}" created successfully!')
            return redirect('clothing_offer_list')
    else:
        form = OfferForm(business=business)
    
    return render(request, 'clothing/offer_form.html', {
        'form': form, 'title': 'Create New Offer', 'button_text': 'Create Offer'
    })


@login_required
@business_required
def offer_edit(request, offer_id):
    business = request.user.business
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer, business=business)
        if form.is_valid():
            form.save()
            messages.success(request, f'Offer "{offer.offer_name}" updated successfully!')
            return redirect('clothing_offer_list')
    else:
        form = OfferForm(instance=offer, business=business)
    
    return render(request, 'clothing/offer_form.html', {
        'form': form, 'offer': offer, 'title': 'Edit Offer', 'button_text': 'Update Offer'
    })


@login_required
@business_required
def offer_delete(request, offer_id):
    business = request.user.business
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    if request.method == 'POST':
        offer_name = offer.offer_name
        offer.delete()
        messages.success(request, f'Offer "{offer_name}" deleted successfully!')
        return redirect('clothing_offer_list')
    
    return render(request, 'clothing/offer_confirm_delete.html', {'offer': offer})


@login_required
@business_required
def offer_detail(request, offer_id):
    business = request.user.business
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    usages = OfferUsage.objects.filter(offer=offer).select_related('order')
    
    context = {
        'offer': offer,
        'total_usage': usages.count(),
        'total_discount': usages.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00'),
        'recent_usages': usages.order_by('-applied_at')[:10],
    }
    return render(request, 'clothing/offer_detail.html', context)


@login_required
@business_required
def offer_toggle_status(request, offer_id):
    business = request.user.business
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    if request.method == 'POST':
        if offer.status == 'ACTIVE':
            offer.status = 'INACTIVE'
            messages.success(request, f'Offer "{offer.offer_name}" deactivated.')
        elif offer.status == 'INACTIVE':
            offer.status = 'ACTIVE'
            messages.success(request, f'Offer "{offer.offer_name}" activated.')
        else:
            messages.error(request, 'Cannot toggle expired offer status.')
            return redirect('clothing_offer_list')
        offer.save()
    
    return redirect('clothing_offer_list')
