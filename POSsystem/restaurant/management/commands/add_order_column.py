from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Add order_id column to restaurant_receptioninvoice table'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                # Check if column exists
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'restaurant_receptioninvoice' 
                    AND COLUMN_NAME = 'order_id'
                """)
                exists = cursor.fetchone()[0]
                
                if exists:
                    self.stdout.write(self.style.SUCCESS('Column order_id already exists'))
                else:
                    # Add the column
                    cursor.execute("""
                        ALTER TABLE restaurant_receptioninvoice 
                        ADD COLUMN order_id bigint NULL
                    """)
                    
                    # Add foreign key constraint
                    cursor.execute("""
                        ALTER TABLE restaurant_receptioninvoice 
                        ADD CONSTRAINT restaurant_receptioninvoice_order_id_fk 
                        FOREIGN KEY (order_id) REFERENCES pos_order(id) 
                        ON DELETE SET NULL
                    """)
                    
                    self.stdout.write(self.style.SUCCESS('Successfully added order_id column'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
