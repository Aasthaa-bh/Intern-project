#!/usr/bin/env python
"""Mark all eSewa payments as PENDING"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from restaurant.models import ReceptionPayment

# Update all eSewa payments to PENDING
payments = ReceptionPayment.objects.filter(payment_method='ESEWA', payment_status='COMPLETED')
count = payments.count()
payments.update(payment_status='PENDING')

print(f'✅ Marked {count} eSewa payments as PENDING')
