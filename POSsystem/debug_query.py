#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

business = Business.objects.filter(business_name='Seed').first()
print(f"Business: {business.business_name} (ID: {business.id})")

# Check all notifications
all_notifs = Notification.objects.filter(business=business)
print(f"\nTotal notifications in DB: {all_notifs.count()}")

# Check with date filter
thirty_days_ago = timezone.now() - timedelta(days=30)
print(f"\n30 days ago: {thirty_days_ago}")
print(f"Current time: {timezone.now()}")

recent = Notification.objects.filter(
    business=business,
    created_at__gte=thirty_days_ago
)
print(f"\nNotifications from last 30 days: {recent.count()}")

# Check with role filter
role_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
with_role = recent.filter(role_filter)
print(f"With ADMIN role filter: {with_role.count()}")

# Show notification dates
print(f"\nNotification created_at dates:")
for n in all_notifs[:5]:
    print(f"  - {n.title}: {n.created_at} (target_role={n.target_role})")
