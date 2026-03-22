from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0013_fix_stockmovement_relation_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="notes",
            field=models.TextField(blank=True),
        ),
    ]
