#!/usr/bin/env python
"""
Create sample clothing data for testing offers
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from core.models import Business
from pos.models import Item, ItemVariant, Category
from clothing.models import Size, Color, ClothingItem, ClothingVariantDetail
from accounts.models import User

def create_sample_data():
    # Get or create business
    business = Business.objects.first()
    if not business:
        print("No business found! Please create a business first.")
        return
    
    print(f"Using business: {business}")
    
    # Get or create user
    user = User.objects.filter(business=business).first()
    if not user:
        print("No user found! Please create a user first.")
        return
    
    # Create or get category
    category, _ = Category.objects.get_or_create(
        business=business,
        name="T-Shirts",
        defaults={'is_active': True}
    )
    print(f"Category: {category.name}")
    
    # Create sizes
    sizes_data = [
        {'name': 'Small', 'code': 'S', 'size_type': 'ALPHA', 'sort_order': 1},
        {'name': 'Medium', 'code': 'M', 'size_type': 'ALPHA', 'sort_order': 2},
        {'name': 'Large', 'code': 'L', 'size_type': 'ALPHA', 'sort_order': 3},
        {'name': 'X-Large', 'code': 'XL', 'size_type': 'ALPHA', 'sort_order': 4},
    ]
    
    sizes = []
    for size_data in sizes_data:
        size, created = Size.objects.get_or_create(
            business=business,
            code=size_data['code'],
            defaults=size_data
        )
        sizes.append(size)
        print(f"Size: {size.name} {'(created)' if created else '(exists)'}")
    
    # Create colors
    colors_data = [
        {'name': 'Black', 'code': 'BLK', 'hex_code': '#000000'},
        {'name': 'White', 'code': 'WHT', 'hex_code': '#FFFFFF'},
        {'name': 'Blue', 'code': 'BLU', 'hex_code': '#0000FF'},
        {'name': 'Red', 'code': 'RED', 'hex_code': '#FF0000'},
    ]
    
    colors = []
    for color_data in colors_data:
        color, created = Color.objects.get_or_create(
            business=business,
            name=color_data['name'],
            defaults=color_data
        )
        colors.append(color)
        print(f"Color: {color.name} {'(created)' if created else '(exists)'}")
    
    # Create products
    products_data = [
        {'name': 'Polo T-Shirt', 'price': 1500},
        {'name': 'Round Neck T-Shirt', 'price': 1200},
        {'name': 'V-Neck T-Shirt', 'price': 1300},
    ]
    
    for product_data in products_data:
        # Create Item
        item, created = Item.objects.get_or_create(
            business=business,
            name=product_data['name'],
            defaults={
                'category': category,
                'price': product_data['price'],
                'is_active': True,
            }
        )
        print(f"\nProduct: {item.name} {'(created)' if created else '(exists)'}")
        
        # Create ClothingItem
        clothing_item, _ = ClothingItem.objects.get_or_create(
            item=item,
            defaults={
                'gender': 'UNISEX',
                'material': 'Cotton',
                'fit': 'Regular Fit',
            }
        )
        
        # Create variants for each size and color combination
        variant_count = 0
        for size in sizes:
            for color in colors:
                variant_name = f"{size.name} / {color.name}"
                sku = f"{item.name[:3].upper()}-{size.code}-{color.code}"
                
                variant, v_created = ItemVariant.objects.get_or_create(
                    item=item,
                    name=variant_name,
                    defaults={
                        'business': business,
                        'sku': sku,
                        'price': item.price,
                        'cost_price': item.price * 0.6,
                        'stock_qty': 50,
                        'min_stock_qty': 10,
                        'is_active': True,
                    }
                )
                
                # Create ClothingVariantDetail
                detail, _ = ClothingVariantDetail.objects.get_or_create(
                    variant=variant,
                    defaults={
                        'size': size,
                        'color': color,
                    }
                )
                
                if v_created:
                    variant_count += 1
        
        print(f"  Created {variant_count} variants")
    
    print("\n✅ Sample clothing data created successfully!")
    print(f"Total Items: {Item.objects.filter(business=business).count()}")
    print(f"Total Variants: {ItemVariant.objects.filter(business=business).count()}")

if __name__ == '__main__':
    create_sample_data()
