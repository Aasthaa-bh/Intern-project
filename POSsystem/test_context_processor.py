import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from accounts.models import User
from django.test import RequestFactory
from core.context_processors import notifications

# Get ishika user
user = User.objects.get(username='ishika')
print(f"User: {user.username}")
print(f"Business: {user.business.business_name}")
print(f"Business Type: {user.business.business_type.name}")

# Create a mock request
factory = RequestFactory()
request = factory.get('/')
request.user = user

# Call the context processor
context = notifications(request)

print("\n" + "=" * 60)
print("CONTEXT PROCESSOR OUTPUT")
print("=" * 60)
print(f"recent_notifications: {context['recent_notifications']}")
print(f"unread_notifications_count: {context['unread_notifications_count']}")
print(f"current_business: {context['current_business']}")
print(f"current_business_type: {context['current_business_type']}")
