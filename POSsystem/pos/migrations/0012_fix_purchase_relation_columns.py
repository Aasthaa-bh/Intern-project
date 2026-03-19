from django.db import migrations


def fix_purchase_relation_columns(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_purchase" not in table_names:
            return

        columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_purchase")
        }

        if "business_id" not in columns:
            cursor.execute("ALTER TABLE pos_purchase ADD COLUMN business_id BIGINT NULL")
        if "supplier_id" not in columns:
            cursor.execute("ALTER TABLE pos_purchase ADD COLUMN supplier_id BIGINT NULL")
        if "created_by_id" not in columns:
            cursor.execute("ALTER TABLE pos_purchase ADD COLUMN created_by_id BIGINT NULL")

        cursor.execute("SHOW INDEX FROM pos_purchase WHERE Key_name = 'pos_purchase_business_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_purchase_business_id_idx ON pos_purchase (business_id)")

        cursor.execute("SHOW INDEX FROM pos_purchase WHERE Key_name = 'pos_purchase_supplier_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_purchase_supplier_id_idx ON pos_purchase (supplier_id)")

        cursor.execute("SHOW INDEX FROM pos_purchase WHERE Key_name = 'pos_purchase_created_by_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_purchase_created_by_id_idx ON pos_purchase (created_by_id)")

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_purchase'
              AND COLUMN_NAME = 'business_id'
              AND REFERENCED_TABLE_NAME = 'core_business'
            """
        )
        if cursor.fetchone() is None and "core_business" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_purchase
                ADD CONSTRAINT pos_purchase_business_id_fk
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
              AND TABLE_NAME = 'pos_purchase'
              AND COLUMN_NAME = 'supplier_id'
              AND REFERENCED_TABLE_NAME = 'pos_supplier'
            """
        )
        if cursor.fetchone() is None and "pos_supplier" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_purchase
                ADD CONSTRAINT pos_purchase_supplier_id_fk
                FOREIGN KEY (supplier_id)
                REFERENCES pos_supplier(id)
                ON DELETE RESTRICT
                """
            )

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_purchase'
              AND COLUMN_NAME = 'created_by_id'
              AND REFERENCED_TABLE_NAME = 'accounts_user'
            """
        )
        if cursor.fetchone() is None and "accounts_user" in table_names:
            cursor.execute(
                """
                ALTER TABLE pos_purchase
                ADD CONSTRAINT pos_purchase_created_by_id_fk
                FOREIGN KEY (created_by_id)
                REFERENCES accounts_user(id)
                ON DELETE RESTRICT
                """
            )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0011_fix_purchaseitem_relation_columns"),
    ]

    operations = [
        migrations.RunPython(fix_purchase_relation_columns, noop_reverse),
    ]
