from clothing.models import Notification
from datetime import timedelta
from django.utils import timezone

print(f'Total notifications: {Notification.objects.count()}')

three_days_ago = timezone.now() - timedelta(days=3)
recent = Notification.objects.filter(created_at__gte=three_days_ago)
print(f'Recent (last 3 days): {recent.count()}')

for n in recent[:10]:
    print(f'  - {n.title} | Business: {n.business.business_name} | Read: {n.is_read} | Created: {n.created_at}')
