from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0017_stockbatch_fifo"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseitem",
            name="selling_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
