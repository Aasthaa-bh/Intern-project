from core.utils import get_business_type_code
    
from .models import Offer, Notification
from datetime import timedelta
from django.utils import timezone



def business_context(request):
    business = getattr(request.user, "business", None) if request.user.is_authenticated else None
    return {
        "current_business": business,
        "current_business_type": get_business_type_code(request.user) if request.user.is_authenticated else None,
    }

def sidebar_offers(request):
    """Add active offers and notifications to template context"""
    if request.path.startswith('/clothing/'):
        from core.models import Business
        business = request.user.business if request.user.is_authenticated else Business.objects.first()
        
        if business:
            offers = Offer.objects.filter(
                business=business,
                status='ACTIVE'
            ).order_by('-created_at')[:10]
            
            # Get notifications from last 3 days
            three_days_ago = timezone.now() - timedelta(days=3)
            all_recent = Notification.objects.filter(
                business=business,
                created_at__gte=three_days_ago
            ).order_by('-created_at')
            
            # Count unread BEFORE slicing
            unread_count = all_recent.filter(is_read=False).count()
            
            # Get top 10 for display
            recent_notifications = list(all_recent[:10])
            
            return {
                'sidebar_offers': offers,
                'recent_notifications': recent_notifications,
                'unread_notifications_count': unread_count,
            }
    
    return {}