import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import User

# Test authentication
username = 'ishika'
password = 'ishika'

print(f"Testing authentication for: {username}")

user = authenticate(username=username, password=password)

if user:
    print(f"✓ Authentication successful!")
    print(f"  Username: {user.username}")
    print(f"  Role: {user.role}")
    print(f"  Business: {user.business.business_name if user.business else 'None'}")
    print(f"  Business Code: {user.business.business_code if user.business else 'None'}")
else:
    print("✗ Authentication failed!")
    
    # Check if user exists
    u = User.objects.filter(username=username).first()
    if u:
        print(f"  User exists in database: {u.username}")
        print(f"  Password check: {u.check_password(password)}")
        print(f"  Is active: {u.is_active}")
    else:
        print(f"  User '{username}' does not exist in database")
