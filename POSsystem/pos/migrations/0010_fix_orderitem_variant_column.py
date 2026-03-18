from django.db import migrations


def fix_orderitem_variant_column(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_orderitem" not in table_names or "pos_itemvariant" not in table_names:
            return

        orderitem_columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_orderitem")
        }

        if "variant_id" not in orderitem_columns:
            cursor.execute("ALTER TABLE pos_orderitem ADD COLUMN variant_id BIGINT NULL")

        cursor.execute("SHOW INDEX FROM pos_orderitem WHERE Key_name = 'pos_orderitem_variant_id_idx'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE INDEX pos_orderitem_variant_id_idx ON pos_orderitem (variant_id)")

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'pos_orderitem'
              AND COLUMN_NAME = 'variant_id'
              AND REFERENCED_TABLE_NAME = 'pos_itemvariant'
            """
        )
        if cursor.fetchone() is None:
            cursor.execute(
                """
                ALTER TABLE pos_orderitem
                ADD CONSTRAINT pos_orderitem_variant_id_fk
                FOREIGN KEY (variant_id)
                REFERENCES pos_itemvariant(id)
                ON DELETE RESTRICT
                """
            )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0009_fix_itemvariant_barcode_image_column"),
    ]

    operations = [
        migrations.RunPython(fix_orderitem_variant_column, noop_reverse),
    ]
