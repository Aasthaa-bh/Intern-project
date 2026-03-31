import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business
from accounts.models import User
from django.utils import timezone
from datetime import timedelta

print("=" * 80)
print("TESTING SUPPLIER NOTIFICATIONS")
print("=" * 80)

# Get Seed business
seed_business = Business.objects.filter(business_name='Seed').first()
puzan_user = User.objects.filter(username='puzan').first()

if not seed_business:
    print("ERROR: Seed business not found!")
    exit(1)

if not puzan_user:
    print("ERROR: puzan user not found!")
    exit(1)

print(f"\n1. Business: {seed_business.business_name} (ID: {seed_business.id})")
print(f"2. User: {puzan_user.username} (Role: {puzan_user.role})")

# Count notifications before
before_count = Notification.objects.filter(business=seed_business).count()
print(f"\n3. Notifications before: {before_count}")

# Create a test supplier notification
print(f"\n4. Creating test supplier notification")

supplier_notif = Notification.objects.create(
    business=seed_business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='New Supplier Added - TEST',
    message='TEST: Supplier "Test Supplier Co." has been added to the system.',
    link='/clothing/suppliers/',
    is_read=False
)
print(f"   - Created ADMIN notification (ID: {supplier_notif.id})")

# Count notifications after
after_count = Notification.objects.filter(business=seed_business).count()
print(f"\n5. Notifications after: {after_count}")
print(f"   - Difference: +{after_count - before_count}")

# Test the context processor query for OWNER
from django.db.models import Q

thirty_days_ago = timezone.now() - timedelta(days=30)
owner_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
owner_notifs = Notification.objects.filter(
    business=seed_business,
    created_at__gte=thirty_days_ago
).filter(owner_filter).order_by('-created_at')

print(f"\n6. OWNER (puzan) should see: {owner_notifs.count()} notifications")
print("   Recent notifications:")
for n in owner_notifs[:5]:
    print(f"      - [{n.target_role}] {n.title}")

print("\n" + "=" * 80)
print("TEST COMPLETE - Supplier notification created successfully!")
print("Now refresh puzan's dashboard to see it in the UI")
print("=" * 80)
