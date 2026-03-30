import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from core.models import Business
from clothing.models import Offer, Notification
from accounts.models import User
from decimal import Decimal
import datetime

# Get businesses
businesses = Business.objects.all()
print(f"Total businesses: {businesses.count()}")

# Create a dummy offer to trigger notification
bus1 = businesses.first()
user = User.objects.first()

if bus1 and user:
    offer = Offer.objects.create(
        business=bus1,
        offer_name="Global Clothing Sale",
        offer_type='PERCENTAGE',
        discount_value=Decimal('20.00'),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=7),
        created_by=user,
        status='ACTIVE'
    )
    print(f"Created offer: {offer.offer_name} for {bus1.business_name}")

    # The view_offer.py logic is what creates the notification, but since I am running a script,
    # I should simulate what happens in the view or just check if the VIEW logic was correct.
    # Actually, the broadcast logic is inside the `offer_create` view in `views_offer.py`.
    # Let's check how many notifications exist now.
    
    # Wait, the logic I added is inside the view, so running this script won't trigger the broadcast
    # unless I call the view or manually run the broadcast logic here.
    # To TRULY test, I should use the browser tool to create an offer via the UI.
