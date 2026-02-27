import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from core.models import Business
from accounts.models import User
from restaurant.models import ReceptionInvoice, ReceptionPayment, ReceptionLoyaltyTransaction
from django.utils import timezone

# Get business and user
business = Business.objects.first()
user = User.objects.filter(is_superuser=True).first()

if not business or not user:
    print("Business or User not found!")
    exit()

# Get invoices
invoices = ReceptionInvoice.objects.filter(business=business)

if not invoices.exists():
    print("No invoices found!")
    exit()

# Add payment for first invoice
invoice1 = invoices.first()
payment1, created1 = ReceptionPayment.objects.get_or_create(
    business=business,
    invoice=invoice1,
    payment_method='CASH',
    defaults={
        'amount': invoice1.total_amount,
        'payment_status': 'COMPLETED',
        'processed_by': user,
        'transaction_id': f"CASH-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        'note': 'Full payment received'
    }
)

if created1:
    # Mark invoice as paid
    invoice1.status = 'PAID'
    invoice1.save()
    print(f"✅ Payment created for {invoice1.invoice_number}: Rs. {payment1.amount}")

# Add loyalty transaction
loyalty1, created_loyalty = ReceptionLoyaltyTransaction.objects.get_or_create(
    business=business,
    invoice=invoice1,
    customer_phone=invoice1.customer_phone,
    defaults={
        'customer_name': invoice1.customer_name,
        'transaction_type': 'EARN',
        'points': 169,  # 10% of amount as points
        'balance_after': 169,
        'description': f'Points earned from {invoice1.invoice_number}',
        'created_by': user
    }
)

if created_loyalty:
    print(f"✅ Loyalty points created: {loyalty1.points} points for {loyalty1.customer_name}")

# Add partial payment for second invoice
if invoices.count() > 1:
    invoice2 = invoices[1]
    payment2, created2 = ReceptionPayment.objects.get_or_create(
        business=business,
        invoice=invoice2,
        payment_method='KHALTI',
        defaults={
            'amount': 1000.00,
            'payment_status': 'COMPLETED',
            'processed_by': user,
            'transaction_id': 'KHALTI-20260222123456',
            'note': 'Partial payment via Khalti'
        }
    )
    
    if created2:
        print(f"✅ Partial payment created for {invoice2.invoice_number}: Rs. {payment2.amount}")

print("\n📊 Summary:")
print(f"Total Payments: {ReceptionPayment.objects.filter(business=business).count()}")
print(f"Total Loyalty Transactions: {ReceptionLoyaltyTransaction.objects.filter(business=business).count()}")
print(f"Paid Invoices: {ReceptionInvoice.objects.filter(business=business, status='PAID').count()}")
print(f"Pending Invoices: {ReceptionInvoice.objects.filter(business=business, status='PENDING').count()}")
print("\n✅ Test data created successfully!")
print("Visit: http://127.0.0.1:8001/reception/payment/history/")
