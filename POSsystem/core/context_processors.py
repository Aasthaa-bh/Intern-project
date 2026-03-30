from datetime import timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def notifications(request):
    """Add notifications and business context to all pages"""
    if not request.user.is_authenticated:
        print("DEBUG: User not authenticated")
        return {
            'recent_notifications': [],
            'unread_notifications_count': 0,
            'current_business': None,
            'current_business_type': None,
        }
    
    if not hasattr(request.user, 'business') or not request.user.business:
        print("DEBUG: User has no business")
        return {
            'recent_notifications': [],
            'unread_notifications_count': 0,
            'current_business': None,
            'current_business_type': None,
        }
    
    try:
        business = request.user.business
        
        # Get business type using the same logic as get_business_type_code
        business_type = None
        if business and business.business_type:
            business_type = business.business_type.name.strip().lower()
        
        print(f"DEBUG: Business = {business.business_name}, Type = {business_type}")
        
        # Only show notifications for clothing businesses
        recent_notifications = []
        unread_count = 0
        
        if business_type == 'clothing':
            from clothing.models import Notification
            from datetime import timedelta
            
            # Get notifications from last 30 days (extended from 3 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            all_recent = Notification.objects.filter(
                business=business,
                created_at__gte=thirty_days_ago
            ).order_by('-created_at')
            
            print(f"DEBUG: Found {all_recent.count()} notifications for business")
            
            # Count unread before slicing
            unread_count = all_recent.filter(is_read=False).count()
            
            # Get top 3 for display (reduced from 10)
            recent_notifications = list(all_recent[:3])
            
            print(f"DEBUG: Unread count = {unread_count}, Recent notifications = {len(recent_notifications)}")
        
        return {
            'recent_notifications': recent_notifications,
            'unread_notifications_count': unread_count,
            'current_business': business,
            'current_business_type': business_type,
        }
    except Exception as e:
        logger.error(f"Error in notifications context processor: {e}")
        print(f"DEBUG ERROR: {e}")
        return {
            'recent_notifications': [],
            'unread_notifications_count': 0,
            'current_business': None,
            'current_business_type': None,
        }

class DummyPreferences:
    theme = "light"


def business_context(request):
    current_business = None
    current_business_type = None
    preferences = DummyPreferences()

    if request.user.is_authenticated:
        current_business = getattr(request.user, "business", None)

        if current_business:
            business_type_obj = getattr(current_business, "business_type", None)
            if business_type_obj:
                current_business_type = getattr(business_type_obj, "name", None)

        user_preferences = getattr(request.user, "preferences", None)
        if user_preferences:
            preferences = user_preferences

    return {
        "current_business": current_business,
        "current_business_type": current_business_type,
        "preferences": preferences,
    }


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            "recent_notifications": [],
            "unread_notifications_count": 0,
        }

    return {
        "recent_notifications": [],
        "unread_notifications_count": 0,
    }