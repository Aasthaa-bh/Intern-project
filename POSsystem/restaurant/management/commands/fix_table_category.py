from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix table category issue'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                # First, create a default category
                cursor.execute("""
                    INSERT INTO restaurant_tablecategory (name, code_prefix, created_at, updated_at, business_id)
                    SELECT 'Cabin', 'C', NOW(), NOW(), id FROM core_business LIMIT 1
                """)
                self.stdout.write(self.style.SUCCESS('Created default category'))
                
                # Get the category id
                cursor.execute("SELECT id FROM restaurant_tablecategory WHERE code_prefix='C' LIMIT 1")
                category_id = cursor.fetchone()[0]
                
                # Add category_id column as nullable first
                cursor.execute("""
                    ALTER TABLE restaurant_diningtable 
                    ADD COLUMN category_id bigint NULL
                """)
                self.stdout.write(self.style.SUCCESS('Added category_id column'))
                
                # Update existing tables with the category
                cursor.execute(f"""
                    UPDATE restaurant_diningtable 
                    SET category_id = {category_id}
                """)
                self.stdout.write(self.style.SUCCESS('Updated existing tables'))
                
                # Now make it NOT NULL
                cursor.execute("""
                    ALTER TABLE restaurant_diningtable 
                    MODIFY category_id bigint NOT NULL
                """)
                
                # Add foreign key
                cursor.execute("""
                    ALTER TABLE restaurant_diningtable 
                    ADD CONSTRAINT fk_table_category 
                    FOREIGN KEY (category_id) REFERENCES restaurant_tablecategory(id)
                """)
                self.stdout.write(self.style.SUCCESS('Added foreign key constraint'))
                
                self.stdout.write(self.style.SUCCESS('Successfully fixed table category!'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
