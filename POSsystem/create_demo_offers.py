#!/usr/bin/env python
"""Create demo offers for testing"""
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from core.models import Business
from clothing.models import Offer
from accounts.models import User

def create_demo_offers():
    business = Business.objects.first()
    if not business:
        print("No business found!")
        return
    
    user = User.objects.filter(business=business).first()
    if not user:
        print("No user found!")
        return
    
    print(f"Using business: {business}")
    print(f"Using user: {user.username}\n")
    
    # Delete existing offers
    Offer.objects.filter(business=business).delete()
    print("Cleared existing offers\n")
    
    # Demo offers
    today = datetime.now().date()
    offers_data = [
        {
            'offer_name': 'Dashain Sale',
            'offer_type': 'PERCENTAGE',
            'description': 'Special Dashain festival discount',
            'discount_value': 25,
            'start_date': today,
            'end_date': today + timedelta(days=15),
            'minimum_purchase': 2000,
            'status': 'ACTIVE',
        },
        {
            'offer_name': 'Tihar Offer',
            'offer_type': 'PERCENTAGE',
            'description': 'Celebrate Tihar with discounts',
            'discount_value': 20,
            'start_date': today + timedelta(days=20),
            'end_date': today + timedelta(days=30),
            'minimum_purchase': 1500,
            'status': 'ACTIVE',
        },
        {
            'offer_name': 'New Year Sale',
            'offer_type': 'FLAT',
            'description': 'Flat discount for New Year',
            'discount_value': 500,
            'start_date': today + timedelta(days=60),
            'end_date': today + timedelta(days=75),
            'minimum_purchase': 3000,
            'status': 'ACTIVE',
        },
        {
            'offer_name': 'Summer Sale',
            'offer_type': 'PERCENTAGE',
            'description': 'Summer discounts',
            'discount_value': 30,
            'start_date': today + timedelta(days=90),
            'end_date': today + timedelta(days=120),
            'minimum_purchase': 1000,
            'status': 'ACTIVE',
        },
        {
            'offer_name': 'Winter Clearance',
            'offer_type': 'PERCENTAGE',
            'description': 'Clear winter stock',
            'discount_value': 40,
            'start_date': today - timedelta(days=30),
            'end_date': today - timedelta(days=1),
            'minimum_purchase': 500,
            'status': 'EXPIRED',
        },
        {
            'offer_name': 'Flash Sale',
            'offer_type': 'FLAT',
            'description': 'Limited time flash sale',
            'discount_value': 300,
            'start_date': today,
            'end_date': today + timedelta(days=3),
            'minimum_purchase': 1500,
            'status': 'ACTIVE',
        },
        {
            'offer_name': 'Weekend Special',
            'offer_type': 'PERCENTAGE',
            'description': 'Weekend only discount',
            'discount_value': 15,
            'start_date': today,
            'end_date': today + timedelta(days=2),
            'minimum_purchase': 0,
            'status': 'INACTIVE',
        },
        {
            'offer_name': 'Buy 1 Get 1',
            'offer_type': 'PERCENTAGE',
            'description': 'Buy one get one free',
            'discount_value': 50,
            'start_date': today,
            'end_date': today + timedelta(days=10),
            'minimum_purchase': 2500,
            'status': 'ACTIVE',
        },
    ]
    
    created_count = 0
    for offer_data in offers_data:
        offer = Offer.objects.create(
            business=business,
            created_by=user,
            **offer_data
        )
        print(f"Created: {offer.offer_name} ({offer.get_offer_type_display()}) - {offer.status}")
        created_count += 1
    
    print(f"\n✅ Successfully created {created_count} demo offers!")
    print(f"\nStats:")
    print(f"  Active: {Offer.objects.filter(business=business, status='ACTIVE').count()}")
    print(f"  Inactive: {Offer.objects.filter(business=business, status='INACTIVE').count()}")
    print(f"  Expired: {Offer.objects.filter(business=business, status='EXPIRED').count()}")

if __name__ == '__main__':
    create_demo_offers()
