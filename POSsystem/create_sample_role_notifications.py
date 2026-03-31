#!/usr/bin/env python
"""
Sample script to create role-based notifications
Use this as a reference for creating notifications in your code
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business

def create_sample_notifications():
    """Create sample notifications for different roles"""
    
    # Get a clothing business
    business = Business.objects.filter(business_type__name__iexact='clothing').first()
    
    if not business:
        print("❌ No clothing business found!")
        return
    
    print(f"Creating sample notifications for: {business.business_name}\n")
    
    # 1. Low Stock Alert - Admin only
    Notification.objects.create(
        business=business,
        notification_type='LOW_STOCK',
        target_role='ADMIN',
        title='Low Stock Alert: 5 items',
        message='Items running low: T-Shirt (SKU-001), Jeans (SKU-002), Jacket (SKU-003) and 2 more',
        link='/clothing/low-stock/',
        is_read=False
    )
    print("✓ Created LOW_STOCK notification for ADMIN")
    
    # 2. Payment Completed - Admin
    Notification.objects.create(
        business=business,
        notification_type='PAYMENT_COMPLETED',
        target_role='ADMIN',
        title='Payment Received',
        message='Payment of Rs 5,500 completed successfully. Transaction: ABC123XYZ',
        link='',
        is_read=False
    )
    print("✓ Created PAYMENT_COMPLETED notification for ADMIN")
    
    # 3. Payment Completed - Cashier
    Notification.objects.create(
        business=business,
        notification_type='PAYMENT_COMPLETED',
        target_role='CASHIER',
        title='Payment Confirmed',
        message='Customer payment of Rs 5,500 has been confirmed. Transaction: ABC123XYZ',
        link='',
        is_read=False
    )
    print("✓ Created PAYMENT_COMPLETED notification for CASHIER")
    
    # 4. Offer Created - Admin
    Notification.objects.create(
        business=business,
        notification_type='OFFER_CREATED',
        target_role='ADMIN',
        title='New Offer Created: Summer Sale',
        message='Percentage Discount - 20% discount. Valid from 2026-04-01 to 2026-04-30.',
        link='/clothing/offers/1/',
        is_read=False
    )
    print("✓ Created OFFER_CREATED notification for ADMIN")
    
    # 5. Purchase Received - Admin
    Notification.objects.create(
        business=business,
        notification_type='PURCHASE_RECEIVED',
        target_role='ADMIN',
        title='Purchase Received: ABC Suppliers',
        message='Purchase order #123 has been fully received. Total: Rs. 50,000',
        link='/clothing/purchases/123/',
        is_read=False
    )
    print("✓ Created PURCHASE_RECEIVED notification for ADMIN")
    
    # 6. General Announcement - All Users
    Notification.objects.create(
        business=business,
        notification_type='GENERAL',
        target_role='ALL',
        title='System Maintenance Notice',
        message='System will be under maintenance on Sunday 2AM-4AM. Please complete all transactions before that.',
        link='',
        is_read=False
    )
    print("✓ Created GENERAL notification for ALL users")
    
    print("\n✅ Sample notifications created successfully!")
    print("\nNotification Summary:")
    print("- Admin will see: 5 notifications (Low Stock, Payment, Offer, Purchase, General)")
    print("- Cashier will see: 2 notifications (Payment, General)")
    print("\nLogin as different users to see role-based filtering in action!")

if __name__ == '__main__':
    create_sample_notifications()
