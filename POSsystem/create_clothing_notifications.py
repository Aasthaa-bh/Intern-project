import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business

# Get the business
business = Business.objects.first()

if not business:
    print("No business found!")
    exit()

# Clear existing notifications
Notification.objects.filter(business=business).delete()

# Create sample notifications
notifications = [
    {
        'notification_type': 'OFFER_CREATED',
        'title': 'New Offer Created',
        'message': 'Summer Sale offer has been created with 20% discount on all items.',
        'link': '/owner/dashboard/clothing/offers/',
    },
    {
        'notification_type': 'OFFER_EXPIRING',
        'title': 'Offer Expiring Soon',
        'message': 'Winter Clearance offer will expire in 2 days. Take action now!',
        'link': '/owner/dashboard/clothing/offers/',
    },
    {
        'notification_type': 'LOW_STOCK',
        'title': 'Low Stock Alert',
        'message': 'T-Shirt (Blue, Size M) stock is running low. Only 5 units remaining.',
        'link': '/owner/dashboard/clothing/products/',
    },
    {
        'notification_type': 'PURCHASE_RECEIVED',
        'title': 'Purchase Order Received',
        'message': 'Purchase order #PO-001 has been received successfully.',
        'link': '/owner/dashboard/clothing/purchases/',
    },
    {
        'notification_type': 'GENERAL',
        'title': 'Welcome to FlexiPOS',
        'message': 'Your clothing store dashboard is ready. Start managing your inventory and offers.',
        'link': '/owner/dashboard/clothing/',
    },
]

for notif_data in notifications:
    Notification.objects.create(
        business=business,
        **notif_data
    )

print(f"✓ Created {len(notifications)} notifications for {business.business_name}")
print("\nNotifications:")
for n in Notification.objects.filter(business=business):
    print(f"  - {n.title} ({n.notification_type})")