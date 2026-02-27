from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from core.models import Business, BusinessType
from pos.models import Category, Item
from restaurant.models import TableCategory, DiningTable


class Command(BaseCommand):
    help = 'Setup test data for waiter system'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up test data...')

        # Create Business Type
        business_type, _ = BusinessType.objects.get_or_create(
            name='Restaurant',
            defaults={'description': 'Restaurant business type'}
        )

        # Create Business
        business, created = Business.objects.get_or_create(
            business_code='REST001',
            defaults={
                'business_type': business_type,
                'business_name': 'Test Restaurant',
                'address': 'Test Address, City',
                'status': 'ACTIVE'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Business created'))
        else:
            self.stdout.write('✓ Business already exists')

        # Create Waiter User
        waiter, created = User.objects.get_or_create(
            username='waiter1',
            defaults={
                'business': business,
                'role': 'WAITER',
                'full_name': 'John Waiter',
                'email': 'waiter@test.com',
                'is_first_login': False
            }
        )
        if created:
            waiter.set_password('waiter123')
            waiter.save()
            self.stdout.write(self.style.SUCCESS('✓ Waiter user created (username: waiter1, password: waiter123)'))
        else:
            self.stdout.write('✓ Waiter user already exists')

        # Create Table Categories
        cabin_cat, _ = TableCategory.objects.get_or_create(
            business=business,
            code_prefix='C',
            defaults={'name': 'Cabin'}
        )
        
        inside_cat, _ = TableCategory.objects.get_or_create(
            business=business,
            code_prefix='T',
            defaults={'name': 'Inside'}
        )
        
        outside_cat, _ = TableCategory.objects.get_or_create(
            business=business,
            code_prefix='O',
            defaults={'name': 'Outside'}
        )
        self.stdout.write(self.style.SUCCESS('✓ Table categories created'))

        # Create Dining Tables
        tables_data = [
            (cabin_cat, 1, 4),
            (cabin_cat, 2, 4),
            (cabin_cat, 3, 6),
            (inside_cat, 1, 2),
            (inside_cat, 2, 2),
            (inside_cat, 3, 4),
            (inside_cat, 4, 4),
            (outside_cat, 1, 6),
            (outside_cat, 2, 6),
        ]

        for category, number, capacity in tables_data:
            DiningTable.objects.get_or_create(
                business=business,
                category=category,
                number=number,
                defaults={
                    'capacity': capacity,
                    'status': 'AVAILABLE'
                }
            )
        self.stdout.write(self.style.SUCCESS('✓ Dining tables created'))

        # Create Menu Categories
        appetizers, _ = Category.objects.get_or_create(
            business=business,
            name='Appetizers'
        )
        
        main_course, _ = Category.objects.get_or_create(
            business=business,
            name='Main Course'
        )
        
        beverages, _ = Category.objects.get_or_create(
            business=business,
            name='Beverages'
        )
        
        desserts, _ = Category.objects.get_or_create(
            business=business,
            name='Desserts'
        )
        self.stdout.write(self.style.SUCCESS('✓ Menu categories created'))

        # Create Menu Items
        menu_items = [
            # Appetizers
            ('Spring Rolls', appetizers, 150, 50),
            ('Chicken Wings', appetizers, 250, 30),
            ('Garlic Bread', appetizers, 120, 40),
            ('Soup of the Day', appetizers, 180, 20),
            
            # Main Course
            ('Grilled Chicken', main_course, 450, 25),
            ('Beef Steak', main_course, 650, 15),
            ('Pasta Carbonara', main_course, 380, 30),
            ('Vegetable Biryani', main_course, 320, 35),
            ('Fish & Chips', main_course, 420, 20),
            ('Margherita Pizza', main_course, 350, 25),
            
            # Beverages
            ('Coca Cola', beverages, 80, 100),
            ('Fresh Juice', beverages, 120, 50),
            ('Coffee', beverages, 100, 80),
            ('Tea', beverages, 80, 80),
            ('Mineral Water', beverages, 50, 150),
            
            # Desserts
            ('Ice Cream', desserts, 150, 40),
            ('Chocolate Cake', desserts, 200, 20),
            ('Fruit Salad', desserts, 180, 25),
        ]

        for name, category, price, stock in menu_items:
            Item.objects.get_or_create(
                business=business,
                name=name,
                defaults={
                    'category': category,
                    'item_type': 'MENU',
                    'price': price,
                    'cost_price': price * 0.6,
                    'track_stock': True,
                    'stock_qty': stock,
                    'min_stock_qty': 10,
                    'is_active': True
                }
            )
        self.stdout.write(self.style.SUCCESS('✓ Menu items created'))

        self.stdout.write(self.style.SUCCESS('\n✅ Test data setup complete!'))
        self.stdout.write(self.style.SUCCESS('\nYou can now login with:'))
        self.stdout.write(self.style.SUCCESS('Username: waiter1'))
        self.stdout.write(self.style.SUCCESS('Password: waiter123'))
