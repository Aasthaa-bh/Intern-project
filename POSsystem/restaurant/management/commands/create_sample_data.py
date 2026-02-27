import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from core.models import Business
from accounts.models import User
from restaurant.models import DiningTable, ReceptionInvoice
from django.utils import timezone

# Get or create business
business = Business.objects.first()
if not business:
    print("No business found! Please create a business first.")
    exit()

# Get or create user
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("No admin user found!")
    exit()

# Create tables if they don't exist
tables_created = 0
for i in range(1, 6):
    table, created = DiningTable.objects.get_or_create(
        business=business,
        table_number=i,
        defaults={
            'capacity': 4,
            'category': 'NORMAL',
            'status': 'AVAILABLE'
        }
    )
    if created:
        tables_created += 1
        print(f"Created Table {i}")

# Create sample invoices for tables 1 and 2
invoice1, created1 = ReceptionInvoice.objects.get_or_create(
    business=business,
    table=DiningTable.objects.get(business=business, table_number=1),
    invoice_number='INV-2026-001',
    defaults={
        'customer_name': 'Ram Sharma',
        'customer_phone': '9841234567',
        'subtotal': 1500.00,
        'tax_amount': 195.00,  # 13% VAT
        'discount_amount': 0.00,
        'total_amount': 1695.00,
        'status': 'PENDING',
        'created_by': user
    }
)
if created1:
    print(f"Created Invoice for Table 1: {invoice1.invoice_number} - Rs. {invoice1.total_amount}")
    # Update table status
    table1 = DiningTable.objects.get(business=business, table_number=1)
    table1.status = 'OCCUPIED'
    table1.save()

invoice2, created2 = ReceptionInvoice.objects.get_or_create(
    business=business,
    table=DiningTable.objects.get(business=business, table_number=2),
    invoice_number='INV-2026-002',
    defaults={
        'customer_name': 'Sita Thapa',
        'customer_phone': '9851234567',
        'subtotal': 2500.00,
        'tax_amount': 325.00,  # 13% VAT
        'discount_amount': 100.00,
        'total_amount': 2725.00,
        'status': 'PENDING',
        'created_by': user
    }
)
if created2:
    print(f"Created Invoice for Table 2: {invoice2.invoice_number} - Rs. {invoice2.total_amount}")
    # Update table status
    table2 = DiningTable.objects.get(business=business, table_number=2)
    table2.status = 'OCCUPIED'
    table2.save()

print("\n✅ Sample data created successfully!")
print(f"- Tables: {DiningTable.objects.filter(business=business).count()}")
print(f"- Invoices: {ReceptionInvoice.objects.filter(business=business).count()}")
print(f"- Occupied Tables: {DiningTable.objects.filter(business=business, status='OCCUPIED').count()}")
print("\nNow you can test the payment system!")
print("Visit: http://127.0.0.1:8001/reception/tables/")
