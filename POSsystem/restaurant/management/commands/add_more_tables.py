from django.core.management.base import BaseCommand
from restaurant.models import DiningTable, TableCategory
from core.models import Business


class Command(BaseCommand):
    help = 'Rename tables T4, T5, T6, T7 to C4, C5, C6, C7'

    def handle(self, *args, **options):
        business = Business.objects.first()
        
        if not business:
            self.stdout.write(self.style.ERROR('No business found!'))
            return
        
        # Get or create Cabin category
        cabin_category, created = TableCategory.objects.get_or_create(
            business=business,
            code_prefix='C',
            defaults={'name': 'Cabin'}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created category: {cabin_category.name}'))
        
        # Tables to rename: old_name -> new_name
        tables_to_rename = {
            'T4': 'C4',
            'T5': 'C5',
            'T6': 'C6',
            'T7': 'C7',
        }
        
        renamed_count = 0
        for old_name, new_name in tables_to_rename.items():
            try:
                table = DiningTable.objects.get(business=business, name=old_name)
                table.name = new_name
                table.category = cabin_category
                table.number = int(new_name[1:])  # Extract number from C4 -> 4
                table.save()
                renamed_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {new_name}'))
            except DiningTable.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Table {old_name} not found, skipping...'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Done! Renamed {renamed_count} tables'))
        
        # Show all tables
        all_tables = DiningTable.objects.filter(business=business).order_by('name')
        self.stdout.write(self.style.SUCCESS(f'\nTotal tables: {all_tables.count()}'))
        for table in all_tables:
            self.stdout.write(f'  - {table.name} ({table.category.name}) - {table.status}')
