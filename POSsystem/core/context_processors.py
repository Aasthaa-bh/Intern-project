from core.utils import get_business_type_code
from restaurant.models import RestaurantNotification

def business_context(request):
    business = getattr(request.user, "business", None) if request.user.is_authenticated else None
    
    unread_notifications_count = 0
    recent_notifications = []
    
    if business:
        unread_notifications_count = RestaurantNotification.objects.filter(business=business, is_read=False).count()
        recent_notifications = RestaurantNotification.objects.filter(business=business).order_by('-created_at')[:10]
        
    return {
        "current_business": business,
        "current_business_type": get_business_type_code(request.user) if request.user.is_authenticated else None,
        "unread_notifications_count": unread_notifications_count,
        "recent_notifications": recent_notifications,
    }