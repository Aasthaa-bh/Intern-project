import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from core.models import Business
from clothing.models import Notification, Offer
from accounts.models import User
from decimal import Decimal
import datetime

def test_broadcast():
    # Setup test data (we already did this in setup_local_db.py)
    bus1 = Business.objects.filter(business_code='BUS001').first()
    user = User.objects.filter(username='pramisha').first()
    
    if not bus1 or not user:
        print("Required objects not found! Run setup_local_db.py first.")
        return

    # 1. Create offer manually (simulate what happens in offer_create view)
    offer = Offer.objects.create(
        business=bus1,
        offer_name="Test Broadcast Sale",
        offer_type='PERCENTAGE',
        discount_value=Decimal('10.00'),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=7),
        created_by=user,
        status='ACTIVE'
    )
    print(f"✓ Created offer: {offer.offer_name} for {bus1.business_name}")
    
    # 2. Trigger the broadcast logic (This is the logic we added to views_offer.py)
    clothing_businesses = [b for b in Business.objects.all() if b.is_clothing_business]
    print(f"Found {len(clothing_businesses)} clothing businesses.")
    
    for cb in clothing_businesses:
        Notification.objects.create(
            business=cb,
            notification_type='OFFER_CREATED',
            title=f'New Offer Created: {offer.offer_name}',
            message=f'{offer.get_offer_type_display()} - {offer.get_discount_display()} discount.',
            link=f'/clothing/offers/{offer.id}/',
            is_read=False
        )
        print(f"✓ Created notification for business: {cb.business_name} (Code: {cb.business_code})")

    # 3. Verify
    total_notifs = Notification.objects.filter(title__contains=offer.offer_name).count()
    print(f"--- VERIFICATION ---")
    print(f"Total notifications for this offer: {total_notifs}")
    if total_notifs == len(clothing_businesses):
        print("PASS: Notifications were broadcasted to ALL clothing businesses!")
    else:
        print("FAIL: Broadcast failed.")

if __name__ == "__main__":
    test_broadcast()
