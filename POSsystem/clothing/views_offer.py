from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from decimal import Decimal

from .models import Offer, OfferUsage
from .forms import OfferForm
from core.decorators import owner_required


def offer_dashboard(request):
    """Dashboard with offer statistics and insights"""
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    
    # Auto-update expired offers
    today = timezone.now().date()
    Offer.objects.filter(business=business, status='ACTIVE', end_date__lt=today).update(status='EXPIRED')
    
    # Basic stats
    total_offers = Offer.objects.filter(business=business).count()
    active_offers = Offer.objects.filter(business=business, status='ACTIVE').count()
    inactive_offers = Offer.objects.filter(business=business, status='INACTIVE').count()
    expired_offers = Offer.objects.filter(business=business, status='EXPIRED').count()
    
    # Usage stats
    usage_stats = OfferUsage.objects.filter(offer__business=business).aggregate(
        total_usage=Count('id'),
        total_discount=Sum('discount_amount'),
        avg_discount=Avg('discount_amount')
    )
    
    # Offers by type
    offers_by_type = Offer.objects.filter(business=business).values('offer_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate percentages
    by_type_stats = []
    for item in offers_by_type:
        percentage = (item['count'] / total_offers * 100) if total_offers > 0 else 0
        by_type_stats.append({
            'type': item['offer_type'],
            'type_display': dict(Offer.OFFER_TYPE_CHOICES).get(item['offer_type'], item['offer_type']),
            'count': item['count'],
            'percentage': round(percentage, 1)
        })
    
    # Top performing offers
    top_offers = Offer.objects.filter(business=business).annotate(
        usage_count=Count('usages'),
        total_discount=Sum('usages__discount_amount')
    ).filter(usage_count__gt=0).order_by('-usage_count')[:10]
    
    # Recent usage
    recent_usage = OfferUsage.objects.filter(
        offer__business=business
    ).select_related('offer', 'order').order_by('-applied_at')[:10]
    
    context = {
        'stats': {
            'total_offers': total_offers,
            'active_offers': active_offers,
            'inactive_offers': inactive_offers,
            'expired_offers': expired_offers,
            'total_usage': usage_stats['total_usage'] or 0,
            'total_discount': usage_stats['total_discount'] or Decimal('0.00'),
            'avg_discount': usage_stats['avg_discount'] or Decimal('0.00'),
            'by_type': by_type_stats,
        },
        'top_offers': top_offers,
        'recent_usage': recent_usage,
    }
    
    return render(request, 'clothing/offer_dashboard.html', context)


def offer_list(request):
    """List all clothing offers"""
    # Get first business if user not logged in
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    
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


def offer_create(request):
    """Create new clothing offer"""
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    
    if request.method == 'POST':
        form = OfferForm(request.POST, business=business)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.business = business
            if request.user.is_authenticated:
                offer.created_by = request.user
            else:
                # Get first user from business or create a default one
                from accounts.models import User
                offer.created_by = User.objects.filter(business=business).first() or User.objects.first()
            offer.save()
            
            # Save many-to-many relationships
            form.save_m2m()
            
            messages.success(request, f'Offer "{offer.offer_name}" created successfully!')
            return redirect('clothing_offer_list')
    else:
        form = OfferForm(business=business)
    
    return render(request, 'clothing/offer_form.html', {
        'form': form,
        'title': 'Create New Offer',
        'button_text': 'Create Offer'
    })


def offer_edit(request, offer_id):
    """Edit existing clothing offer"""
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
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
        'form': form,
        'offer': offer,
        'title': 'Edit Offer',
        'button_text': 'Update Offer'
    })


def offer_delete(request, offer_id):
    """Delete clothing offer"""
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    if request.method == 'POST':
        offer_name = offer.offer_name
        offer.delete()
        messages.success(request, f'Offer "{offer_name}" deleted successfully!')
        return redirect('clothing_offer_list')
    
    return render(request, 'clothing/offer_confirm_delete.html', {'offer': offer})


def offer_detail(request, offer_id):
    """View clothing offer details and usage statistics"""
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    usages = OfferUsage.objects.filter(offer=offer).select_related('order')
    
    context = {
        'offer': offer,
        'total_usage': usages.count(),
        'total_discount': usages.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00'),
        'recent_usages': usages.order_by('-applied_at')[:10],
    }
    return render(request, 'clothing/offer_detail_simple.html', context)


def offer_toggle_status(request, offer_id):
    """Toggle offer status between ACTIVE and INACTIVE"""
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
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


# Helper functions for discount calculation
def get_applicable_offers(business, subtotal, item=None, variant=None, category=None, customer=None):
    """Get all applicable offers for a given order"""
    today = timezone.now().date()
    
    offers = Offer.objects.filter(
        business=business,
        status='ACTIVE',
        start_date__lte=today,
        end_date__gte=today,
        minimum_purchase__lte=subtotal
    )
    
    applicable_offers = []
    for offer in offers:
        if offer.offer_type in ['PERCENTAGE', 'FLAT', 'SEASONAL']:
            applicable_offers.append(offer)
        elif offer.offer_type == 'PRODUCT' and item and offer.product_id == item.id:
            applicable_offers.append(offer)
        elif offer.offer_type == 'VARIANT' and variant and offer.variants.filter(id=variant.id).exists():
            applicable_offers.append(offer)
        elif offer.offer_type == 'CATEGORY' and category and offer.category_id == category.id:
            applicable_offers.append(offer)
        elif offer.offer_type == 'LOYALTY' and customer:
            applicable_offers.append(offer)
    
    return applicable_offers


def calculate_best_offer(business, subtotal, items=None, customer=None):
    """Calculate the best offer discount for an order"""
    best_offer = None
    best_discount = Decimal('0.00')
    
    general_offers = get_applicable_offers(business, subtotal, customer=customer)
    
    for offer in general_offers:
        discount = offer.calculate_discount(subtotal)
        if discount > best_discount:
            best_discount = discount
            best_offer = offer
    
    if items:
        for item_data in items:
            item = item_data.get('item')
            variant = item_data.get('variant')
            category = item.category if item else None
            
            item_offers = get_applicable_offers(business, subtotal, item=item, variant=variant, category=category, customer=customer)
            
            for offer in item_offers:
                discount = offer.calculate_discount(subtotal, item=item, variant=variant, category=category)
                if discount > best_discount:
                    best_discount = discount
                    best_offer = offer
    
    return best_offer, best_discount
