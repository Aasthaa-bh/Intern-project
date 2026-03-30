from django.db import migrations


def fix_item_image_public_id_column(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_item" not in table_names:
            return

        columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_item")
        }
        if "image_public_id" not in columns:
            return

        cursor.execute(
            "ALTER TABLE pos_item MODIFY COLUMN image_public_id VARCHAR(255) NULL DEFAULT NULL"
        )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0015_merge_0005_itemvariant_barcode_image_0014_supplier_notes"),
    ]

    operations = [
        migrations.RunPython(fix_item_image_public_id_column, noop_reverse),
    ]
