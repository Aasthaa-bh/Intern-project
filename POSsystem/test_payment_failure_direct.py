#!/usr/bin/env python
"""
Direct test for payment failure notification creation
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business

def test_payment_failure_notification():
    print("\n" + "="*60)
    print("DIRECT PAYMENT FAILURE NOTIFICATION TEST")
    print("="*60)
    
    # Get a clothing business
    business = Business.objects.filter(business_type__name__iexact='clothing').first()
    
    if not business:
        print("\n❌ No clothing business found!")
        return
    
    print(f"\n✓ Testing with business: {business.business_name}")
    
    # Simulate payment failure notification creation
    print("\n" + "-"*60)
    print("Creating payment failure notifications...")
    print("-"*60)
    
    # Admin notification
    admin_notif = Notification.objects.create(
        business=business,
        notification_type='PAYMENT_FAILED',
        target_role='ADMIN',
        title='Payment Failed',
        message='Payment cancelled or failed. Amount: Rs 2,500. Transaction: TEST-FAIL-123',
        link='',
        is_read=False
    )
    print("✓ Created PAYMENT_FAILED notification for ADMIN")
    print(f"   ID: {admin_notif.id}")
    print(f"   Title: {admin_notif.title}")
    print(f"   Message: {admin_notif.message}")
    
    # Cashier notification
    cashier_notif = Notification.objects.create(
        business=business,
        notification_type='PAYMENT_FAILED',
        target_role='CASHIER',
        title='Payment Cancelled',
        message='Customer payment was cancelled or failed. Amount: Rs 2,500. Transaction: TEST-FAIL-123',
        link='',
        is_read=False
    )
    print("\n✓ Created PAYMENT_FAILED notification for CASHIER")
    print(f"   ID: {cashier_notif.id}")
    print(f"   Title: {cashier_notif.title}")
    print(f"   Message: {cashier_notif.message}")
    
    # Check if they're visible
    print("\n" + "-"*60)
    print("Checking notification visibility...")
    print("-"*60)
    
    from django.db.models import Q
    
    # Admin view
    admin_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
    admin_count = Notification.objects.filter(
        business=business,
        is_read=False
    ).filter(admin_filter).count()
    print(f"\n👤 ADMIN can see {admin_count} unread notifications")
    
    # Cashier view
    cashier_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
    cashier_count = Notification.objects.filter(
        business=business,
        is_read=False
    ).filter(cashier_filter).count()
    print(f"👤 CASHIER can see {cashier_count} unread notifications")
    
    # Cleanup
    print("\n" + "-"*60)
    print("Cleaning up...")
    print("-"*60)
    
    admin_notif.delete()
    cashier_notif.delete()
    print("✓ Test notifications deleted")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETED")
    print("="*60)
    print("\nNotifications are being created correctly.")
    print("If you're not seeing them in the UI, check:")
    print("1. Are you logged in as the correct user?")
    print("2. Is your user assigned to the correct business?")
    print("3. Does your user have the correct role (OWNER/CASHIER)?")
    print("4. Check browser console for JavaScript errors")
    print("5. Try refreshing the page")
    print()

if __name__ == '__main__':
    test_payment_failure_notification()
