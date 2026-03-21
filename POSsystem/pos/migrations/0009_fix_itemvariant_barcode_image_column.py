from django.db import migrations


def fix_itemvariant_barcode_image_column(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "mysql":
        return

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)
        if "pos_itemvariant" not in table_names:
            return

        variant_columns = {
            col.name for col in connection.introspection.get_table_description(cursor, "pos_itemvariant")
        }

        # Legacy databases may still have this non-null column even though the model does not.
        # Make it nullable to avoid INSERT failures when Django does not provide a value.
        if "barcode_image" in variant_columns:
            cursor.execute(
                "ALTER TABLE pos_itemvariant MODIFY COLUMN barcode_image VARCHAR(255) NULL DEFAULT NULL"
            )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0008_fix_itemvariant_item_column"),
    ]

    operations = [
        migrations.RunPython(fix_itemvariant_barcode_image_column, noop_reverse),
    ]
