import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from accounts.models import User

print("=" * 70)
print("NOTIFICATION SYSTEM TEST")
print("=" * 70)

# Get ishika user
try:
    user = User.objects.get(username='ishika')
    business = user.business
    
    print(f"\nUser: {user.username}")
    print(f"Business: {business.business_name}")
    print(f"Business Type: {business.business_type.name}")
    
    # Get all notifications for this business
    all_notifications = Notification.objects.filter(business=business).order_by('-created_at')
    unread_notifications = all_notifications.filter(is_read=False)
    
    print(f"\n{'='*70}")
    print(f"NOTIFICATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total Notifications: {all_notifications.count()}")
    print(f"Unread Notifications: {unread_notifications.count()}")
    print(f"Read Notifications: {all_notifications.filter(is_read=True).count()}")
    
    print(f"\n{'='*70}")
    print(f"ALL NOTIFICATIONS")
    print(f"{'='*70}")
    
    for notif in all_notifications:
        status = "✓ READ" if notif.is_read else "● UNREAD"
        print(f"\n[{status}] {notif.title}")
        print(f"  Type: {notif.get_notification_type_display()}")
        print(f"  Message: {notif.message}")
        print(f"  Link: {notif.link or 'No link'}")
        print(f"  Created: {notif.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if all_notifications.count() == 0:
        print("\n  No notifications found for this business.")
        print("\n  To create test notifications, run:")
        print("  python manage.py shell")
        print("  >>> from clothing.models import Notification")
        print("  >>> from core.models import Business")
        print("  >>> business = Business.objects.get(business_name='SassyLassy')")
        print("  >>> Notification.objects.create(")
        print("  ...     business=business,")
        print("  ...     notification_type='GENERAL',")
        print("  ...     title='Test Notification',")
        print("  ...     message='This is a test notification',")
        print("  ...     is_read=False")
        print("  ... )")
    
except User.DoesNotExist:
    print("\nError: User 'ishika' not found")
except Exception as e:
    print(f"\nError: {e}")

print("\n" + "=" * 70)
print("NOTIFICATION TYPES AVAILABLE")
print("=" * 70)
print("1. OFFER_CREATED - When a new offer is created")
print("2. OFFER_EXPIRING - When an offer is about to expire (3 days)")
print("3. OFFER_EXPIRED - When an offer has expired")
print("4. LOW_STOCK - When items are running low on stock")
print("5. PURCHASE_RECEIVED - When a purchase order is received")
print("6. GENERAL - General notifications")

print("\n" + "=" * 70)
print("MANAGEMENT COMMANDS")
print("=" * 70)
print("Run these commands to generate notifications:")
print("1. python manage.py check_low_stock")
print("2. python manage.py check_expiring_offers")
print("=" * 70)
