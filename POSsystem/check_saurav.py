import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from accounts.models import User
from core.models import Business
from clothing.models import Notification
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

print("=" * 80)
print("CHECKING SAURAV USER")
print("=" * 80)

# Find all Saurav users
saurav_users = User.objects.filter(username__icontains='saurav')

print(f"\n📋 FOUND {saurav_users.count()} SAURAV USERS:")
for user in saurav_users:
    print(f"\n👤 Username: {user.username}")
    print(f"   Role: {user.role}")
    print(f"   Business: {user.business.business_name if user.business else 'None'}")
    print(f"   Business ID: {user.business.id if user.business else 'None'}")
    
    if user.business:
        # Check notifications for this user's business
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        if user.role == 'CASHIER':
            cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
            notifs = Notification.objects.filter(
                business=user.business,
                created_at__gte=thirty_days_ago
            ).filter(cashier_filter).order_by('-created_at')
            
            print(f"\n   📢 NOTIFICATIONS FOR {user.username} (CASHIER): {notifs.count()}")
            for i, n in enumerate(notifs[:5], 1):
                read_status = "✓" if n.is_read else "✗"
                print(f"      {i}. [{read_status}] [{n.target_role}] {n.title}")
        
        elif user.role in ['OWNER', 'SUPERADMIN']:
            admin_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
            notifs = Notification.objects.filter(
                business=user.business,
                created_at__gte=thirty_days_ago
            ).filter(admin_filter).order_by('-created_at')
            
            print(f"\n   📢 NOTIFICATIONS FOR {user.username} (ADMIN): {notifs.count()}")
            for i, n in enumerate(notifs[:5], 1):
                read_status = "✓" if n.is_read else "✗"
                print(f"      {i}. [{read_status}] [{n.target_role}] {n.title}")

print("\n" + "=" * 80)
