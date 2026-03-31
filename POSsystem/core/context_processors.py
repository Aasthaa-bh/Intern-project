from datetime import timedelta
import logging

from django.utils import timezone
from core.utils import get_business_type_code

logger = logging.getLogger(__name__)


class DummyPreferences:
    theme = "light"


def notifications(request):
    """Add notifications and business context to all pages"""
    if not request.user.is_authenticated:
        print("DEBUG: User not authenticated")
        return {
            'recent_notifications': [],
            'unread_notifications_count': 0,
            'current_business': None,
            'current_business_type': None,
            'preferences': DummyPreferences(),
        }
    
    if not hasattr(request.user, 'business') or not request.user.business:
        print("DEBUG: User has no business")
        return {
            'recent_notifications': [],
            'unread_notifications_count': 0,
            'current_business': None,
            'current_business_type': None,
            'preferences': DummyPreferences(),
        }
    
    try:
        business = request.user.business
        
        # Get business type using the same logic as get_business_type_code
        business_type = None
        if business and business.business_type:
            business_type = business.business_type.name.strip().lower()
        
        # Get user preferences
        preferences = getattr(request.user, "preferences", None)
        if not preferences:
            preferences = DummyPreferences()
        
        print(f"DEBUG: Business = {business.business_name}, Type = {business_type}")
        
        # Only show notifications for clothing businesses
        recent_notifications = []
        unread_count = 0
        
        if business_type == 'clothing':
            from clothing.models import Notification
            from django.db.models import Q
            
            # Determine user role for notification filtering
            user_role = request.user.role
            
            print(f"DEBUG: User role = {user_role}")
            
            # Map user roles to notification target roles
            if user_role in ['SUPERADMIN', 'OWNER']:
                # Admin users see ADMIN and ALL notifications
                role_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
            elif user_role == 'CASHIER':
                # Cashiers see CASHIER and ALL notifications
                role_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
            else:
                # Other roles see only ALL notifications
                role_filter = Q(target_role='ALL')
            
            print(f"DEBUG: Role filter = {role_filter}")
            
            # Get notifications from last 30 days (extended from 3 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            print(f"DEBUG: Thirty days ago = {thirty_days_ago}")
            print(f"DEBUG: Current time = {timezone.now()}")
            
            all_recent = Notification.objects.filter(
                business=business,
                created_at__gte=thirty_days_ago
            ).filter(role_filter).order_by('-created_at')
            
            print(f"DEBUG: Query = {all_recent.query}")
            print(f"DEBUG: Found {all_recent.count()} notifications for business (role: {user_role})")
            
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
            'preferences': preferences,
        }
    except Exception as e:
        logger.error(f"Error in notifications context processor: {e}")
        print(f"DEBUG ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'recent_notifications': [],
            'unread_notifications_count': 0,
            'current_business': None,
            'current_business_type': None,
            'preferences': DummyPreferences(),
        }



def app_context(request):
    if not request.user.is_authenticated:
        return {
            "current_business": None,
            "current_business_type": None,
            "preferences": DummyPreferences(),
            "recent_notifications": [],
            "unread_notifications_count": 0,
        }

    try:
        business = getattr(request.user, "business", None)
        preferences = getattr(request.user, "preferences", None) or DummyPreferences()

        if not business:
            return {
                "current_business": None,
                "current_business_type": None,
                "preferences": preferences,
                "recent_notifications": [],
                "unread_notifications_count": 0,
            }

        business_type = None
        if business.business_type:
            business_type = business.business_type.name.strip().lower()

        recent_notifications = []
        unread_notifications_count = 0

        if business_type == "clothing":
            from clothing.models import Notification

            thirty_days_ago = timezone.now() - timedelta(days=30)

            all_recent = Notification.objects.filter(
                business=business,
                created_at__gte=thirty_days_ago
            ).order_by("-created_at")

            unread_notifications_count = all_recent.filter(is_read=False).count()
            recent_notifications = list(all_recent[:3])

        elif business_type == "restaurant":
            from restaurant.models import RestaurantNotification

            all_recent = RestaurantNotification.objects.filter(
                business=business
            ).order_by("-created_at")

            unread_notifications_count = all_recent.filter(is_read=False).count()
            recent_notifications = list(all_recent[:10])

        return {
            "current_business": business,
            "current_business_type": get_business_type_code(request.user),
            "preferences": preferences,
            "recent_notifications": recent_notifications,
            "unread_notifications_count": unread_notifications_count,
        }

    except Exception as e:
        logger.error(f"Error in app_context processor: {e}", exc_info=True)
        return {
            "current_business": None,
            "current_business_type": None,
            "preferences": DummyPreferences(),
            "recent_notifications": [],
            "unread_notifications_count": 0,
        }


# compatibility aliases
business_context = app_context
notification_context = app_context
notifications = app_context