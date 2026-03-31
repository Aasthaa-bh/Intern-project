import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business

sassy = Business.objects.get(business_name='SassyLassy')

# Cashier notification
Notification.objects.create(
    business=sassy,
    notification_type='GENERAL',
    target_role='CASHIER',
    title='New Product Available',
    message='New product "Denim Jacket" is now available for sale.',
    link='',
    is_read=False
)

# Admin notification
Notification.objects.create(
    business=sassy,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='New Product Added',
    message='Product "Denim Jacket" has been added to inventory.',
    link='',
    is_read=False
)

print("✅ Created 2 product notifications for SassyLassy (Saurav will see 1)")
