import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from restaurant.models import ReceptionInvoice, ReceptionPayment
from accounts.models import User

# Get all pending invoices
pending = ReceptionInvoice.objects.filter(status='PENDING')

print("=== Pending Invoices ===\n")
for inv in pending:
    print(f"{inv.id}. Invoice: {inv.invoice_number}")
    print(f"   Table: {inv.table.table_number if inv.table else 'N/A'}")
    print(f"   Amount: Rs. {inv.total_amount}")
    print(f"   Customer: {inv.customer_name}")
    print()

if pending.count() == 0:
    print("No pending invoices!")
else:
    invoice_id = input("\nEnter invoice ID to mark as paid (or 'all' for all): ")
    
    if invoice_id.lower() == 'all':
        invoices = pending
    else:
        invoices = ReceptionInvoice.objects.filter(id=int(invoice_id))
    
    payment_method = input("Payment method (Cash/Khalti/eSewa) [default: Cash]: ").strip() or "Cash"
    
    user = User.objects.first()
    
    for invoice in invoices:
        # Create payment record
        payment = ReceptionPayment.objects.create(
            invoice=invoice,
            payment_method=payment_method,
            amount=invoice.total_amount,
            payment_status='COMPLETED',
            processed_by=user
        )
        
        # Mark invoice as paid
        invoice.status = 'PAID'
        invoice.save()
        
        # Free up table
        if invoice.table:
            invoice.table.status = 'AVAILABLE'
            invoice.table.save()
        
        print(f"\n✓ Invoice {invoice.invoice_number} marked as PAID")
        print(f"  Payment: Rs. {payment.amount} via {payment_method}")
        if invoice.table:
            print(f"  Table {invoice.table.table_number} is now AVAILABLE")
    
    print("\n✅ Payment processing complete!")
