#!/usr/bin/env python
"""
Check recent notifications in the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from clothing.models import Notification
from core.models import Business
from django.utils import timezone
from datetime import timedelta

def check_recent_notifications():
    print("\n" + "="*60)
    print("RECENT NOTIFICATIONS CHECK")
    print("="*60)
    
    # Get all clothing businesses
    clothing_businesses = Business.objects.filter(business_type__name__iexact='clothing')
    
    if not clothing_businesses.exists():
        print("\n❌ No clothing businesses found!")
        return
    
    # Check notifications from last 10 minutes
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)
    
    for business in clothing_businesses:
        print(f"\n{'='*60}")
        print(f"Business: {business.business_name}")
        print(f"{'='*60}")
        
        recent_notifications = Notification.objects.filter(
            business=business,
            created_at__gte=ten_minutes_ago
        ).order_by('-created_at')
        
        if recent_notifications.exists():
            print(f"\nFound {recent_notifications.count()} notifications in last 10 minutes:")
            print("-" * 60)
            
            for notif in recent_notifications:
                print(f"\n📬 Notification ID: {notif.id}")
                print(f"   Type: {notif.notification_type}")
                print(f"   Target: {notif.target_role}")
                print(f"   Title: {notif.title}")
                print(f"   Message: {notif.message}")
                print(f"   Read: {notif.is_read}")
                print(f"   Created: {notif.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"\n❌ No notifications found in last 10 minutes")
        
        # Show all unread notifications
        unread = Notification.objects.filter(
            business=business,
            is_read=False
        ).order_by('-created_at')
        
        print(f"\n{'='*60}")
        print(f"Total Unread Notifications: {unread.count()}")
        print(f"{'='*60}")
        
        if unread.exists():
            print("\nShowing last 5 unread:")
            for notif in unread[:5]:
                print(f"   - [{notif.target_role}] {notif.title} ({notif.created_at.strftime('%Y-%m-%d %H:%M')})")

if __name__ == '__main__':
    check_recent_notifications()
