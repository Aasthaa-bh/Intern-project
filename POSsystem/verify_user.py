import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from accounts.models import User
from core.models import Business

u = User.objects.filter(username='ishika').first()

if u:
    print(f"✓ User found: {u.username}")
    print(f"  Full name: {u.full_name}")
    print(f"  Role: {u.role}")
    print(f"  Business: {u.business.business_name if u.business else 'None'}")
    print(f"  Business Code: {u.business.business_code if u.business else 'None'}")
    print(f"  Business Type: {u.business.business_type.name if u.business and u.business.business_type else 'None'}")
    print(f"  Password check (ishika): {u.check_password('ishika')}")
else:
    print("✗ User 'ishika' not found!")
    
print("\n=== All users ===")
for user in User.objects.all():
    print(f"- {user.username} (role: {user.role}, business: {user.business.business_code if user.business else 'None'})")
