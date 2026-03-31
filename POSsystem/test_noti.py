import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from restaurant.models import RestaurantNotification
from core.models import Business

# We will look for business with name 'HAMRO PASAL'
business = Business.objects.filter(business_name__icontains="hamro").first()

if business:
    # 1. Simulate a payment success
    RestaurantNotification.objects.create(
        business=business,
        message="TEST: New order received for Hamro Pasal (Takeaway)"
    )
    
    # 2. Simulate a kitchen order ready
    RestaurantNotification.objects.create(
        business=business, 
        message="TEST: Rs. 500 Payment Successful via eSewa"
    )
    
    print(f"✅ Successfully created 2 test notifications for: {business.business_name}!")
else:
    print("❌ Error: Business 'HAMRO PASAL' not found.")
