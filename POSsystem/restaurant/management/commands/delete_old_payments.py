#!/usr/bin/env python
"""Delete old converted eSewa payments"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from restaurant.models import ReceptionPayment

# Delete all eSewa payments (converted from Khalti)
payments = ReceptionPayment.objects.filter(payment_method='ESEWA')
count = payments.count()
payments.delete()

print(f'✅ Deleted {count} old eSewa payments')
print('Now you can test fresh payments!')
