from pos.models import Item, ItemVariant


def find_sellable_by_barcode(business, barcode: str):
    barcode = (barcode or "").strip()
    if not barcode:
        return None

    variant = (
        ItemVariant.objects.select_related("item")
        .filter(
            business=business,
            barcode=barcode,
            is_active=True,
            item__is_active=True,
            item__item_type="PRODUCT",
        )
        .first()
    )
    if variant:
        return {
            "type": "variant",
            "item": variant.item,
            "variant": variant,
            "price": variant.price if variant.price is not None else variant.item.price,
            "stock_qty": variant.stock_qty,
            "name": variant.item.name,
            "variant_name": variant.name,
            "barcode": variant.barcode,
            "sku": variant.sku or variant.item.sku or "",
        }

    item = (
        Item.objects.filter(
            business=business,
            barcode=barcode,
            is_active=True,
            item_type="PRODUCT",
            has_variants=False,
        )
        .first()
    )
    if item:
        return {
            "type": "item",
            "item": item,
            "variant": None,
            "price": item.price,
            "stock_qty": item.stock_qty,
            "name": item.name,
            "variant_name": "",
            "barcode": item.barcode,
            "sku": item.sku or "",
        }

    return None