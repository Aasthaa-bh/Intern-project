from django.db import migrations


def fix_supplier_business_column(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor

    if vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_supplier" not in table_names:
            return

        columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_supplier")
        }

        if "business_id" not in columns:
            cursor.execute("ALTER TABLE pos_supplier ADD COLUMN business_id BIGINT NULL")

        # Backfill supplier.business_id from existing purchases where possible.
        if "pos_purchase" in table_names:
            purchase_columns = {
                col.name for col in connection.introspection.get_table_description(cursor, "pos_purchase")
            }
            if "supplier_id" in purchase_columns and "business_id" in purchase_columns:
                cursor.execute(
                    """
                    UPDATE pos_supplier s
                    JOIN (
                        SELECT supplier_id, MIN(business_id) AS business_id
                        FROM pos_purchase
                        WHERE supplier_id IS NOT NULL
                        GROUP BY supplier_id
                    ) p ON p.supplier_id = s.id
                    SET s.business_id = p.business_id
                    WHERE s.business_id IS NULL
                    """
                )

        # Fallback: assign first available business for any leftover NULL rows.
        cursor.execute("SELECT id FROM core_business ORDER BY id ASC LIMIT 1")
        row = cursor.fetchone()
        if row:
            default_business_id = row[0]
            cursor.execute(
                "UPDATE pos_supplier SET business_id = %s WHERE business_id IS NULL",
                [default_business_id],
            )

        # Add index if missing.
        cursor.execute("SHOW INDEX FROM pos_supplier WHERE Key_name = 'pos_supplier_business_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_supplier_business_id_idx ON pos_supplier (business_id)")

        # Add FK constraint if missing.
        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_supplier'
              AND COLUMN_NAME = 'business_id'
              AND REFERENCED_TABLE_NAME = 'core_business'
            """
        )
        if cursor.fetchone() is None:
            cursor.execute(
                """
                ALTER TABLE pos_supplier
                ADD CONSTRAINT pos_supplier_business_id_fk
                FOREIGN KEY (business_id)
                REFERENCES core_business(id)
                ON DELETE CASCADE
                """
            )

        # Enforce NOT NULL if possible.
        cursor.execute("SELECT COUNT(*) FROM pos_supplier WHERE business_id IS NULL")
        null_count = cursor.fetchone()[0]
        if null_count == 0:
            cursor.execute("ALTER TABLE pos_supplier MODIFY COLUMN business_id BIGINT NOT NULL")


def noop_reverse(apps, schema_editor):
    # This is a repair migration; keep reverse as no-op to avoid destructive schema changes.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0006_purchase_receive_tracking"),
    ]

    operations = [
        migrations.RunPython(fix_supplier_business_column, noop_reverse),
    ]
