from decimal import Decimal

from django.db import transaction
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from .models import Item, ItemVariant, Purchase, StockMovement


OUTBOUND_MOVEMENTS = {"SALE_OUT", "PURCHASE_RETURN_OUT", "ADJUSTMENT_OUT", "DAMAGE_OUT"}


def _to_decimal(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_stock_target(item: Item, variant: ItemVariant | None):
    validate_item_variant_relation(item, variant)
    return variant if variant else item

def validate_item_variant_relation(item: Item, variant: ItemVariant | None):
    if item.has_variants and variant is None:
        raise ValueError(f"{item.name} requires a variant.")
    if not item.has_variants and variant is not None:
        raise ValueError(f"{item.name} does not use variants.")
    if variant is not None and variant.item_id != item.id:
        raise ValueError("Selected variant does not belong to the selected item.")

def assert_stock_available(item: Item, variant: ItemVariant | None, quantity: Decimal):
    target = get_stock_target(item, variant)
    current_qty = _to_decimal(target.stock_qty or 0)
    if current_qty < quantity:
        label = variant.name if variant else item.name
        raise ValueError(f"Insufficient stock for {label}. Available: {current_qty}, requested: {quantity}")


def apply_stock_delta(item: Item, variant: ItemVariant | None, delta: Decimal):
    target = get_stock_target(item, variant)
    if not target.track_stock:
        return

    current_qty = _to_decimal(target.stock_qty or 0)
    target.stock_qty = current_qty + delta
    target.save(update_fields=["stock_qty", "updated_at"])


def create_stock_movement(
    *,
    business,
    item: Item,
    variant: ItemVariant | None,
    movement_type: str,
    quantity: Decimal,
    created_by,
    reference_type: str = "",
    reference_id: int | None = None,
    note: str = "",
):
    qty = _to_decimal(quantity)
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")

    return StockMovement.objects.create(
        business=business,
        item=item,
        variant=variant,
        movement_type=movement_type,
        quantity=qty,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by=created_by,
    )


def recalculate_purchase_totals(purchase: Purchase):
    aggregate = purchase.items.aggregate(total=Sum("line_total"))
    subtotal = aggregate.get("total") or Decimal("0")

    purchase.subtotal_amount = subtotal
    purchase.total_amount = subtotal - (purchase.discount_amount or Decimal("0")) + (purchase.tax_amount or Decimal("0"))
    purchase.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])


@transaction.atomic
def receive_purchase_lines(purchase: Purchase, received_map: dict[int, Decimal], user):
    if purchase.status == "CANCELLED":
        raise ValueError("Cancelled purchase cannot be received.")

    lines = purchase.items.select_for_update().select_related("item", "variant")

    any_received = False
    for line in lines:
        remaining = _to_decimal(line.quantity) - _to_decimal(line.received_quantity)
        requested = _to_decimal(received_map.get(line.id, Decimal("0")))

        if requested <= 0:
            continue
        if requested > remaining:
            raise ValueError(f"Received quantity exceeds remaining quantity for {line.item_name_snapshot}.")

        apply_stock_delta(line.item, line.variant, requested)
        create_stock_movement(
            business=purchase.business,
            item=line.item,
            variant=line.variant,
            movement_type="PURCHASE_IN",
            quantity=requested,
            created_by=user,
            reference_type="PURCHASE",
            reference_id=purchase.id,
            note=f"Received in purchase {purchase.purchase_no}",
        )

        line.received_quantity = _to_decimal(line.received_quantity) + requested
        if line.received_quantity >= _to_decimal(line.quantity):
            line.received_at = timezone.now()
            line.received_by = user

        line.save(update_fields=["received_quantity", "received_at", "received_by", "updated_at"])
        any_received = True

    all_received = not lines.exclude(received_quantity__gte=models.F("quantity")).exists() if lines.exists() else False
    if all_received:
        purchase.status = "RECEIVED"
        purchase.received_at = timezone.now()
        purchase.received_by = user
        purchase.save(update_fields=["status", "received_at", "received_by", "updated_at"])

    return any_received, all_received


@transaction.atomic
def create_adjustment(
    *,
    business,
    item: Item,
    variant: ItemVariant | None,
    movement_type: str,
    quantity: Decimal,
    user,
    note: str = "",
):
    qty = _to_decimal(quantity)
    if movement_type in OUTBOUND_MOVEMENTS:
        assert_stock_available(item, variant, qty)
        delta = -qty
    else:
        delta = qty

    apply_stock_delta(item, variant, delta)
    return create_stock_movement(
        business=business,
        item=item,
        variant=variant,
        movement_type=movement_type,
        quantity=qty,
        created_by=user,
        reference_type="MANUAL",
        note=note,
    )
