from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from clothing.models import Notification, Offer


class Command(BaseCommand):
    help = 'Check for expiring offers and create notifications'

    def handle(self, *args, **options):
        today = timezone.now().date()
        three_days_later = today + timedelta(days=3)
        
        # Find offers expiring in next 3 days
        expiring_offers = Offer.objects.filter(
            status='ACTIVE',
            end_date__gte=today,
            end_date__lte=three_days_later
        ).select_related('business')
        
        for offer in expiring_offers:
            # Check if we already sent expiring notification for this offer
            existing_notification = Notification.objects.filter(
                business=offer.business,
                notification_type='OFFER_EXPIRING',
                title__icontains=offer.offer_name
            ).exists()
            
            if not existing_notification:
                days_left = (offer.end_date - today).days
                
                Notification.objects.create(
                    business=offer.business,
                    notification_type='OFFER_EXPIRING',
                    target_role='ADMIN',
                    title=f'Offer Expiring Soon: {offer.offer_name}',
                    message=f'This offer will expire in {days_left} day(s) on {offer.end_date}. {offer.get_discount_display()} discount.',
                    link=f'/clothing/offers/{offer.id}/',
                    is_read=False
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created expiring notification for offer: {offer.offer_name}'
                    )
                )
        
        # Find expired offers and update status
        expired_offers = Offer.objects.filter(
            status='ACTIVE',
            end_date__lt=today
        ).select_related('business')
        
        for offer in expired_offers:
            # Update status to expired
            offer.status = 'EXPIRED'
            offer.save()
            
            # Check if we already sent expired notification for this offer
            existing_notification = Notification.objects.filter(
                business=offer.business,
                notification_type='OFFER_EXPIRED',
                title__icontains=offer.offer_name
            ).exists()
            
            if not existing_notification:
                Notification.objects.create(
                    business=offer.business,
                    notification_type='OFFER_EXPIRED',
                    target_role='ADMIN',
                    title=f'Offer Expired: {offer.offer_name}',
                    message=f'This offer has expired on {offer.end_date}.',
                    link=f'/clothing/offers/{offer.id}/',
                    is_read=False
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created expired notification for offer: {offer.offer_name}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Checked {expiring_offers.count()} expiring and {expired_offers.count()} expired offers'
            )
        )
