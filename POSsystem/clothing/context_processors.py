from .models import Offer


def sidebar_offers(request):
    """Add active offers to template context for sidebar"""
    if request.path.startswith('/clothing/'):
        from core.models import Business
        business = request.user.business if request.user.is_authenticated else Business.objects.first()
        
        if business:
            offers = Offer.objects.filter(
                business=business,
                status='ACTIVE'
            ).order_by('-created_at')[:10]  # Show max 10 offers in sidebar
            
            return {'sidebar_offers': offers}
    
    return {}
