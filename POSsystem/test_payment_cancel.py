import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification, ClothingEsewaPayment
from core.models import Business
from accounts.models import User
from django.utils import timezone
import uuid

print("=" * 80)
print("TESTING PAYMENT CANCELLATION NOTIFICATIONS")
print("=" * 80)

# Get Seed business and sauri user
seed_business = Business.objects.filter(business_name='Seed').first()
sauri_user = User.objects.filter(username='sauri').first()

if not seed_business:
    print("ERROR: Seed business not found!")
    exit(1)

if not sauri_user:
    print("ERROR: sauri user not found!")
    exit(1)

print(f"\n1. Business: {seed_business.business_name} (ID: {seed_business.id})")
print(f"2. User: {sauri_user.username} (Role: {sauri_user.role})")

# Count notifications before
before_count = Notification.objects.filter(business=seed_business).count()
print(f"\n3. Notifications before: {before_count}")

# Create a test payment failure notification (simulating what esewa.py should do)
txn_uuid = str(uuid.uuid4())
print(f"\n4. Creating test payment failure notifications for transaction: {txn_uuid}")

# Admin notification
admin_notif = Notification.objects.create(
    business=seed_business,
    notification_type='PAYMENT_FAILED',
    target_role='ADMIN',
    title='Payment Failed - TEST',
    message=f'TEST: Payment cancelled. Transaction: {txn_uuid}',
    link='',
    is_read=False
)
print(f"   - Created ADMIN notification (ID: {admin_notif.id})")

# Cashier notification
cashier_notif = Notification.objects.create(
    business=seed_business,
    notification_type='PAYMENT_FAILED',
    target_role='CASHIER',
    title='Payment Cancelled - TEST',
    message=f'TEST: Customer payment was cancelled. Transaction: {txn_uuid}',
    link='',
    is_read=False
)
print(f"   - Created CASHIER notification (ID: {cashier_notif.id})")

# Count notifications after
after_count = Notification.objects.filter(business=seed_business).count()
print(f"\n5. Notifications after: {after_count}")
print(f"   - Difference: +{after_count - before_count}")

# Test the context processor query
from django.db.models import Q
from datetime import timedelta

thirty_days_ago = timezone.now() - timedelta(days=30)

# For OWNER (puzan)
owner_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
owner_notifs = Notification.objects.filter(
    business=seed_business,
    created_at__gte=thirty_days_ago
).filter(owner_filter).order_by('-created_at')

print(f"\n6. OWNER (puzan) should see: {owner_notifs.count()} notifications")
print("   Recent notifications:")
for n in owner_notifs[:5]:
    print(f"      - [{n.target_role}] {n.title}")

# For CASHIER (sauri)
cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
cashier_notifs = Notification.objects.filter(
    business=seed_business,
    created_at__gte=thirty_days_ago
).filter(cashier_filter).order_by('-created_at')

print(f"\n7. CASHIER (sauri) should see: {cashier_notifs.count()} notifications")
print("   Recent notifications:")
for n in cashier_notifs[:5]:
    print(f"      - [{n.target_role}] {n.title}")

print("\n" + "=" * 80)
print("TEST COMPLETE - Notifications created successfully!")
print("Now refresh the browser to see them in the UI")
print("=" * 80)
