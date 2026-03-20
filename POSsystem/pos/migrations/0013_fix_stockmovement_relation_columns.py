from django.db import migrations


def fix_stockmovement_relation_columns(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_stockmovement" not in table_names:
            return

        columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_stockmovement")
        }

        if "business_id" not in columns:
            cursor.execute("ALTER TABLE pos_stockmovement ADD COLUMN business_id BIGINT NULL")
        if "item_id" not in columns:
            cursor.execute("ALTER TABLE pos_stockmovement ADD COLUMN item_id BIGINT NULL")
        if "variant_id" not in columns:
            cursor.execute("ALTER TABLE pos_stockmovement ADD COLUMN variant_id BIGINT NULL")
        if "created_by_id" not in columns:
            cursor.execute("ALTER TABLE pos_stockmovement ADD COLUMN created_by_id BIGINT NULL")

        cursor.execute("SHOW INDEX FROM pos_stockmovement WHERE Key_name = 'pos_stockmovement_business_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_stockmovement_business_id_idx ON pos_stockmovement (business_id)")

        cursor.execute("SHOW INDEX FROM pos_stockmovement WHERE Key_name = 'pos_stockmovement_item_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_stockmovement_item_id_idx ON pos_stockmovement (item_id)")

        cursor.execute("SHOW INDEX FROM pos_stockmovement WHERE Key_name = 'pos_stockmovement_variant_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_stockmovement_variant_id_idx ON pos_stockmovement (variant_id)")

        cursor.execute("SHOW INDEX FROM pos_stockmovement WHERE Key_name = 'pos_stockmovement_created_by_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_stockmovement_created_by_id_idx ON pos_stockmovement (created_by_id)")

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_stockmovement'
              AND COLUMN_NAME = 'business_id'
              AND REFERENCED_TABLE_NAME = 'core_business'
            """
        )
        if cursor.fetchone() is None and "core_business" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_stockmovement
                ADD CONSTRAINT pos_stockmovement_business_id_fk
                FOREIGN KEY (business_id)
                REFERENCES core_business(id)
                ON DELETE CASCADE
                """
            )

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_stockmovement'
              AND COLUMN_NAME = 'item_id'
              AND REFERENCED_TABLE_NAME = 'pos_item'
            """
        )
        if cursor.fetchone() is None and "pos_item" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_stockmovement
                ADD CONSTRAINT pos_stockmovement_item_id_fk
                FOREIGN KEY (item_id)
                REFERENCES pos_item(id)
                ON DELETE RESTRICT
                """
            )

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_stockmovement'
              AND COLUMN_NAME = 'variant_id'
              AND REFERENCED_TABLE_NAME = 'pos_itemvariant'
            """
        )
        if cursor.fetchone() is None and "pos_itemvariant" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_stockmovement
                ADD CONSTRAINT pos_stockmovement_variant_id_fk
                FOREIGN KEY (variant_id)
                REFERENCES pos_itemvariant(id)
                ON DELETE RESTRICT
                """
            )

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_stockmovement'
              AND COLUMN_NAME = 'created_by_id'
              AND REFERENCED_TABLE_NAME = 'accounts_user'
            """
        )
        if cursor.fetchone() is None and "accounts_user" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_stockmovement
                ADD CONSTRAINT pos_stockmovement_created_by_id_fk
                FOREIGN KEY (created_by_id)
                REFERENCES accounts_user(id)
                ON DELETE RESTRICT
                """
            )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0012_fix_purchase_relation_columns"),
    ]

    operations = [
        migrations.RunPython(fix_stockmovement_relation_columns, noop_reverse),
    ]
