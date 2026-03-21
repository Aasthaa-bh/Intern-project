from django.db import migrations


def fix_purchaseitem_relation_columns(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_purchaseitem" not in table_names:
            return

        columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_purchaseitem")
        }

        if "purchase_id" not in columns:
            cursor.execute("ALTER TABLE pos_purchaseitem ADD COLUMN purchase_id BIGINT NULL")
        if "item_id" not in columns:
            cursor.execute("ALTER TABLE pos_purchaseitem ADD COLUMN item_id BIGINT NULL")
        if "variant_id" not in columns:
            cursor.execute("ALTER TABLE pos_purchaseitem ADD COLUMN variant_id BIGINT NULL")

        cursor.execute("SHOW INDEX FROM pos_purchaseitem WHERE Key_name = 'pos_purchaseitem_purchase_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_purchaseitem_purchase_id_idx ON pos_purchaseitem (purchase_id)")

        cursor.execute("SHOW INDEX FROM pos_purchaseitem WHERE Key_name = 'pos_purchaseitem_item_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_purchaseitem_item_id_idx ON pos_purchaseitem (item_id)")

        cursor.execute("SHOW INDEX FROM pos_purchaseitem WHERE Key_name = 'pos_purchaseitem_variant_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_purchaseitem_variant_id_idx ON pos_purchaseitem (variant_id)")

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_purchaseitem'
              AND COLUMN_NAME = 'purchase_id'
              AND REFERENCED_TABLE_NAME = 'pos_purchase'
            """
        )
        if cursor.fetchone() is None and "pos_purchase" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_purchaseitem
                ADD CONSTRAINT pos_purchaseitem_purchase_id_fk
                FOREIGN KEY (purchase_id)
                REFERENCES pos_purchase(id)
                ON DELETE CASCADE
                """
            )

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_purchaseitem'
              AND COLUMN_NAME = 'item_id'
              AND REFERENCED_TABLE_NAME = 'pos_item'
            """
        )
        if cursor.fetchone() is None and "pos_item" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_purchaseitem
                ADD CONSTRAINT pos_purchaseitem_item_id_fk
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
              AND TABLE_NAME = 'pos_purchaseitem'
              AND COLUMN_NAME = 'variant_id'
              AND REFERENCED_TABLE_NAME = 'pos_itemvariant'
            """
        )
        if cursor.fetchone() is None and "pos_itemvariant" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_purchaseitem
                ADD CONSTRAINT pos_purchaseitem_variant_id_fk
                FOREIGN KEY (variant_id)
                REFERENCES pos_itemvariant(id)
                ON DELETE RESTRICT
                """
            )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0010_fix_orderitem_variant_column"),
    ]

    operations = [
        migrations.RunPython(fix_purchaseitem_relation_columns, noop_reverse),
    ]
