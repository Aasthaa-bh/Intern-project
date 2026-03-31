from datetime import timedelta
import logging

from django.utils import timezone
from core.utils import get_business_type_code

logger = logging.getLogger(__name__)


class DummyPreferences:
    theme = "light"


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
            from django.db.models import Q

            user_role = getattr(request.user, "role", "ALL").upper()
            
            # Filter logic for Restaurant
            if user_role in ["OWNER", "SUPERADMIN"]:
                # Owners/Admins see everything
                noti_filter = Q(target_role__in=["ALL", "WAITER", "KITCHEN", "CASHIER", "OWNER"])
            elif user_role in ["WAITER", "KITCHEN", "CASHIER"]:
                # Staff see global notifications + their specific role
                noti_filter = Q(target_role="ALL") | Q(target_role=user_role)
            else:
                # Default fallback
                noti_filter = Q(target_role="ALL") | Q(target_role=user_role)

            all_recent = RestaurantNotification.objects.filter(
                Q(business=business),
                noti_filter
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