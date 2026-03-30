#!/usr/bin/env python
"""Create missing clothing tables"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from django.db import connection

# SQL to create missing tables
sql_commands = [
    """
    CREATE TABLE IF NOT EXISTS `clothing_size` (
        `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
        `name` varchar(50) NOT NULL,
        `code` varchar(20) NOT NULL,
        `size_type` varchar(20) NOT NULL,
        `sort_order` integer UNSIGNED NOT NULL CHECK (`sort_order` >= 0),
        `is_active` bool NOT NULL,
        `created_at` datetime(6) NOT NULL,
        `updated_at` datetime(6) NOT NULL,
        `business_id` bigint NOT NULL,
        UNIQUE KEY `clothing_size_business_id_code_uniq` (`business_id`, `code`),
        FOREIGN KEY (`business_id`) REFERENCES `core_business` (`id`)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS `clothing_color` (
        `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
        `name` varchar(50) NOT NULL,
        `code` varchar(20) NOT NULL,
        `hex_code` varchar(7) NOT NULL,
        `is_active` bool NOT NULL,
        `created_at` datetime(6) NOT NULL,
        `updated_at` datetime(6) NOT NULL,
        `business_id` bigint NOT NULL,
        UNIQUE KEY `clothing_color_business_id_name_uniq` (`business_id`, `name`),
        FOREIGN KEY (`business_id`) REFERENCES `core_business` (`id`)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS `clothing_clothingitem` (
        `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
        `gender` varchar(20) NOT NULL,
        `material` varchar(100) NOT NULL,
        `fit` varchar(50) NOT NULL,
        `care_note` varchar(255) NOT NULL,
        `created_at` datetime(6) NOT NULL,
        `updated_at` datetime(6) NOT NULL,
        `item_id` bigint NOT NULL UNIQUE,
        FOREIGN KEY (`item_id`) REFERENCES `pos_item` (`id`)
    );
    """
]

with connection.cursor() as cursor:
    for sql in sql_commands:
        try:
            cursor.execute(sql)
            print(f"✓ Executed SQL successfully")
        except Exception as e:
            print(f"✗ Error: {e}")

print("\n✅ Done! Tables created.")
