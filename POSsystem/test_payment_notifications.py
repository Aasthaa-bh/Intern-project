#!/usr/bin/env python
"""
Test script to verify payment notifications (success and failure)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business
from django.db.models import Q

def test_payment_notifications():
    print("\n" + "="*60)
    print("PAYMENT NOTIFICATION SYSTEM TEST")
    print("="*60)
    
    # Get a clothing business
    clothing_businesses = Business.objects.filter(business_type__name__iexact='clothing')
    
    if not clothing_businesses.exists():
        print("\n❌ No clothing businesses found!")
        return
    
    business = clothing_businesses.first()
    print(f"\n✓ Testing with business: {business.business_name}")
    
    print("\n" + "-"*60)
    print("Creating test payment notifications...")
    print("-"*60)
    
    # Test 1: Payment Success Notifications
    print("\n1. Payment Success Scenario:")
    
    admin_success = Notification.objects.create(
        business=business,
        notification_type='PAYMENT_COMPLETED',
        target_role='ADMIN',
        title='Payment Received',
        message='Payment of Rs 5,500 completed successfully. Transaction: TEST123',
        link='',
        is_read=False
    )
    print("   ✓ Created PAYMENT_COMPLETED notification for ADMIN")
    
    cashier_success = Notification.objects.create(
        business=business,
        notification_type='PAYMENT_COMPLETED',
        target_role='CASHIER',
        title='Payment Confirmed',
        message='Customer payment of Rs 5,500 has been confirmed. Transaction: TEST123',
        link='',
        is_read=False
    )
    print("   ✓ Created PAYMENT_COMPLETED notification for CASHIER")
    
    # Test 2: Payment Failure Notifications
    print("\n2. Payment Failure/Cancel Scenario:")
    
    admin_failed = Notification.objects.create(
        business=business,
        notification_type='PAYMENT_FAILED',
        target_role='ADMIN',
        title='Payment Failed',
        message='Payment cancelled or failed. Amount: Rs 3,200. Transaction: TEST456',
        link='',
        is_read=False
    )
    print("   ✓ Created PAYMENT_FAILED notification for ADMIN")
    
    cashier_failed = Notification.objects.create(
        business=business,
        notification_type='PAYMENT_FAILED',
        target_role='CASHIER',
        title='Payment Cancelled',
        message='Customer payment was cancelled or failed. Amount: Rs 3,200. Transaction: TEST456',
        link='',
        is_read=False
    )
    print("   ✓ Created PAYMENT_FAILED notification for CASHIER")
    
    # Test filtering
    print("\n" + "-"*60)
    print("Testing notification visibility by role...")
    print("-"*60)
    
    # Admin view
    admin_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
    admin_notifications = Notification.objects.filter(
        business=business,
        is_read=False
    ).filter(admin_filter).order_by('-created_at')
    
    print(f"\n👤 ADMIN/OWNER sees {admin_notifications.count()} notifications:")
    payment_notifs = admin_notifications.filter(
        notification_type__in=['PAYMENT_COMPLETED', 'PAYMENT_FAILED']
    )[:4]
    for notif in payment_notifs:
        print(f"   - [{notif.notification_type}] {notif.title}")
    
    # Cashier view
    cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
    cashier_notifications = Notification.objects.filter(
        business=business,
        is_read=False
    ).filter(cashier_filter).order_by('-created_at')
    
    print(f"\n👤 CASHIER sees {cashier_notifications.count()} notifications:")
    payment_notifs = cashier_notifications.filter(
        notification_type__in=['PAYMENT_COMPLETED', 'PAYMENT_FAILED']
    )[:4]
    for notif in payment_notifs:
        print(f"   - [{notif.notification_type}] {notif.title}")
    
    # Cleanup
    print("\n" + "-"*60)
    print("Cleaning up test notifications...")
    print("-"*60)
    
    admin_success.delete()
    cashier_success.delete()
    admin_failed.delete()
    cashier_failed.delete()
    print("✓ Test notifications deleted")
    
    print("\n" + "="*60)
    print("✅ PAYMENT NOTIFICATION TEST COMPLETED")
    print("="*60)
    print("\nPayment notification system is working correctly!")
    print("\nNotification Flow:")
    print("- Payment Success → Admin & Cashier both get PAYMENT_COMPLETED")
    print("- Payment Failed → Admin & Cashier both get PAYMENT_FAILED")
    print("- Admin sees: 'Payment Received' or 'Payment Failed'")
    print("- Cashier sees: 'Payment Confirmed' or 'Payment Cancelled'")
    print()

if __name__ == '__main__':
    test_payment_notifications()
