import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from accounts.models import User
from core.models import Business, BusinessType

# Get or create CLOTHING business type
bt = BusinessType.objects.filter(code='CLOTHING').first()
if not bt:
    bt = BusinessType.objects.create(
        name='Clothing Store',
        code='CLOTHING',
        description='Clothing and apparel business'
    )
    print(f"✓ Business type created: {bt.name}")

# Update business
b = Business.objects.first()
b.business_type = bt
b.business_code = 'BUS005'
b.save()
print(f"✓ Business updated: {b.business_name} (code: {b.business_code}, type: {bt.code})")

# Create or update ishika user
user, created = User.objects.update_or_create(
    username='ishika',
    defaults={
        'business': b,
        'role': 'OWNER',
        'full_name': 'Ishika',
        'email': 'ishika@test.com',
        'is_first_login': False
    }
)

user.set_password('ishika')
user.save()

print(f"✓ User {'created' if created else 'updated'}: {user.username}")
print("\n=== Login Credentials ===")
print("Business Code: BUS005")
print("Username: ishika")
print("Password: ishika")
print("Role: OWNER")
