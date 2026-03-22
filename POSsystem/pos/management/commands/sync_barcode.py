from django.core.management.base import BaseCommand

from pos.models import Item, ItemVariant
from pos.utils_barcode import generate_barcode_image


class Command(BaseCommand):
    help = "Sync has_variants, generate missing barcodes, and barcode images."

    def handle(self, *args, **options):
        for item in Item.objects.all():
            actual_has_variants = item.variants.exists()

            updates = []

            if item.has_variants != actual_has_variants:
                item.has_variants = actual_has_variants
                updates.append("has_variants")

            if item.item_type == "PRODUCT":
                if item.has_variants:
                    if item.barcode is not None:
                        item.barcode = None
                        updates.append("barcode")
                    if item.barcode_image:
                        item.barcode_image = ""
                        updates.append("barcode_image")
                else:
                    if not item.barcode:
                        item.barcode = item.generate_next_barcode()
                        updates.append("barcode")
                    if item.barcode and not item.barcode_image:
                        item.barcode_image = generate_barcode_image(
                            item.barcode,
                            f"item_{item.id}_{item.barcode}",
                        )
                        updates.append("barcode_image")

            if updates:
                item.save(update_fields=updates + ["updated_at"])

        for variant in ItemVariant.objects.select_related("item").all():
            updates = []

            if not variant.business_id and variant.item.business_id:
                variant.business = variant.item.business
                updates.append("business")

            if not variant.barcode:
                variant.barcode = variant.generate_next_barcode()
                updates.append("barcode")

            if variant.barcode and not variant.barcode_image:
                variant.barcode_image = generate_barcode_image(
                    variant.barcode,
                    f"variant_{variant.id}_{variant.barcode}",
                )
                updates.append("barcode_image")

            if updates:
                variant.save(update_fields=updates + ["updated_at"])

        self.stdout.write(self.style.SUCCESS("Barcode sync completed successfully."))