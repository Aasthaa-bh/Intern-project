import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from core.models import Business, BusinessType
from accounts.models import User
from clothing.models import Notification

# 1. Create Business Type for Clothing
bt, _ = BusinessType.objects.get_or_create(
    name='Clothing Store',
    code='CLOTH',
    defaults={'description': 'Clothing and apparel business'}
)

# 2. Create the main Clothing Business
bus1, _ = Business.objects.get_or_create(
    business_code='BUS001',
    defaults={
        'business_name': 'SassyLassy Clothing',
        'business_type': bt,
        'address': 'Kathmandu',
        'status': 'ACTIVE'
    }
)

# 3. Create a second Clothing Business to test broadcast
bus2, _ = Business.objects.get_or_create(
    business_code='BUS002',
    defaults={
        'business_name': 'Urban Wear',
        'business_type': bt,
        'address': 'Lalitpur',
        'status': 'ACTIVE'
    }
)

# 4. Create User for main business
user, created = User.objects.get_or_create(
    username='pramisha',
    defaults={
        'business': bus1,
        'role': 'OWNER',
        'full_name': 'Pramisha',
        'email': 'pramisha@test.com',
        'is_first_login': False
    }
)
user.set_password('pramisha')
user.save()

print("✓ Setup complete!")
print("Business 1: SassyLassy (BUS001)")
print("Business 2: Urban Wear (BUS002)")
print("User: pramisha / pramisha")
