from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Create missing restaurant tables'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                # Create ReceptionInvoice table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restaurant_receptioninvoice (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        invoice_number varchar(50) UNIQUE NOT NULL,
                        customer_name varchar(100),
                        customer_phone varchar(20),
                        subtotal decimal(10,2) NOT NULL,
                        tax_amount decimal(10,2) DEFAULT 0,
                        discount_amount decimal(10,2) DEFAULT 0,
                        total_amount decimal(10,2) NOT NULL,
                        transaction_uuid varchar(200),
                        status varchar(20) DEFAULT 'PENDING',
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL,
                        business_id bigint NOT NULL,
                        created_by_id bigint NOT NULL,
                        order_id bigint NULL,
                        table_id bigint NULL,
                        FOREIGN KEY (business_id) REFERENCES core_business(id),
                        FOREIGN KEY (created_by_id) REFERENCES accounts_user(id),
                        FOREIGN KEY (order_id) REFERENCES pos_order(id) ON DELETE SET NULL,
                        FOREIGN KEY (table_id) REFERENCES restaurant_diningtable(id) ON DELETE SET NULL
                    )
                """)
                self.stdout.write(self.style.SUCCESS('Created restaurant_receptioninvoice table'))
                
                # Create other missing tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restaurant_receptionpayment (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        payment_method varchar(20) NOT NULL,
                        amount decimal(10,2) NOT NULL,
                        transaction_id varchar(100),
                        transaction_uuid varchar(200),
                        payer_ref_code varchar(100),
                        payment_status varchar(20) DEFAULT 'PENDING',
                        note text,
                        processed_at datetime NOT NULL,
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL,
                        business_id bigint NOT NULL,
                        invoice_id bigint NOT NULL,
                        processed_by_id bigint NOT NULL,
                        FOREIGN KEY (business_id) REFERENCES core_business(id),
                        FOREIGN KEY (invoice_id) REFERENCES restaurant_receptioninvoice(id),
                        FOREIGN KEY (processed_by_id) REFERENCES accounts_user(id)
                    )
                """)
                self.stdout.write(self.style.SUCCESS('Created restaurant_receptionpayment table'))
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restaurant_ingredient (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        name varchar(100) NOT NULL,
                        unit varchar(20) NOT NULL,
                        quantity decimal(10,2) NOT NULL,
                        min_stock decimal(10,2) NOT NULL,
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL,
                        business_id bigint NOT NULL,
                        FOREIGN KEY (business_id) REFERENCES core_business(id)
                    )
                """)
                self.stdout.write(self.style.SUCCESS('Created restaurant_ingredient table'))
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restaurant_kitchenorder (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        status varchar(20) DEFAULT 'PENDING',
                        sent_at datetime NULL,
                        ready_at datetime NULL,
                        sent_to_cashier_at datetime NULL,
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL,
                        business_id bigint NOT NULL,
                        order_id bigint NOT NULL UNIQUE,
                        FOREIGN KEY (business_id) REFERENCES core_business(id),
                        FOREIGN KEY (order_id) REFERENCES pos_order(id)
                    )
                """)
                self.stdout.write(self.style.SUCCESS('Created restaurant_kitchenorder table'))
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restaurant_inventorystockhistory (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        ingredient_name varchar(100),
                        unit varchar(20),
                        change_type varchar(20) NOT NULL,
                        quantity_change decimal(10,2) NOT NULL,
                        price decimal(10,2) DEFAULT 0,
                        total_price decimal(12,2) DEFAULT 0,
                        note varchar(255),
                        changed_at datetime NOT NULL,
                        created_at datetime NOT NULL,
                        business_id bigint NOT NULL,
                        changed_by_id bigint NOT NULL,
                        ingredient_id bigint NOT NULL,
                        FOREIGN KEY (business_id) REFERENCES core_business(id),
                        FOREIGN KEY (changed_by_id) REFERENCES accounts_user(id),
                        FOREIGN KEY (ingredient_id) REFERENCES restaurant_ingredient(id)
                    )
                """)
                self.stdout.write(self.style.SUCCESS('Created restaurant_inventorystockhistory table'))
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restaurant_tablecategory (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        name varchar(50) NOT NULL,
                        code_prefix varchar(2) NOT NULL,
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL,
                        business_id bigint NOT NULL,
                        FOREIGN KEY (business_id) REFERENCES core_business(id),
                        UNIQUE KEY unique_business_prefix (business_id, code_prefix)
                    )
                """)
                self.stdout.write(self.style.SUCCESS('Created restaurant_tablecategory table'))
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS restaurant_receptionloyaltytransaction (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        customer_phone varchar(20) NOT NULL,
                        customer_name varchar(100) NOT NULL,
                        transaction_type varchar(20) NOT NULL,
                        points int NOT NULL,
                        balance_after int NOT NULL,
                        description varchar(255),
                        created_at datetime NOT NULL,
                        business_id bigint NOT NULL,
                        created_by_id bigint NOT NULL,
                        invoice_id bigint NULL,
                        FOREIGN KEY (business_id) REFERENCES core_business(id),
                        FOREIGN KEY (created_by_id) REFERENCES accounts_user(id),
                        FOREIGN KEY (invoice_id) REFERENCES restaurant_receptioninvoice(id) ON DELETE SET NULL
                    )
                """)
                self.stdout.write(self.style.SUCCESS('Created restaurant_receptionloyaltytransaction table'))
                
                self.stdout.write(self.style.SUCCESS('All tables created successfully!'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
