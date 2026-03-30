import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business

# Get first business
business = Business.objects.first()

if business:
    # Create test notifications
    Notification.objects.create(
        business=business,
        notification_type='OFFER_CREATED',
        title='New Offer Created',
        message='Summer Sale offer has been created successfully',
        link='/clothing/offers/',
        is_read=False
    )
    
    Notification.objects.create(
        business=business,
        notification_type='LOW_STOCK',
        title='Low Stock Alert',
        message='5 products are running low on stock',
        link='/clothing/low-stock/',
        is_read=False
    )
    
    Notification.objects.create(
        business=business,
        notification_type='OFFER_EXPIRING',
        title='Offer Expiring Soon',
        message='Dashain Sale will expire in 2 days',
        link='/clothing/offers/',
        is_read=False
    )
    
    print(f"✓ Created 3 test notifications for {business.business_name}")
else:
    print("✗ No business found")
