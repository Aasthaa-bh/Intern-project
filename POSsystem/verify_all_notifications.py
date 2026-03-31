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
print("COMPLETE NOTIFICATION SYSTEM VERIFICATION")
print("=" * 80)

# Get Seed business and users
seed_business = Business.objects.filter(business_name='Seed').first()
puzan = User.objects.filter(username='puzan').first()
sauri = User.objects.filter(username='sauri').first()

if not seed_business or not puzan or not sauri:
    print("ERROR: Required data not found!")
    exit(1)

print(f"\n📊 BUSINESS: {seed_business.business_name} (ID: {seed_business.id})")
print(f"👤 ADMIN: {puzan.username} (Role: {puzan.role})")
print(f"👤 CASHIER: {sauri.username} (Role: {sauri.role})")

# Get all notifications
all_notifs = Notification.objects.filter(business=seed_business).order_by('-created_at')
print(f"\n📢 TOTAL NOTIFICATIONS: {all_notifs.count()}")

# Group by type
notif_types = {}
for n in all_notifs:
    notif_types[n.notification_type] = notif_types.get(n.notification_type, 0) + 1

print("\n📋 NOTIFICATIONS BY TYPE:")
for ntype, count in sorted(notif_types.items()):
    print(f"   - {ntype}: {count}")

# Group by target role
notif_roles = {}
for n in all_notifs:
    notif_roles[n.target_role] = notif_roles.get(n.target_role, 0) + 1

print("\n🎯 NOTIFICATIONS BY TARGET ROLE:")
for role, count in sorted(notif_roles.items()):
    print(f"   - {role}: {count}")

# Test context processor queries
thirty_days_ago = timezone.now() - timedelta(days=30)

# ADMIN notifications
admin_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
admin_notifs = Notification.objects.filter(
    business=seed_business,
    created_at__gte=thirty_days_ago
).filter(admin_filter).order_by('-created_at')

print(f"\n👨‍💼 ADMIN (puzan) SEES: {admin_notifs.count()} notifications")
print("   Recent 5:")
for i, n in enumerate(admin_notifs[:5], 1):
    read_status = "✓" if n.is_read else "✗"
    print(f"   {i}. [{read_status}] [{n.notification_type}] {n.title}")

# CASHIER notifications
cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
cashier_notifs = Notification.objects.filter(
    business=seed_business,
    created_at__gte=thirty_days_ago
).filter(cashier_filter).order_by('-created_at')

print(f"\n💰 CASHIER (sauri) SEES: {cashier_notifs.count()} notifications")
print("   Recent 5:")
for i, n in enumerate(cashier_notifs[:5], 1):
    read_status = "✓" if n.is_read else "✗"
    print(f"   {i}. [{read_status}] [{n.notification_type}] {n.title}")

# Check for specific notification types
print("\n🔍 CHECKING SPECIFIC NOTIFICATION TYPES:")

payment_completed = all_notifs.filter(notification_type='PAYMENT_COMPLETED').count()
payment_failed = all_notifs.filter(notification_type='PAYMENT_FAILED').count()
supplier_notifs = all_notifs.filter(notification_type='GENERAL', title__icontains='Supplier').count()
low_stock = all_notifs.filter(notification_type='LOW_STOCK').count()
offers = all_notifs.filter(notification_type__in=['OFFER_CREATED', 'OFFER_EXPIRING']).count()

print(f"   ✓ Payment Completed: {payment_completed}")
print(f"   ✓ Payment Failed/Cancelled: {payment_failed}")
print(f"   ✓ Supplier Notifications: {supplier_notifs}")
print(f"   ✓ Low Stock Alerts: {low_stock}")
print(f"   ✓ Offer Notifications: {offers}")

# Unread counts
admin_unread = admin_notifs.filter(is_read=False).count()
cashier_unread = cashier_notifs.filter(is_read=False).count()

print(f"\n📬 UNREAD NOTIFICATIONS:")
print(f"   - Admin: {admin_unread} unread")
print(f"   - Cashier: {cashier_unread} unread")

print("\n" + "=" * 80)
print("✅ VERIFICATION COMPLETE!")
print("=" * 80)
print("\n📝 NEXT STEPS:")
print("   1. Restart Django server: python manage.py runserver")
print("   2. Login as 'puzan' (Admin) - should see notifications in bell icon")
print("   3. Login as 'sauri' (Cashier) - should see notifications in bell icon")
print("   4. Test payment cancel - should create new notifications")
print("   5. Test supplier add - should create new notification")
print("=" * 80)
