#!/usr/bin/env python
"""
Check user details and what notifications they should see
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from accounts.models import User
from clothing.models import Notification
from django.db.models import Q

def check_user(username):
    print("\n" + "="*60)
    print(f"USER DETAILS CHECK: {username}")
    print("="*60)
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"\n❌ User '{username}' not found!")
        return
    
    print(f"\n✓ User found: {user.username}")
    print(f"   Full Name: {user.full_name}")
    print(f"   Role: {user.role}")
    print(f"   Business: {user.business.business_name if user.business else 'None'}")
    
    if user.business:
        business_type = user.business.business_type.name if user.business.business_type else 'None'
        print(f"   Business Type: {business_type}")
        
        # Check what notifications this user should see
        print(f"\n{'='*60}")
        print("NOTIFICATIONS FOR THIS USER")
        print(f"{'='*60}")
        
        # Determine filter based on role
        if user.role in ['SUPERADMIN', 'OWNER']:
            role_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
            print(f"\n✓ User role '{user.role}' sees: ADMIN + ALL notifications")
        elif user.role == 'CASHIER':
            role_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
            print(f"\n✓ User role '{user.role}' sees: CASHIER + ALL notifications")
        else:
            role_filter = Q(target_role='ALL')
            print(f"\n✓ User role '{user.role}' sees: ALL notifications only")
        
        # Get notifications
        notifications = Notification.objects.filter(
            business=user.business
        ).filter(role_filter).order_by('-created_at')
        
        unread_count = notifications.filter(is_read=False).count()
        
        print(f"\nTotal notifications: {notifications.count()}")
        print(f"Unread notifications: {unread_count}")
        
        if notifications.exists():
            print(f"\nLast 5 notifications:")
            print("-" * 60)
            for notif in notifications[:5]:
                status = "📬 UNREAD" if not notif.is_read else "✓ Read"
                print(f"\n{status}")
                print(f"   [{notif.target_role}] {notif.notification_type}")
                print(f"   Title: {notif.title}")
                print(f"   Created: {notif.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\n❌ No notifications found for this user")
    else:
        print("\n❌ User has no business assigned!")
        print("   This user will not see any notifications.")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = 'saurav'  # Default from screenshot
    
    check_user(username)
