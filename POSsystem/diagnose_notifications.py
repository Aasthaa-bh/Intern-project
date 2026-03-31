#!/usr/bin/env python
"""
Comprehensive notification system diagnosis
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from django.conf import settings
from clothing.models import Notification
from accounts.models import User
from core.models import Business
from django.test import RequestFactory
from core.context_processors import notifications as notifications_context
from django.db.models import Q

def diagnose():
    print("\n" + "="*70)
    print("NOTIFICATION SYSTEM COMPREHENSIVE DIAGNOSIS")
    print("="*70)
    
    # 1. Check Settings
    print("\n1. CHECKING SETTINGS.PY")
    print("-" * 70)
    context_processors = None
    for template_engine in settings.TEMPLATES:
        if 'context_processors' in template_engine.get('OPTIONS', {}):
            context_processors = template_engine['OPTIONS']['context_processors']
            break
    
    if context_processors:
        print("✓ Context processors found:")
        for cp in context_processors:
            marker = "  ⚠️ " if 'business_context' in cp else "  ✓ "
            print(f"{marker}{cp}")
        
        if 'core.context_processors.business_context' in context_processors:
            print("\n❌ WARNING: business_context is still in settings!")
            print("   This will overwrite notification context variables.")
            print("   Remove it from settings.py")
    
    # 2. Check Database
    print("\n2. CHECKING DATABASE")
    print("-" * 70)
    
    user = User.objects.filter(username='puzan').first()
    if not user:
        print("❌ User 'puzan' not found!")
        return
    
    print(f"✓ User: {user.username}")
    print(f"  Role: {user.role}")
    print(f"  Business: {user.business.business_name if user.business else 'None'}")
    
    if not user.business:
        print("❌ User has no business!")
        return
    
    business = user.business
    business_type = business.business_type.name.strip().lower() if business.business_type else None
    print(f"  Business Type: {business_type}")
    
    # Check notifications in database
    if user.role in ['SUPERADMIN', 'OWNER']:
        role_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
    elif user.role == 'CASHIER':
        role_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
    else:
        role_filter = Q(target_role='ALL')
    
    all_notifications = Notification.objects.filter(
        business=business
    ).filter(role_filter)
    
    unread_notifications = all_notifications.filter(is_read=False)
    
    print(f"\n✓ Notifications in database:")
    print(f"  Total: {all_notifications.count()}")
    print(f"  Unread: {unread_notifications.count()}")
    
    if unread_notifications.exists():
        print(f"\n  Last 3 unread notifications:")
        for notif in unread_notifications[:3]:
            print(f"    - [{notif.target_role}] {notif.title}")
    
    # 3. Test Context Processor
    print("\n3. TESTING CONTEXT PROCESSOR")
    print("-" * 70)
    
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user
    
    try:
        context = notifications_context(request)
        
        print(f"✓ Context processor executed successfully")
        print(f"\n  Context variables:")
        print(f"    recent_notifications: {len(context.get('recent_notifications', []))} items")
        print(f"    unread_notifications_count: {context.get('unread_notifications_count', 0)}")
        print(f"    current_business: {context.get('current_business')}")
        print(f"    current_business_type: {context.get('current_business_type')}")
        print(f"    preferences: {context.get('preferences')}")
        
        if context.get('recent_notifications'):
            print(f"\n  Notifications returned by context processor:")
            for notif in context['recent_notifications']:
                print(f"    - [{notif.target_role}] {notif.title}")
        else:
            print(f"\n  ❌ Context processor returned EMPTY notifications list!")
            print(f"     But database has {unread_notifications.count()} unread notifications")
            print(f"     This indicates a problem in the context processor logic")
    
    except Exception as e:
        print(f"❌ Context processor failed with error:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Summary and Recommendations
    print("\n4. DIAGNOSIS SUMMARY")
    print("="*70)
    
    issues = []
    
    if 'core.context_processors.business_context' in context_processors:
        issues.append("Remove 'core.context_processors.business_context' from settings.py")
    
    if business_type != 'clothing':
        issues.append(f"Business type is '{business_type}', should be 'clothing'")
    
    if all_notifications.count() > 0 and len(context.get('recent_notifications', [])) == 0:
        issues.append("Context processor is not returning notifications despite them existing in DB")
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        
        print("\n📋 REQUIRED ACTIONS:")
        print("   1. Fix the issues listed above")
        print("   2. RESTART Django development server (Ctrl+C then python manage.py runserver)")
        print("   3. Hard refresh browser (Ctrl+F5)")
        print("   4. Run this script again to verify")
    else:
        print("\n✅ NO ISSUES FOUND!")
        print("   If notifications still don't show in UI:")
        print("   1. RESTART Django development server")
        print("   2. Clear browser cache and hard refresh (Ctrl+F5)")
        print("   3. Check browser console for JavaScript errors (F12)")
        print("   4. View page source and search for 'DEBUG:' comments")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    diagnose()
