import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification, ClothingEsewaPayment
from core.models import Business
from accounts.models import User
from django.utils import timezone
from datetime import timedelta

print("=" * 80)
print("PAYMENT NOTIFICATION DIAGNOSTIC")
print("=" * 80)

# Check businesses
businesses = Business.objects.all()
print(f"\n1. BUSINESSES ({businesses.count()}):")
for b in businesses:
    print(f"   - ID: {b.id}, Name: {b.business_name}, Type: {b.business_type.name if b.business_type else 'None'}")

# Check users
users = User.objects.all()
print(f"\n2. USERS ({users.count()}):")
for u in users:
    print(f"   - Username: {u.username}, Role: {u.role}, Business: {u.business.business_name if u.business else 'None'}")

# Check eSewa payments
payments = ClothingEsewaPayment.objects.all().order_by('-created_at')[:10]
print(f"\n3. RECENT ESEWA PAYMENTS ({payments.count()}):")
for p in payments:
    print(f"   - ID: {p.id}, Status: {p.status}, Amount: {p.amount}, Created: {p.created_at}")
    print(f"     Business: {p.business.business_name if p.business else 'None'}")
    print(f"     Transaction UUID: {p.transaction_uuid}")

# Check all notifications
all_notifs = Notification.objects.all().order_by('-created_at')
print(f"\n4. ALL NOTIFICATIONS ({all_notifs.count()}):")
for n in all_notifs:
    print(f"   - ID: {n.id}, Type: {n.notification_type}, Target: {n.target_role}")
    print(f"     Title: {n.title}")
    print(f"     Business: {n.business.business_name if n.business else 'None'}")
    print(f"     Created: {n.created_at}, Read: {n.is_read}")

# Check notifications from last hour
one_hour_ago = timezone.now() - timedelta(hours=1)
recent_notifs = Notification.objects.filter(created_at__gte=one_hour_ago).order_by('-created_at')
print(f"\n5. NOTIFICATIONS FROM LAST HOUR ({recent_notifs.count()}):")
for n in recent_notifs:
    print(f"   - ID: {n.id}, Type: {n.notification_type}, Target: {n.target_role}")
    print(f"     Title: {n.title}")
    print(f"     Message: {n.message}")
    print(f"     Business: {n.business.business_name if n.business else 'None'}")

# Test the context processor query
print("\n6. TESTING CONTEXT PROCESSOR QUERY:")
seed_business = Business.objects.filter(business_name='Seed').first()
if seed_business:
    print(f"   Seed Business ID: {seed_business.id}")
    
    # Test for OWNER role
    from django.db.models import Q
    thirty_days_ago = timezone.now() - timedelta(days=30)
    role_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
    
    owner_notifs = Notification.objects.filter(
        business=seed_business,
        created_at__gte=thirty_days_ago
    ).filter(role_filter).order_by('-created_at')
    
    print(f"   OWNER notifications (ADMIN + ALL): {owner_notifs.count()}")
    for n in owner_notifs[:5]:
        print(f"      - {n.title} ({n.target_role})")
    
    # Test for CASHIER role
    role_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
    cashier_notifs = Notification.objects.filter(
        business=seed_business,
        created_at__gte=thirty_days_ago
    ).filter(role_filter).order_by('-created_at')
    
    print(f"   CASHIER notifications (CASHIER + ALL): {cashier_notifs.count()}")
    for n in cashier_notifs[:5]:
        print(f"      - {n.title} ({n.target_role})")
else:
    print("   Seed business not found!")

print("\n" + "=" * 80)
