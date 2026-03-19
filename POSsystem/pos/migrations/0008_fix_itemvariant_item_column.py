from django.db import migrations


def fix_itemvariant_item_column(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_itemvariant" not in table_names or "pos_item" not in table_names:
            return

        variant_columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_itemvariant")
        }

        if "item_id" not in variant_columns:
            cursor.execute("ALTER TABLE pos_itemvariant ADD COLUMN item_id BIGINT NULL")

        # Backfill from matching SKU within same business, when available.
        cursor.execute(
            """
            UPDATE pos_itemvariant v
            JOIN pos_item i
              ON i.business_id = v.business_id
             AND i.sku = v.sku
            SET v.item_id = i.id
            WHERE v.item_id IS NULL
              AND v.sku IS NOT NULL
              AND v.sku <> ''
            """
        )

        # Fallback per business to first available item.
        cursor.execute(
            """
            UPDATE pos_itemvariant v
            JOIN (
                SELECT business_id, MIN(id) AS item_id
                FROM pos_item
                GROUP BY business_id
            ) x ON x.business_id = v.business_id
            SET v.item_id = x.item_id
            WHERE v.item_id IS NULL
            """
        )

        # Final fallback to first item in system.
        cursor.execute("SELECT id FROM pos_item ORDER BY id ASC LIMIT 1")
        row = cursor.fetchone()
        if row:
            default_item_id = row[0]
            cursor.execute(
                "UPDATE pos_itemvariant SET item_id = %s WHERE item_id IS NULL",
                [default_item_id],
            )

        # Add index if missing.
        cursor.execute("SHOW INDEX FROM pos_itemvariant WHERE Key_name = 'pos_itemvariant_item_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_itemvariant_item_id_idx ON pos_itemvariant (item_id)")

        # Add FK if missing.
        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_itemvariant'
              AND COLUMN_NAME = 'item_id'
              AND REFERENCED_TABLE_NAME = 'pos_item'
            """
        )
        if cursor.fetchone() is None:
            cursor.execute(
                """
                ALTER TABLE pos_itemvariant
                ADD CONSTRAINT pos_itemvariant_item_id_fk
                FOREIGN KEY (item_id)
                REFERENCES pos_item(id)
                ON DELETE CASCADE
                """
            )

        # Enforce NOT NULL only when safe.
        cursor.execute("SELECT COUNT(*) FROM pos_itemvariant WHERE item_id IS NULL")
        null_count = cursor.fetchone()[0]
        if null_count == 0:
            cursor.execute("ALTER TABLE pos_itemvariant MODIFY COLUMN item_id BIGINT NOT NULL")


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0007_fix_supplier_business_column"),
    ]

    operations = [
        migrations.RunPython(fix_itemvariant_item_column, noop_reverse),
    ]
