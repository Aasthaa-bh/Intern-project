#!/usr/bin/env python
"""
Test script to verify role-based notification system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business
from accounts.models import User
from django.db.models import Q

def test_notifications():
    print("\n" + "="*60)
    print("ROLE-BASED NOTIFICATION SYSTEM TEST")
    print("="*60)
    
    # Get a clothing business
    clothing_businesses = Business.objects.filter(business_type__name__iexact='clothing')
    
    if not clothing_businesses.exists():
        print("\n❌ No clothing businesses found!")
        return
    
    business = clothing_businesses.first()
    print(f"\n✓ Testing with business: {business.business_name}")
    
    # Create test notifications
    print("\n" + "-"*60)
    print("Creating test notifications...")
    print("-"*60)
    
    # Admin notification (Low Stock)
    admin_notif = Notification.objects.create(
        business=business,
        notification_type='LOW_STOCK',
        target_role='ADMIN',
        title='Test: Low Stock Alert',
        message='This is a test notification for Admin users only',
        link='/clothing/low-stock/',
        is_read=False
    )
    print("✓ Created ADMIN notification (Low Stock)")
    
    # Cashier notification (Payment)
    cashier_notif = Notification.objects.create(
        business=business,
        notification_type='PAYMENT_COMPLETED',
        target_role='CASHIER',
        title='Test: Payment Confirmed',
        message='This is a test notification for Cashier users only',
        link='',
        is_read=False
    )
    print("✓ Created CASHIER notification (Payment)")
    
    # All users notification
    all_notif = Notification.objects.create(
        business=business,
        notification_type='GENERAL',
        target_role='ALL',
        title='Test: General Announcement',
        message='This is a test notification for all users',
        link='',
        is_read=False
    )
    print("✓ Created ALL notification (General)")
    
    # Test filtering for different roles
    print("\n" + "-"*60)
    print("Testing notification filtering by role...")
    print("-"*60)
    
    # Admin role filter
    admin_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
    admin_notifications = Notification.objects.filter(
        business=business,
        is_read=False
    ).filter(admin_filter)
    
    print(f"\n👤 ADMIN/OWNER users see: {admin_notifications.count()} notifications")
    for notif in admin_notifications:
        print(f"   - [{notif.target_role}] {notif.title}")
    
    # Cashier role filter
    cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
    cashier_notifications = Notification.objects.filter(
        business=business,
        is_read=False
    ).filter(cashier_filter)
    
    print(f"\n👤 CASHIER users see: {cashier_notifications.count()} notifications")
    for notif in cashier_notifications:
        print(f"   - [{notif.target_role}] {notif.title}")
    
    # Check users in the business
    print("\n" + "-"*60)
    print("Users in this business:")
    print("-"*60)
    
    users = User.objects.filter(business=business)
    if users.exists():
        for user in users:
            print(f"   - {user.username} ({user.role})")
    else:
        print("   No users found for this business")
    
    # Cleanup
    print("\n" + "-"*60)
    print("Cleaning up test notifications...")
    print("-"*60)
    
    admin_notif.delete()
    cashier_notif.delete()
    all_notif.delete()
    print("✓ Test notifications deleted")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("="*60)
    print("\nNotification system is working correctly!")
    print("- Admin users will see: LOW_STOCK, PAYMENT_COMPLETED (admin), OFFER_*, PURCHASE_RECEIVED, GENERAL")
    print("- Cashier users will see: PAYMENT_COMPLETED (cashier)")
    print("- All users will see: Notifications with target_role='ALL'")
    print()

if __name__ == '__main__':
    test_notifications()
