#!/usr/bin/env python
"""Fix transaction IDs - replace KHALTI with ESEWA"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from restaurant.models import ReceptionPayment

# Update all transaction IDs containing KHALTI
payments = ReceptionPayment.objects.filter(transaction_id__icontains='KHALTI')
count = 0
for payment in payments:
    payment.transaction_id = payment.transaction_id.replace('KHALTI', 'ESEWA')
    payment.save()
    count += 1

print(f'✅ Updated {count} transaction IDs from KHALTI to ESEWA')
