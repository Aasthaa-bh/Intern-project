import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from accounts.models import User
from core.models import Business

print("=" * 60)
print("NOTIFICATION DEBUG")
print("=" * 60)

# Check all notifications
all_notifs = Notification.objects.all()
print(f"\nTotal notifications in DB: {all_notifs.count()}")

for n in all_notifs:
    print(f"\n  ID: {n.id}")
    print(f"  Title: {n.title}")
    print(f"  Business: {n.business.business_name} (ID: {n.business.id})")
    print(f"  Type: {n.notification_type}")
    print(f"  Read: {n.is_read}")
    print(f"  Created: {n.created_at}")

# Check users and their businesses
print("\n" + "=" * 60)
print("USERS AND BUSINESSES")
print("=" * 60)

users = User.objects.filter(business__isnull=False)
for user in users:
    print(f"\n  User: {user.username}")
    print(f"  Business: {user.business.business_name}")
    print(f"  Business Type: {user.business.business_type.name if user.business.business_type else 'None'}")
    
    # Count notifications for this business
    notif_count = Notification.objects.filter(business=user.business).count()
    unread_count = Notification.objects.filter(business=user.business, is_read=False).count()
    print(f"  Total Notifications: {notif_count}")
    print(f"  Unread Notifications: {unread_count}")
