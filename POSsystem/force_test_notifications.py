#!/usr/bin/env python
"""
Force test to see if notifications work when directly accessing the view
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

print("\n" + "="*70)
print("FORCING NOTIFICATION TEST")
print("="*70)

# Import after django.setup()
from django.test import Client
from accounts.models import User

# Create a test client
client = Client(SERVER_NAME='127.0.0.1:8000')

# Login as puzan
user = User.objects.get(username='puzan')
client.force_login(user)

# Make a request to the dashboard
print("\nMaking request to dashboard...")
response = client.get('/owner/dashboard/clothing/', HTTP_HOST='127.0.0.1:8000')

print(f"\nResponse status: {response.status_code}")
print(f"Context keys: {list(response.context.keys()) if hasattr(response, 'context') and response.context else 'No context'}")

if hasattr(response, 'context') and response.context:
    print(f"\nNotification context variables:")
    print(f"  recent_notifications: {len(response.context.get('recent_notifications', []))}")
    print(f"  unread_notifications_count: {response.context.get('unread_notifications_count', 'NOT FOUND')}")
    print(f"  current_business: {response.context.get('current_business', 'NOT FOUND')}")
    print(f"  current_business_type: {response.context.get('current_business_type', 'NOT FOUND')}")
    
    if response.context.get('recent_notifications'):
        print(f"\n  Notifications:")
        for notif in response.context['recent_notifications']:
            print(f"    - {notif.title}")
    else:
        print(f"\n  ❌ No notifications in context!")
else:
    print("\n❌ No context available in response!")

print("\n" + "="*70)
