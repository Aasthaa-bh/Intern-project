import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business
from accounts.models import User
import uuid

print("=" * 80)
print("CREATING NOTIFICATIONS FOR SAURAV (SassyLassy)")
print("=" * 80)

# Get SassyLassy business and Saurav user
sassy_business = Business.objects.filter(business_name='SassyLassy').first()
saurav = User.objects.filter(username='Saurav').first()

if not sassy_business:
    print("ERROR: SassyLassy business not found!")
    exit(1)

if not saurav:
    print("ERROR: Saurav user not found!")
    exit(1)

print(f"\n1. Business: {sassy_business.business_name} (ID: {sassy_business.id})")
print(f"2. User: {saurav.username} (Role: {saurav.role})")

# Count before
before = Notification.objects.filter(business=sassy_business).count()
print(f"\n3. Notifications before: {before}")

# Create test notifications
print(f"\n4. Creating test notifications...")

# Welcome notification for Cashier
notif1 = Notification.objects.create(
    business=sassy_business,
    notification_type='GENERAL',
    target_role='CASHIER',
    title='Welcome Cashier!',
    message='This is a test notification for cashier users. You can now see notifications!',
    link='',
    is_read=False
)
print(f"   ✓ Created: {notif1.title}")

# Payment cancelled notification
txn_uuid = str(uuid.uuid4())
notif2 = Notification.objects.create(
    business=sassy_business,
    notification_type='PAYMENT_FAILED',
    target_role='CASHIER',
    title='Payment Cancelled',
    message=f'Customer payment was cancelled. Transaction: {txn_uuid}',
    link='',
    is_read=False
)
print(f"   ✓ Created: {notif2.title}")

# Payment completed notification
notif3 = Notification.objects.create(
    business=sassy_business,
    notification_type='PAYMENT_COMPLETED',
    target_role='CASHIER',
    title='Payment Successful',
    message='Customer payment completed via eSewa. Amount: Rs 2500.00',
    link='',
    is_read=False
)
print(f"   ✓ Created: {notif3.title}")

# Admin notifications
notif4 = Notification.objects.create(
    business=sassy_business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='Welcome Admin!',
    message='This is a test notification for admin users.',
    link='',
    is_read=False
)
print(f"   ✓ Created: {notif4.title}")

notif5 = Notification.objects.create(
    business=sassy_business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='New Supplier Added',
    message='Supplier "Test Supplier" has been added to the system.',
    link='/clothing/suppliers/',
    is_read=False
)
print(f"   ✓ Created: {notif5.title}")

# Count after
after = Notification.objects.filter(business=sassy_business).count()
print(f"\n5. Notifications after: {after}")
print(f"   Difference: +{after - before}")

# Verify what Saurav can see
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

thirty_days_ago = timezone.now() - timedelta(days=30)
cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
saurav_notifs = Notification.objects.filter(
    business=sassy_business,
    created_at__gte=thirty_days_ago
).filter(cashier_filter).order_by('-created_at')

print(f"\n6. SAURAV (Cashier) should see: {saurav_notifs.count()} notifications")
for i, n in enumerate(saurav_notifs, 1):
    read_status = "✓" if n.is_read else "✗"
    print(f"   {i}. [{read_status}] {n.title}")

# Check admin notifications too
admin_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
admin_notifs = Notification.objects.filter(
    business=sassy_business,
    created_at__gte=thirty_days_ago
).filter(admin_filter).order_by('-created_at')

print(f"\n7. ADMIN (ishika) should see: {admin_notifs.count()} notifications")
for i, n in enumerate(admin_notifs[:5], 1):
    read_status = "✓" if n.is_read else "✗"
    print(f"   {i}. [{read_status}] {n.title}")

print("\n" + "=" * 80)
print("✅ NOTIFICATIONS CREATED FOR SAURAV!")
print("Now Saurav should login and check the bell icon")
print("=" * 80)
