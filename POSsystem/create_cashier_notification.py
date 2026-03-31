#!/usr/bin/env python
"""
Create a test notification for CASHIER role
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business

# Get Seed business
business = Business.objects.filter(business_name='Seed').first()

if business:
    # Create a notification for CASHIER
    Notification.objects.create(
        business=business,
        notification_type='GENERAL',
        target_role='CASHIER',
        title='Welcome Cashier!',
        message='This is a test notification for cashier users. You can now see notifications!',
        link='',
        is_read=False
    )
    print(f"✅ Created CASHIER notification for {business.business_name}")
    
    # Also create one for ADMIN
    Notification.objects.create(
        business=business,
        notification_type='GENERAL',
        target_role='ADMIN',
        title='Welcome Admin!',
        message='This is a test notification for admin users. The notification system is working!',
        link='',
        is_read=False
    )
    print(f"✅ Created ADMIN notification for {business.business_name}")
else:
    print("❌ Business not found!")
