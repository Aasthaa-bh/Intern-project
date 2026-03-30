from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0016_fix_item_image_public_id_column"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=10)),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=10)),
                ("remaining_qty", models.DecimalField(decimal_places=2, max_digits=10)),
                ("received_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("business", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.business")),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="pos.item")),
                ("purchase", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="pos.purchase")),
                ("purchase_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="pos.purchaseitem")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="pos.itemvariant")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["business", "item", "received_at"], name="pos_stockbat_busines_69bf73_idx"),
                    models.Index(fields=["variant", "received_at"], name="pos_stockbat_variant_72b74f_idx"),
                    models.Index(fields=["business", "remaining_qty"], name="pos_stockbat_busines_d2ecb1_idx"),
                ],
            },
        ),
    ]
