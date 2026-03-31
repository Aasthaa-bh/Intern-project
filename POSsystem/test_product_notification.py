import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business
from accounts.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

print("=" * 80)
print("TESTING PRODUCT ADD NOTIFICATIONS")
print("=" * 80)

# Get Seed business
seed_business = Business.objects.filter(business_name='Seed').first()

if not seed_business:
    print("ERROR: Seed business not found!")
    exit(1)

print(f"\n1. Business: {seed_business.business_name} (ID: {seed_business.id})")

# Count before
before = Notification.objects.filter(business=seed_business).count()
print(f"\n2. Notifications before: {before}")

# Create test product notifications
print(f"\n3. Creating test product notifications...")

# Admin notification
admin_notif = Notification.objects.create(
    business=seed_business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='New Product Added',
    message='Product "Test T-Shirt" has been added to inventory.',
    link='/clothing/products/1/',
    is_read=False
)
print(f"   ✓ Created ADMIN notification: {admin_notif.title}")

# Cashier notification
cashier_notif = Notification.objects.create(
    business=seed_business,
    notification_type='GENERAL',
    target_role='CASHIER',
    title='New Product Available',
    message='New product "Test T-Shirt" is now available for sale.',
    link='',
    is_read=False
)
print(f"   ✓ Created CASHIER notification: {cashier_notif.title}")

# Count after
after = Notification.objects.filter(business=seed_business).count()
print(f"\n4. Notifications after: {after}")
print(f"   Difference: +{after - before}")

# Check what each user sees
thirty_days_ago = timezone.now() - timedelta(days=30)

# Admin (puzan)
admin_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
admin_notifs = Notification.objects.filter(
    business=seed_business,
    created_at__gte=thirty_days_ago
).filter(admin_filter).order_by('-created_at')

print(f"\n5. ADMIN (puzan) should see: {admin_notifs.count()} notifications")
print("   Recent 5:")
for i, n in enumerate(admin_notifs[:5], 1):
    read_status = "✓" if n.is_read else "✗"
    print(f"   {i}. [{read_status}] [{n.target_role}] {n.title}")

# Cashier (sauri)
cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
cashier_notifs = Notification.objects.filter(
    business=seed_business,
    created_at__gte=thirty_days_ago
).filter(cashier_filter).order_by('-created_at')

print(f"\n6. CASHIER (sauri) should see: {cashier_notifs.count()} notifications")
print("   All notifications:")
for i, n in enumerate(cashier_notifs, 1):
    read_status = "✓" if n.is_read else "✗"
    print(f"   {i}. [{read_status}] [{n.target_role}] {n.title}")

print("\n" + "=" * 80)
print("✅ PRODUCT NOTIFICATIONS CREATED!")
print("Now:")
print("  - Puzan (Admin) should see 'New Product Added' notification")
print("  - Sauri (Cashier) should see 'New Product Available' notification")
print("=" * 80)
