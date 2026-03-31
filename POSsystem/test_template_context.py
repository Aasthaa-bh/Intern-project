#!/usr/bin/env python
"""
Test if context processor is working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from accounts.models import User
from core.context_processors import notifications

def test_context_processor():
    print("\n" + "="*60)
    print("CONTEXT PROCESSOR TEST")
    print("="*60)
    
    # Create a fake request
    factory = RequestFactory()
    request = factory.get('/')
    
    # Test with puzan user
    try:
        user = User.objects.get(username='puzan')
        request.user = user
        
        print(f"\n✓ Testing with user: {user.username}")
        print(f"   Role: {user.role}")
        print(f"   Business: {user.business.business_name if user.business else 'None'}")
        
        # Call context processor
        context = notifications(request)
        
        print(f"\n{'='*60}")
        print("CONTEXT PROCESSOR OUTPUT")
        print(f"{'='*60}")
        
        print(f"\nrecent_notifications: {len(context['recent_notifications'])} items")
        print(f"unread_notifications_count: {context['unread_notifications_count']}")
        print(f"current_business: {context['current_business']}")
        print(f"current_business_type: {context['current_business_type']}")
        
        if context['recent_notifications']:
            print(f"\nNotifications:")
            for notif in context['recent_notifications']:
                print(f"   - [{notif.target_role}] {notif.title}")
        else:
            print("\n❌ No notifications in context!")
            
    except User.DoesNotExist:
        print("\n❌ User 'puzan' not found!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_context_processor()
