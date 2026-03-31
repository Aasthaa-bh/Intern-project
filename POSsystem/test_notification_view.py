"""
Add this to your urls.py temporarily to test:

from test_notification_view import test_notification_context

urlpatterns = [
    ...
    path('test-notifications/', test_notification_context, name='test_notifications'),
]

Then visit: http://127.0.0.1:8000/test-notifications/
"""

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from core.context_processors import notifications as notifications_context

@login_required
def test_notification_context(request):
    """Test view to see what context processor returns"""
    
    context = notifications_context(request)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Notification Context Test</title>
        <style>
            body {{ font-family: monospace; padding: 20px; }}
            .success {{ color: green; }}
            .error {{ color: red; }}
            .info {{ color: blue; }}
            pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Notification Context Processor Test</h1>
        
        <h2>User Info:</h2>
        <pre>
Username: {request.user.username}
Role: {request.user.role}
Business: {request.user.business.business_name if request.user.business else 'None'}
Business Type: {request.user.business.business_type.name if request.user.business and request.user.business.business_type else 'None'}
        </pre>
        
        <h2>Context Variables:</h2>
        <pre>
recent_notifications: {len(context.get('recent_notifications', []))} items
unread_notifications_count: {context.get('unread_notifications_count', 0)}
current_business: {context.get('current_business')}
current_business_type: {context.get('current_business_type')}
preferences: {context.get('preferences')}
        </pre>
        
        <h2>Notifications:</h2>
    """
    
    if context.get('recent_notifications'):
        html += '<div class="success">✓ Notifications found!</div><ul>'
        for notif in context['recent_notifications']:
            html += f'<li>[{notif.target_role}] {notif.title} - {notif.message[:50]}...</li>'
        html += '</ul>'
    else:
        html += '<div class="error">✗ No notifications in context!</div>'
    
    html += """
        <hr>
        <p><a href="javascript:history.back()">← Go Back</a></p>
    </body>
    </html>
    """
    
    return HttpResponse(html)
