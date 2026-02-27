import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from restaurant.models import ReceptionInvoice, DiningTable

print("=== Resetting All Tables ===\n")

# Mark all pending invoices as PAID
pending_invoices = ReceptionInvoice.objects.filter(status='PENDING')
count = pending_invoices.count()

for invoice in pending_invoices:
    invoice.status = 'PAID'
    invoice.save()
    print(f"✓ Invoice {invoice.invoice_number} marked as PAID")

print(f"\nTotal invoices updated: {count}")

# Set all tables to AVAILABLE
tables = DiningTable.objects.all()
for table in tables:
    table.status = 'AVAILABLE'
    table.save()
    print(f"✓ Table {table.table_number} set to AVAILABLE")

print("\n=== All Tables Status ===")
for table in DiningTable.objects.all().order_by('table_number'):
    print(f"Table {table.table_number}: {table.status}")

print("\n✅ All tables are now AVAILABLE!")
