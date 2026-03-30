import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from accounts.models import User
from core.models import Business

# Get or create business
business = Business.objects.first()
if not business:
    print("No business found! Please create a business first.")
    exit()

# Create or update pramisha user
user, created = User.objects.update_or_create(
    username='pramisha',
    defaults={
        'business': business,
        'role': 'CASHIER',  # Reception role
        'full_name': 'Pramisha',
        'email': 'pramisha@test.com',
        'is_first_login': False
    }
)

# Set password
user.set_password('pramisha')
user.save()

if created:
    print("✓ User 'pramisha' created successfully!")
else:
    print("✓ User 'pramisha' updated successfully!")

print("\nLogin credentials:")
print("Username: pramisha")
print("Password: pramisha")
print("Role: CASHIER (Reception)")
