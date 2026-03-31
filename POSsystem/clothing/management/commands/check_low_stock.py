from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from clothing.models import Notification
from pos.models import ItemVariant
from core.models import Business


class Command(BaseCommand):
    help = 'Check for low stock items and create notifications'

    def handle(self, *args, **options):
        # Get all clothing businesses
        clothing_businesses = Business.objects.filter(business_type__name__iexact='clothing')
        
        for business in clothing_businesses:
            # Find low stock variants (stock <= reorder_level)
            low_stock_variants = ItemVariant.objects.filter(
                item__business=business,
                stock__lte=models.F('reorder_level'),
                reorder_level__gt=0,
                is_active=True
            ).select_related('item')
            
            if low_stock_variants.exists():
                # Check if we already sent a notification today
                today = timezone.now().date()
                existing_notification = Notification.objects.filter(
                    business=business,
                    notification_type='LOW_STOCK',
                    created_at__date=today
                ).exists()
                
                if not existing_notification:
                    low_stock_count = low_stock_variants.count()
                    low_stock_items = ', '.join([
                        f"{v.item.name} ({v.sku})" 
                        for v in low_stock_variants[:3]
                    ])
                    
                    if low_stock_count > 3:
                        low_stock_items += f" and {low_stock_count - 3} more"
                    
                    Notification.objects.create(
                        business=business,
                        notification_type='LOW_STOCK',
                        target_role='ADMIN',
                        title=f'Low Stock Alert: {low_stock_count} items',
                        message=f'The following items are running low: {low_stock_items}',
                        link='/clothing/low-stock/',
                        is_read=False
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created low stock notification for {business.business_name}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Low stock notification already sent today for {business.business_name}'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'No low stock items for {business.business_name}'
                    )
                )
