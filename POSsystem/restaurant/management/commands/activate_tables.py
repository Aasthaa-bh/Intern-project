import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from restaurant.models import ReceptionInvoice, DiningTable
from accounts.models import User
from django.utils import timezone

# Get user for created_by
user = User.objects.filter(is_superuser=True).first() or User.objects.first()

# Get tables
table4 = DiningTable.objects.get(table_number=4)
table5 = DiningTable.objects.get(table_number=5)

# Create invoice for Table 4
subtotal4 = Decimal('2500.00')
tax4 = subtotal4 * Decimal('0.13')
total4 = subtotal4 + tax4

invoice4 = ReceptionInvoice.objects.create(
    business=table4.business,
    table=table4,
    invoice_number=f"INV-{timezone.now().strftime('%Y%m%d')}-4001",
    customer_name="Shyam Prasad",
    customer_phone="9851234567",
    subtotal=subtotal4,
    tax_amount=tax4,
    discount_amount=Decimal('0.00'),
    total_amount=total4,
    status='PENDING',
    created_by=user
)

table4.status = 'OCCUPIED'
table4.save()

print(f"✓ Table 4 activated with Invoice {invoice4.invoice_number}")
print(f"  Customer: {invoice4.customer_name}")
print(f"  Amount: Rs. {invoice4.total_amount}")

# Create invoice for Table 5
subtotal5 = Decimal('1800.00')
tax5 = subtotal5 * Decimal('0.13')
total5 = subtotal5 + tax5

invoice5 = ReceptionInvoice.objects.create(
    business=table5.business,
    table=table5,
    invoice_number=f"INV-{timezone.now().strftime('%Y%m%d')}-5001",
    customer_name="Rita Kumari",
    customer_phone="9841567890",
    subtotal=subtotal5,
    tax_amount=tax5,
    discount_amount=Decimal('0.00'),
    total_amount=total5,
    status='PENDING',
    created_by=user
)

table5.status = 'OCCUPIED'
table5.save()

print(f"✓ Table 5 activated with Invoice {invoice5.invoice_number}")
print(f"  Customer: {invoice5.customer_name}")
print(f"  Amount: Rs. {invoice5.total_amount}")

print("\n=== All Tables Status ===")
for table in DiningTable.objects.all().order_by('table_number'):
    pending = ReceptionInvoice.objects.filter(table=table, status='PENDING').first()
    if pending:
        print(f"Table {table.table_number}: {table.status} - {pending.invoice_number} (Rs. {pending.total_amount})")
    else:
        print(f"Table {table.table_number}: {table.status}")
