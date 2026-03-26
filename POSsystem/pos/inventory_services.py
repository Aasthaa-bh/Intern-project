from decimal import Decimal

from django.db import transaction
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from .models import Item, ItemVariant, Purchase, PurchaseItem, StockBatch, StockMovement


OUTBOUND_MOVEMENTS = {"SALE_OUT", "PURCHASE_RETURN_OUT", "ADJUSTMENT_OUT", "DAMAGE_OUT"}


def _to_decimal(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_stock_target(item: Item, variant: ItemVariant | None):
    return variant if variant else item


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


def apply_latest_cost_price(item: Item, variant: ItemVariant | None, unit_cost: Decimal, received_qty: Decimal):
    target = get_stock_target(item, variant)

    existing_qty = _to_decimal(target.stock_qty or 0)
    incoming_qty = _to_decimal(received_qty)
    incoming_cost = _to_decimal(unit_cost)

    if incoming_qty <= 0:
        return

    existing_cost = _to_decimal(target.cost_price) if target.cost_price is not None else incoming_cost

    total_qty = existing_qty + incoming_qty
    if total_qty <= 0:
        weighted_cost = incoming_cost
    else:
        weighted_cost = ((existing_qty * existing_cost) + (incoming_qty * incoming_cost)) / total_qty

    target.cost_price = weighted_cost.quantize(Decimal("0.01"))
    target.save(update_fields=["cost_price", "updated_at"])


def apply_latest_selling_price(item: Item, variant: ItemVariant | None, selling_price: Decimal | None):
    if selling_price is None:
        return

    target = get_stock_target(item, variant)
    normalized_price = _to_decimal(selling_price).quantize(Decimal("0.01"))
    target.price = normalized_price
    target.save(update_fields=["price", "updated_at"])


def create_purchase_batch(purchase: Purchase, line: PurchaseItem, quantity: Decimal):
    qty = _to_decimal(quantity)
    if qty <= 0:
        return None

    return StockBatch.objects.create(
        business=purchase.business,
        item=line.item,
        variant=line.variant,
        purchase=purchase,
        purchase_item=line,
        unit_cost=_to_decimal(line.unit_cost),
        quantity=qty,
        remaining_qty=qty,
        received_at=timezone.now(),
    )


def consume_stock_fifo(item: Item, variant: ItemVariant | None, quantity: Decimal):
    qty = _to_decimal(quantity)
    if qty <= 0:
        return None

    assert_stock_available(item, variant, qty)

    target = get_stock_target(item, variant)
    if not target.track_stock:
        return None

    remaining = qty
    total_cost = Decimal("0")

    batches = StockBatch.objects.select_for_update().filter(
        business=item.business,
        item=item,
        variant=variant,
        remaining_qty__gt=0,
    ).order_by("received_at", "id")

    for batch in batches:
        if remaining <= 0:
            break

        available = _to_decimal(batch.remaining_qty)
        consume_qty = available if available <= remaining else remaining
        if consume_qty <= 0:
            continue

        batch.remaining_qty = available - consume_qty
        batch.save(update_fields=["remaining_qty", "updated_at"])

        total_cost += consume_qty * _to_decimal(batch.unit_cost)
        remaining -= consume_qty

    if remaining > 0:
        fallback_cost = _to_decimal(target.cost_price) if target.cost_price is not None else Decimal("0")
        total_cost += remaining * fallback_cost
        remaining = Decimal("0")

    apply_stock_delta(item, variant, -qty)

    if qty > 0:
        return (total_cost / qty).quantize(Decimal("0.01"))
    return None


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

        apply_latest_cost_price(line.item, line.variant, line.unit_cost, requested)
        apply_latest_selling_price(line.item, line.variant, line.selling_price)
        apply_stock_delta(line.item, line.variant, requested)
        create_purchase_batch(purchase, line, requested)
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

        line.save(update_fields=["received_quantity", "received_at", "received_by"])
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
