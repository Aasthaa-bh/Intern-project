from decimal import Decimal, InvalidOperation
from datetime import timedelta, date
import json

from django.conf import settings
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import (
    JsonResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import Business
from pos.models import Order, OrderItem, Item
from restaurant.models import KitchenOrder

from .models import (
    DiningTable,
    Ingredient,
    InventoryStockHistory,
    ReceptionInvoice,
    ReceptionPayment,
    ReceptionLoyaltyTransaction,
)
from . import payment_service
from .esewa_utils import (
    prepare_esewa_form_data,
    generate_transaction_uuid,
    verify_esewa_payment,
    verify_esewa_response_signature,
    decode_esewa_callback_data,
)

KITCHEN_STATUSES = ("PENDING", "COOKING", "READY")


# ============================================================
# Common helpers
# ============================================================

def _parse_decimal(value, default=None):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _get_request_business(request):
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False) and getattr(user, "business_id", None):
        return user.business
    return None


def _get_dev_business_fallback():
    if not settings.DEBUG:
        return None
    return Business.objects.order_by("id").first()


def _get_stock_actor_user(request, business):
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return user

    if not settings.DEBUG or business is None:
        return None

    business_user = business.users.order_by("id").first()
    if business_user:
        return business_user

    from accounts.models import User
    return User.objects.order_by("id").first()


def _get_kitchen_status_map(request):
    data = request.session.get("kitchen_order_statuses", {})
    if isinstance(data, dict):
        return data
    return {}


def _build_stock_note(note):
    return (note or "").strip()


def _safe_money(value, default="0.00"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _award_loyalty_points(invoice, created_by=None):
    if not invoice.customer_phone:
        return

    points_earned = int(invoice.total_amount / 10)
    ReceptionLoyaltyTransaction.objects.create(
        business=invoice.business,
        invoice=invoice,
        customer_phone=invoice.customer_phone,
        customer_name=invoice.customer_name or "Customer",
        transaction_type="EARN",
        points=points_earned,
        balance_after=0,
        description=f"Points earned from invoice {invoice.invoice_number}",
        created_by=created_by or invoice.created_by,
    )


def _mark_invoice_paid(invoice):
    invoice.status = "PAID"
    invoice.save(update_fields=["status"])

    if invoice.table:
        invoice.table.status = "AVAILABLE"
        invoice.table.save(update_fields=["status"])


# ============================================================
# Kitchen
# ============================================================

def kitchen_dashboard(request):
    business = _get_request_business(request)
    if business is None:
        business = _get_dev_business_fallback()

    open_orders = Order.objects.filter(status="OPEN").select_related("table")
    if business:
        open_orders = open_orders.filter(business=business)

    open_order_ids = list(open_orders.values_list("id", flat=True))

    grouped_items = []
    if open_order_ids:
        grouped_items = (
            OrderItem.objects.filter(order_id__in=open_order_ids)
            .values("item_name_snapshot")
            .annotate(total_qty=Sum("quantity"), order_count=Count("order", distinct=True))
            .order_by("item_name_snapshot")
        )

    kitchen_status_map = _get_kitchen_status_map(request)
    orders = list(open_orders.order_by("opened_at")[:20])
    for order in orders:
        order.kitchen_status = kitchen_status_map.get(str(order.id), "PENDING")

    kitchen_status_counts = {status: 0 for status in KITCHEN_STATUSES}
    for order in orders:
        kitchen_status_counts[order.kitchen_status] = kitchen_status_counts.get(order.kitchen_status, 0) + 1

    context = {
        "open_order_count": open_orders.count(),
        "dine_in_count": open_orders.filter(order_type="DINE_IN").count(),
        "takeaway_count": open_orders.filter(order_type="TAKEAWAY").count(),
        "delivery_count": open_orders.filter(order_type="DELIVERY").count(),
        "grouped_items": grouped_items,
        "orders": orders,
        "pending_count": kitchen_status_counts.get("PENDING", 0),
        "cooking_count": kitchen_status_counts.get("COOKING", 0),
        "ready_count": kitchen_status_counts.get("READY", 0),
    }
    return render(request, "restaurant/kitchen_dashboard.html", context)


def kitchen_stock(request):
    business = _get_request_business(request)
    if business is None:
        business = _get_dev_business_fallback()

    form_error = None

    if request.method == "POST":
        actor_user = _get_stock_actor_user(request, business)
        if not business or actor_user is None:
            return HttpResponseForbidden(
                "No business/user available for kitchen stock update. Create a business and at least one user."
            )

        action = request.POST.get("action") or "add_stock"

        if action == "add_stock":
            quantity_to_add = _parse_decimal(request.POST.get("quantity"))
            price_value = _parse_decimal(request.POST.get("price"))

            if quantity_to_add is None or quantity_to_add <= 0:
                form_error = "Enter a valid quantity greater than zero."
            elif price_value is not None and price_value < 0:
                form_error = "Enter a valid price."
            else:
                ingredient = None
                ingredient_name = (request.POST.get("ingredient_name") or "").strip()
                unit = (request.POST.get("unit") or "").strip()

                if not ingredient_name or not unit:
                    form_error = "Ingredient and unit are required."
                else:
                    ingredient = Ingredient.objects.filter(
                        business=business,
                        name__iexact=ingredient_name
                    ).first()

                    if ingredient:
                        ingredient.unit = unit
                    else:
                        ingredient = Ingredient.objects.create(
                            business=business,
                            name=ingredient_name,
                            unit=unit,
                            quantity=Decimal("0"),
                            min_stock=Decimal("0"),
                        )

                if ingredient is not None and form_error is None:
                    note = (request.POST.get("note") or "").strip()
                    if price_value is not None:
                        price_note = f"Price: {price_value}"
                        note = f"{note} | {price_note}" if note else price_note

                    ingredient.quantity = (ingredient.quantity or Decimal("0")) + quantity_to_add
                    ingredient.save()

                    price_amount = price_value or Decimal("0")

                    InventoryStockHistory.objects.create(
                        business=business,
                        ingredient=ingredient,
                        ingredient_name=ingredient.name,
                        unit=ingredient.unit,
                        change_type="ADD",
                        quantity_change=quantity_to_add,
                        price=price_amount,
                        total_price=quantity_to_add * price_amount,
                        note=note,
                        changed_by=actor_user,
                        changed_at=timezone.now(),
                    )
                    return redirect("restaurant_kitchen_stock")
        else:
            form_error = "Unsupported kitchen stock action."

    ingredients = Ingredient.objects.none()
    recent_changes = InventoryStockHistory.objects.none()
    low_stock_count = 0

    if business:
        ingredients = list(Ingredient.objects.filter(business=business).order_by("name"))
        recent_changes = list(
            InventoryStockHistory.objects.filter(business=business)
            .select_related("ingredient", "changed_by")
            .order_by("-changed_at", "-id")[:20]
        )

        for change in recent_changes:
            change.edit_note = (change.note or "").strip()
            change.edit_price = change.price

        ingredient_price_map = {}
        ingredient_ids = [item.id for item in ingredients]
        if ingredient_ids:
            latest_adds = (
                InventoryStockHistory.objects.filter(
                    business=business,
                    change_type="ADD",
                    ingredient_id__in=ingredient_ids
                )
                .select_related("ingredient")
                .order_by("ingredient_id", "-changed_at", "-id")
            )
            for change in latest_adds:
                if change.ingredient_id in ingredient_price_map:
                    continue
                ingredient_price_map[change.ingredient_id] = change.price

        for item in ingredients:
            item.latest_price = ingredient_price_map.get(item.id, "")

        low_stock_count = sum(1 for item in ingredients if item.quantity <= item.min_stock)

    context = {
        "ingredients": ingredients,
        "recent_changes": recent_changes,
        "low_stock_count": low_stock_count,
        "business": business,
        "form_error": form_error,
    }
    return render(request, "restaurant/kitchen_stock.html", context)


def kitchen_stock_change_delete(request, change_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    business = _get_request_business(request)
    if business is None:
        business = _get_dev_business_fallback()

    actor_user = _get_stock_actor_user(request, business)
    if not business or actor_user is None:
        return HttpResponseForbidden(
            "No business/user available for kitchen stock update. Create a business and at least one user."
        )

    change = get_object_or_404(
        InventoryStockHistory.objects.select_related("ingredient"),
        pk=change_id,
        business=business,
    )

    if change.change_type != "ADD":
        return HttpResponseForbidden("Only ADD stock entries can be deleted from kitchen history.")

    ingredient = change.ingredient
    if ingredient.quantity < change.quantity_change:
        return HttpResponseForbidden(
            "Cannot delete this entry because current stock is lower than the added quantity."
        )

    ingredient.quantity = ingredient.quantity - change.quantity_change
    ingredient.save(update_fields=["quantity", "updated_at"])
    change.delete()

    return redirect("restaurant_kitchen_stock")


def kitchen_ingredient_delete(request, ingredient_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    business = _get_request_business(request)
    if business is None:
        business = _get_dev_business_fallback()

    actor_user = _get_stock_actor_user(request, business)
    if not business or actor_user is None:
        return HttpResponseForbidden(
            "No business/user available for kitchen stock update. Create a business and at least one user."
        )

    ingredient = get_object_or_404(Ingredient, pk=ingredient_id, business=business)
    ingredient.delete()
    return redirect("restaurant_kitchen_stock")


def kitchen_stock_change_edit(request, change_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    business = _get_request_business(request)
    if business is None:
        business = _get_dev_business_fallback()

    actor_user = _get_stock_actor_user(request, business)
    if not business or actor_user is None:
        return HttpResponseForbidden(
            "No business/user available for kitchen stock update. Create a business and at least one user."
        )

    change = get_object_or_404(
        InventoryStockHistory.objects.select_related("ingredient"),
        pk=change_id,
        business=business,
    )

    if change.change_type != "ADD":
        return HttpResponseForbidden("Only ADD stock entries can be edited from kitchen history.")

    new_qty = _parse_decimal(request.POST.get("quantity"))
    new_price = _parse_decimal(request.POST.get("price"), default=None)
    new_note = (request.POST.get("note") or "").strip()

    if new_qty is None or new_qty <= 0:
        return HttpResponseForbidden("Enter a valid quantity greater than zero.")
    if new_price is not None and new_price < 0:
        return HttpResponseForbidden("Enter a valid price.")

    ingredient = change.ingredient
    delta = new_qty - change.quantity_change
    if delta < 0 and ingredient.quantity < abs(delta):
        return HttpResponseForbidden(
            "Cannot reduce this entry by that amount because current stock is too low."
        )

    ingredient.quantity = ingredient.quantity + delta
    ingredient.save(update_fields=["quantity", "updated_at"])

    change.quantity_change = new_qty
    price_amount = new_price or Decimal("0")
    change.price = price_amount
    change.total_price = new_qty * price_amount
    change.ingredient_name = change.ingredient.name
    change.unit = change.ingredient.unit
    change.note = _build_stock_note(new_note)
    change.changed_by = actor_user
    change.changed_at = timezone.now()
    change.save(
        update_fields=[
            "quantity_change",
            "price",
            "total_price",
            "ingredient_name",
            "unit",
            "note",
            "changed_by",
            "changed_at",
        ]
    )

    return redirect("restaurant_kitchen_stock")


def kitchen_order_status_update(request, order_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    business = _get_request_business(request)
    if business is None:
        business = _get_dev_business_fallback()

    if not business:
        return HttpResponseForbidden("No business available to update order status.")

    order = get_object_or_404(Order, pk=order_id, business=business)

    kitchen_status = (request.POST.get("kitchen_status") or "").strip().upper()
    if kitchen_status in KITCHEN_STATUSES:
        kitchen_status_map = _get_kitchen_status_map(request)
        kitchen_status_map[str(order.id)] = kitchen_status
        request.session["kitchen_order_statuses"] = kitchen_status_map
        request.session.modified = True
        return redirect("restaurant_kitchen_dashboard")

    next_status = (request.POST.get("status") or "").strip().upper()
    allowed_statuses = {"OPEN", "COMPLETED", "CANCELLED"}

    if next_status in allowed_statuses and order.status != next_status:
        actor_user = _get_stock_actor_user(request, business)
        order.status = next_status
        if actor_user:
            order.updated_by = actor_user
        if next_status in {"COMPLETED", "CANCELLED"} and not order.closed_at:
            order.closed_at = timezone.now()
        if next_status == "OPEN":
            order.closed_at = None

        update_fields = ["status", "closed_at", "updated_at"]
        if actor_user:
            update_fields.insert(1, "updated_by")
        order.save(update_fields=update_fields)

    return redirect("restaurant_kitchen_dashboard")


def create_order(request, table_number):
    if request.method == "POST":
        table = get_object_or_404(DiningTable, table_number=table_number)

        if table.status == "occupied":
            return JsonResponse({"error": "Table is already occupied."}, status=400)
        if table.status == "reserved":
            return JsonResponse({"error": "Table is reserved."}, status=400)

        order = Order.objects.create(table=table, total_amount=0.00, status="pending")
        order.confirm()
        table.status = "occupied"
        table.save()

        return JsonResponse(
            {
                "message": "Order created successfully.",
                "order_id": order.id,
                "table": table.table_number,
                "order_status": order.status,
            }
        )
    return JsonResponse({"error": "Invalid request method."}, status=405)


# ============================================================
# Reception dashboard and billing
# ============================================================

def reception_dashboard(request):
    business = Business.objects.first()

    if not business:
        context = {
            "total_tables": 0,
            "occupied_tables": 0,
            "available_tables": 0,
            "today_orders": 0,
            "today_revenue": 0,
            "pending_invoices": 0,
            "pending_payments": 0,
        }
        return render(request, "restaurant/reception_dashboard.html", context)

    total_tables = DiningTable.objects.filter(business=business).count()
    occupied_tables = DiningTable.objects.filter(business=business, status="OCCUPIED").count()
    available_tables = DiningTable.objects.filter(business=business, status="AVAILABLE").count()

    today = timezone.now().date()
    today_orders = ReceptionInvoice.objects.filter(
        business=business,
        created_at__date=today
    ).count()

    today_revenue = ReceptionPayment.objects.filter(
        business=business,
        payment_status="COMPLETED",
        created_at__date=today
    ).aggregate(total=Sum("amount"))["total"] or 0

    pending_invoices = ReceptionInvoice.objects.filter(
        business=business,
        status="PENDING"
    ).count()

    pending_payments = ReceptionPayment.objects.filter(
        business=business,
        payment_status="PENDING"
    ).count()

    recent_payments = ReceptionPayment.objects.filter(
        business=business,
        payment_status="COMPLETED"
    ).select_related("invoice").order_by("-processed_at")[:5]

    esewa_today = ReceptionPayment.objects.filter(
        business=business,
        payment_method="ESEWA",
        payment_status="COMPLETED",
        created_at__date=today
    ).aggregate(total=Sum("amount"), count=Count("id"))

    cash_today = ReceptionPayment.objects.filter(
        business=business,
        payment_method="CASH",
        payment_status="COMPLETED",
        created_at__date=today
    ).aggregate(total=Sum("amount"), count=Count("id"))

    context = {
        "total_tables": total_tables,
        "occupied_tables": occupied_tables,
        "available_tables": available_tables,
        "today_orders": today_orders,
        "today_revenue": today_revenue,
        "pending_invoices": pending_invoices,
        "pending_payments": pending_payments,
        "recent_payments": recent_payments,
        "esewa_today_amount": esewa_today["total"] or 0,
        "esewa_today_count": esewa_today["count"] or 0,
        "cash_today_amount": cash_today["total"] or 0,
        "cash_today_count": cash_today["count"] or 0,
    }
    return render(request, "restaurant/reception_dashboard.html", context)


def table_check(request):
    business = Business.objects.first()

    if business:
        tables = DiningTable.objects.filter(business=business).order_by("name")
        available_count = tables.filter(status="AVAILABLE").count()
        occupied_count = tables.filter(status="OCCUPIED").count()
        reserved_count = tables.filter(status="RESERVED").count()
    else:
        tables = []
        available_count = occupied_count = reserved_count = 0

    context = {
        "tables": tables,
        "available_count": available_count,
        "occupied_count": occupied_count,
        "reserved_count": reserved_count,
    }
    return render(request, "restaurant/table_check.html", context)


def table_bill(request, table_id):
    table = get_object_or_404(DiningTable, id=table_id)
    invoice = ReceptionInvoice.objects.filter(
        table=table,
        status="PENDING"
    ).order_by("-created_at").first()

    last_completed = ReceptionInvoice.objects.filter(
        table=table,
        status="PAID"
    ).order_by("-created_at").first()

    if invoice and table.status == "AVAILABLE":
        table.status = "RESERVED"
        table.save(update_fields=["status"])

    context = {
        "table": table,
        "invoice": invoice,
        "last_completed": last_completed,
    }
    return render(request, "restaurant/table_bill.html", context)


def guest_bill(request, invoice_id):
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    payments = ReceptionPayment.objects.filter(invoice=invoice)

    context = {
        "invoice": invoice,
        "payments": payments,
    }
    return render(request, "restaurant/guest_bill.html", context)


def payment_success(request, payment_id):
    payment = get_object_or_404(ReceptionPayment, id=payment_id)
    invoice = payment.invoice

    context = {
        "payment": payment,
        "invoice": invoice,
    }
    return render(request, "restaurant/payment_success.html", context)


def process_payment(request, invoice_id):
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")

        if not payment_method:
            messages.error(request, "Please select a payment method!")
            return redirect("process_payment", invoice_id=invoice.id)

        amount = _safe_money(request.POST.get("amount", 0))

        if payment_method == "CASH":
            payment = ReceptionPayment.objects.create(
                business=invoice.business,
                invoice=invoice,
                payment_method=payment_method,
                amount=amount,
                payment_status="COMPLETED",
                processed_by=request.user if request.user.is_authenticated else invoice.created_by,
                transaction_id=f"CASH-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                processed_at=timezone.now(),
            )

            total_paid = ReceptionPayment.objects.filter(
                invoice=invoice,
                payment_status="COMPLETED"
            ).aggregate(total=Sum("amount"))["total"] or 0

            if total_paid >= invoice.total_amount:
                _mark_invoice_paid(invoice)
                _award_loyalty_points(
                    invoice,
                    created_by=request.user if request.user.is_authenticated else invoice.created_by
                )
                messages.success(request, "Cash payment completed successfully! Table is now available.")
                return redirect("payment_success", payment_id=payment.id)

            messages.info(request, f"Partial payment received. Remaining: Rs. {invoice.total_amount - total_paid}")
            return redirect("guest_bill", invoice_id=invoice.id)

        elif payment_method == "ESEWA":
            return redirect("esewa_payment", invoice_id=invoice.id)

        else:
            messages.error(request, "Invalid payment method selected!")
            return redirect("process_payment", invoice_id=invoice.id)

    context = {"invoice": invoice}
    return render(request, "restaurant/process_payment.html", context)


# ============================================================
# Real eSewa integration for restaurant invoices
# ============================================================

def esewa_payment(request, invoice_id):
    """
    Real eSewa payment page.
    Renders a form that posts directly to eSewa.
    """
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)

    if invoice.status == "PAID":
        messages.error(request, "This invoice is already paid!")
        return redirect("guest_bill", invoice_id=invoice.id)

    payment = ReceptionPayment.objects.filter(
        invoice=invoice,
        payment_method="ESEWA",
        payment_status="PENDING"
    ).order_by("-id").first()

    if not payment:
        transaction_uuid = generate_transaction_uuid()

        invoice.transaction_uuid = transaction_uuid
        invoice.save(update_fields=["transaction_uuid"])

        payment = ReceptionPayment.objects.create(
            business=invoice.business,
            invoice=invoice,
            payment_method="ESEWA",
            amount=invoice.total_amount,
            payment_status="PENDING",
            processed_by=request.user if request.user.is_authenticated else invoice.created_by,
            transaction_uuid=transaction_uuid,
            note=f"eSewa payment initiated - UUID: {transaction_uuid}",
        )

    success_url = request.build_absolute_uri(reverse("restaurant_esewa_success"))
    failure_url = request.build_absolute_uri(reverse("restaurant_esewa_failure"))

    form_data = prepare_esewa_form_data(
        total_amount=payment.amount,
        transaction_uuid=payment.transaction_uuid,
        success_url=success_url,
        failure_url=failure_url,
        product_code=settings.ESEWA_PRODUCT_CODE,
    )

    context = {
        "invoice": invoice,
        "payment": payment,
        "form_data": form_data,
        "debug": settings.DEBUG,
    }
    return render(request, "restaurant/esewa_payment.html", context)


@csrf_exempt
def restaurant_esewa_success(request):
    """
    Handle eSewa success callback.
    """
    encoded_data = request.GET.get("data") or request.POST.get("data")

    callback_payload = None
    transaction_uuid = None
    callback_total_amount = None

    if encoded_data:
        try:
            callback_payload = decode_esewa_callback_data(encoded_data)
            transaction_uuid = callback_payload.get("transaction_uuid")
            callback_total_amount = callback_payload.get("total_amount")
        except Exception:
            messages.error(request, "Invalid eSewa callback data.")
            return redirect("reception_dashboard")

    transaction_uuid = (
        transaction_uuid
        or request.GET.get("transaction_uuid")
        or request.GET.get("pid")
        or request.GET.get("oid")
    )

    if not transaction_uuid:
        messages.error(request, "Missing transaction UUID.")
        return redirect("reception_dashboard")

    try:
        invoice = ReceptionInvoice.objects.get(transaction_uuid=transaction_uuid)
    except ReceptionInvoice.DoesNotExist:
        messages.error(request, "Invoice not found.")
        return redirect("reception_dashboard")

    if invoice.status == "PAID":
        payment = ReceptionPayment.objects.filter(
            invoice=invoice,
            payment_method="ESEWA",
            payment_status="COMPLETED",
        ).order_by("-id").first()

        if payment:
            return redirect("payment_success", payment_id=payment.id)
        return redirect("guest_bill", invoice_id=invoice.id)

    payment = ReceptionPayment.objects.filter(
        invoice=invoice,
        payment_method="ESEWA",
        transaction_uuid=transaction_uuid,
        payment_status="PENDING"
    ).order_by("-id").first()

    if not payment:
        messages.error(request, "Pending payment record not found.")
        return redirect("guest_bill", invoice_id=invoice.id)

    if callback_payload:
        if not verify_esewa_response_signature(callback_payload):
            payment.payment_status = "FAILED"
            payment.note = "Invalid eSewa response signature"
            payment.save(update_fields=["payment_status", "note"])
            messages.error(request, "Invalid eSewa response signature.")
            return redirect("process_payment", invoice_id=invoice.id)

    verify_amount = _safe_money(callback_total_amount or payment.amount)

    verification = verify_esewa_payment(
        transaction_uuid=transaction_uuid,
        total_amount=verify_amount,
        product_code=settings.ESEWA_PRODUCT_CODE,
    )

    if not verification.get("success"):
        payment.payment_status = "FAILED"
        payment.note = verification.get("message", "Payment verification failed")
        payment.save(update_fields=["payment_status", "note"])
        messages.error(request, payment.note)
        return redirect("process_payment", invoice_id=invoice.id)

    data = verification.get("data", {})
    esewa_status = str(data.get("status", "")).upper()
    verified_amount = _safe_money(data.get("total_amount", payment.amount))

    ref_id = data.get("ref_id")
    if not ref_id and callback_payload:
        ref_id = callback_payload.get("transaction_code")

    if esewa_status != "COMPLETE":
        payment.payment_status = "FAILED"
        payment.note = f"eSewa status: {esewa_status}"
        payment.save(update_fields=["payment_status", "note"])
        messages.error(request, f"Payment not completed. Status: {esewa_status}")
        return redirect("process_payment", invoice_id=invoice.id)

    if verified_amount != _safe_money(payment.amount):
        payment.payment_status = "FAILED"
        payment.note = "Amount mismatch detected during eSewa verification"
        payment.save(update_fields=["payment_status", "note"])
        messages.error(request, "Amount mismatch detected.")
        return redirect("process_payment", invoice_id=invoice.id)

    payment.payment_status = "COMPLETED"
    payment.transaction_id = ref_id or f"ESEWA-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    payment.note = f"eSewa payment verified - Ref: {payment.transaction_id}"
    payment.processed_at = timezone.now()
    payment.save(update_fields=["payment_status", "transaction_id", "note", "processed_at"])

    _mark_invoice_paid(invoice)
    _award_loyalty_points(
        invoice,
        created_by=request.user if request.user.is_authenticated else invoice.created_by
    )

    messages.success(request, "Payment completed successfully via eSewa.")
    return redirect("payment_success", payment_id=payment.id)


@csrf_exempt
def restaurant_esewa_failure(request):
    """
    Handle eSewa failure callback.
    """
    encoded_data = request.GET.get("data") or request.POST.get("data")
    transaction_uuid = None

    if encoded_data:
        try:
            payload = decode_esewa_callback_data(encoded_data)
            transaction_uuid = payload.get("transaction_uuid")
        except Exception:
            transaction_uuid = None

    transaction_uuid = (
        transaction_uuid
        or request.GET.get("transaction_uuid")
        or request.GET.get("pid")
        or request.GET.get("oid")
    )

    if transaction_uuid:
        try:
            invoice = ReceptionInvoice.objects.get(transaction_uuid=transaction_uuid)
            payment = ReceptionPayment.objects.filter(
                invoice=invoice,
                transaction_uuid=transaction_uuid,
                payment_method="ESEWA",
                payment_status="PENDING",
            ).order_by("-id").first()

            if payment:
                payment.payment_status = "FAILED"
                payment.note = "Payment cancelled or failed by user"
                payment.save(update_fields=["payment_status", "note"])

            messages.error(request, "Payment was cancelled or failed.")
            return redirect("process_payment", invoice_id=invoice.id)
        except ReceptionInvoice.DoesNotExist:
            pass

    messages.error(request, "Payment was cancelled or failed.")
    return redirect("reception_dashboard")


# Optional aliases if your old urls still point to esewa_success/esewa_failure
esewa_success = restaurant_esewa_success
esewa_failure = restaurant_esewa_failure


# ============================================================
# Partial / split / loyalty / history
# ============================================================

def partial_payment(request, invoice_id):
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)

    if request.method == "POST":
        amount = _safe_money(request.POST.get("amount", 0))
        payment_method = request.POST.get("payment_method")

        if amount > 0 and amount <= invoice.total_amount:
            ReceptionPayment.objects.create(
                business=invoice.business,
                invoice=invoice,
                payment_method=payment_method,
                amount=amount,
                payment_status="COMPLETED",
                processed_by=request.user if request.user.is_authenticated else invoice.created_by,
                transaction_id=f"PARTIAL-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                processed_at=timezone.now(),
            )
            messages.success(request, f"Partial payment of Rs. {amount} received!")
            return redirect("guest_bill", invoice_id=invoice.id)

    context = {"invoice": invoice}
    return render(request, "restaurant/partial_payment.html", context)


def split_bill(request, invoice_id):
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)

    if request.method == "POST":
        split_count = int(request.POST.get("split_count", 1))
        split_amount = invoice.total_amount / split_count

        context = {
            "invoice": invoice,
            "split_count": split_count,
            "split_amount": split_amount,
        }
        return render(request, "restaurant/split_bill.html", context)

    context = {"invoice": invoice}
    return render(request, "restaurant/split_bill.html", context)


def loyalty_points_check(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        business = Business.objects.first()

        if business:
            transactions = ReceptionLoyaltyTransaction.objects.filter(
                business=business,
                customer_phone=phone
            ).order_by("-created_at")[:10]

            total_earned = ReceptionLoyaltyTransaction.objects.filter(
                business=business,
                customer_phone=phone,
                transaction_type="EARN"
            ).aggregate(total=Sum("points"))["total"] or 0

            total_redeemed = ReceptionLoyaltyTransaction.objects.filter(
                business=business,
                customer_phone=phone,
                transaction_type="REDEEM"
            ).aggregate(total=Sum("points"))["total"] or 0

            current_balance = total_earned - total_redeemed

            if transactions.exists():
                context = {
                    "customer_phone": phone,
                    "customer_name": transactions.first().customer_name,
                    "current_balance": current_balance,
                    "transactions": transactions,
                }
                return render(request, "restaurant/loyalty_points_check.html", context)
            else:
                messages.error(request, "No loyalty transactions found for this customer!")

    return render(request, "restaurant/loyalty_points_check.html")


def payment_history(request):
    business = Business.objects.first()

    if business:
        payments = ReceptionPayment.objects.filter(
            business=business,
            payment_status="COMPLETED"
        ).select_related(
            "invoice", "processed_by"
        ).order_by("-processed_at")[:50]

        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        if date_from:
            payments = payments.filter(processed_at__date__gte=date_from)
        if date_to:
            payments = payments.filter(processed_at__date__lte=date_to)
    else:
        payments = []

    context = {"payments": payments}
    return render(request, "restaurant/payment_history.html", context)


# ============================================================
# Tables
# ============================================================

def update_table_status(request, table_id):
    table = get_object_or_404(DiningTable, id=table_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in ["AVAILABLE", "OCCUPIED", "RESERVED"]:
            table.status = new_status
            table.save(update_fields=["status"])
            messages.success(request, f"Table {table.table_number} status updated!")
        return redirect("table_check")

    context = {"table": table}
    return render(request, "restaurant/update_table_status.html", context)


def toggle_table_status(request, table_id):
    table = get_object_or_404(DiningTable, id=table_id)

    if request.method == "POST":
        if table.status == "OCCUPIED":
            table.status = "AVAILABLE"
            messages.success(request, f"Table {table.table_number} is now AVAILABLE")
        else:
            table.status = "OCCUPIED"
            messages.success(request, f"Table {table.table_number} is now OCCUPIED")

        table.save(update_fields=["status"])

    return redirect("table_bill", table_id=table.id)


def bulk_update_tables(request):
    if request.method == "POST":
        table_ids = request.POST.getlist("table_ids")
        status = request.POST.get("status")

        if status in ["AVAILABLE", "OCCUPIED", "RESERVED"]:
            tables = DiningTable.objects.filter(id__in=table_ids)
            count = tables.update(status=status)
            messages.success(request, f"{count} table(s) updated to {status}")

    return redirect("table_check")


def quick_status_change(request, table_id):
    if request.method == "POST":
        table = get_object_or_404(DiningTable, id=table_id)
        status = request.POST.get("status")

        if status in ["AVAILABLE", "OCCUPIED", "RESERVED"]:
            table.status = status
            table.save(update_fields=["status"])

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "message": f"Table {table.name} is now {status}"})

            messages.success(request, f"Table {table.name} is now {status}")
            return redirect("table_check")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": "Invalid status"}, status=400)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

    return redirect("table_check")


def bulk_update_all_tables(request):
    if request.method == "POST":
        status = request.POST.get("status")

        if status in ["AVAILABLE", "OCCUPIED", "RESERVED"]:
            business = Business.objects.first()

            if business:
                count = DiningTable.objects.filter(business=business).update(status=status)
                messages.success(request, f"All {count} tables updated to {status}")
            else:
                messages.error(request, "No business found")

    return redirect("table_check")


# ============================================================
# Invoices
# ============================================================

def create_invoice(request, table_id):
    from accounts.models import User

    table = get_object_or_404(DiningTable, id=table_id)

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "Guest")
        customer_phone = request.POST.get("customer_phone", "")
        subtotal = float(request.POST.get("subtotal", 0))

        tax_amount = subtotal * 0.13
        discount = float(request.POST.get("discount", 0))
        total = subtotal + tax_amount - discount

        import random
        invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        invoice = ReceptionInvoice.objects.create(
            business=table.business,
            table=table,
            invoice_number=invoice_number,
            customer_name=customer_name,
            customer_phone=customer_phone,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount,
            total_amount=total,
            status="PENDING",
            created_by=user,
        )

        table.status = "OCCUPIED"
        table.save(update_fields=["status"])

        messages.success(request, f"Invoice {invoice_number} created successfully!")
        return redirect("table_bill", table_id=table.id)

    context = {"table": table}
    return render(request, "restaurant/create_invoice.html", context)


def pending_invoices(request):
    business = Business.objects.first()

    if business:
        invoices = ReceptionInvoice.objects.filter(
            business=business,
            status="PENDING"
        ).select_related("table", "created_by").order_by("-created_at")
    else:
        invoices = []

    context = {"invoices": invoices}
    return render(request, "restaurant/pending_invoices.html", context)


# ============================================================
# Payment admin / verification
# ============================================================

def verify_payment(request, payment_id):
    payment = get_object_or_404(ReceptionPayment, id=payment_id)

    if request.method == "POST":
        transaction_id = request.POST.get("transaction_id", "").strip()

        from accounts.models import User
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        result = payment_service.verify_payment(payment_id, transaction_id, user)

        if result["success"]:
            msg = "Payment verified successfully!"
            if result["invoice_paid"]:
                msg += " Invoice marked as PAID."
            if result["table_freed"]:
                msg += " Table is now AVAILABLE."
            messages.success(request, msg)
            return redirect("guest_bill", invoice_id=payment.invoice.id)
        else:
            messages.error(request, result["message"])

    context = {"payment": payment}
    return render(request, "restaurant/verify_payment.html", context)


def pending_payments_list(request):
    business = Business.objects.first()

    if business:
        payments = payment_service.get_pending_payments(business)

        now = timezone.now()
        payments_with_time = []
        for payment in payments:
            elapsed = now - payment.processed_at
            elapsed_minutes = int(elapsed.total_seconds() / 60)
            payments_with_time.append({
                "payment": payment,
                "elapsed_minutes": elapsed_minutes,
                "highlight": elapsed_minutes > 10,
            })

        context = {"payments_data": payments_with_time}
    else:
        context = {"payments_data": []}

    return render(request, "restaurant/pending_payments_list.html", context)


# ============================================================
# QR payments
# ============================================================

def qr_payment(request, invoice_id):
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)

    if invoice.status == "PAID":
        messages.error(request, "This invoice is already paid!")
        return redirect("guest_bill", invoice_id=invoice_id)

    context = {
        "invoice": invoice,
        "qr_code_url": "/static/images/qr-code.png",
    }
    return render(request, "restaurant/qr_payment.html", context)


def confirm_qr_payment(request, invoice_id):
    if request.method != "POST":
        return redirect("qr_payment", invoice_id=invoice_id)

    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    payer_ref_code = request.POST.get("payer_ref_code", "").strip()

    if invoice.status == "PAID":
        messages.error(request, "This invoice is already paid!")
        return redirect("guest_bill", invoice_id=invoice_id)

    if not payer_ref_code:
        messages.error(request, "Transaction/Reference code is required!")
        return redirect("qr_payment", invoice_id=invoice_id)

    existing_payment = ReceptionPayment.objects.filter(
        invoice=invoice,
        payer_ref_code=payer_ref_code,
        payment_status="COMPLETED"
    ).first()

    if existing_payment:
        messages.error(request, "Payment with this reference code has already been processed!")
        return redirect("guest_bill", invoice_id=invoice_id)

    business = Business.objects.first()

    payment = ReceptionPayment.objects.create(
        business=business,
        invoice=invoice,
        payment_method="QR",
        amount=invoice.total_amount,
        payer_ref_code=payer_ref_code,
        payment_status="COMPLETED",
        note=f"QR payment confirmed with reference: {payer_ref_code}",
        processed_by=request.user if request.user.is_authenticated else None,
        processed_at=timezone.now(),
    )

    _mark_invoice_paid(invoice)

    messages.success(request, f"Payment of Rs. {invoice.total_amount} confirmed successfully!")
    return redirect("guest_bill", invoice_id=invoice_id)


def payment_list(request):
    business = Business.objects.first()

    date_filter = request.GET.get("date")
    method_filter = request.GET.get("method")

    payments = ReceptionPayment.objects.filter(business=business).select_related("invoice", "processed_by")

    if date_filter:
        payments = payments.filter(created_at__date=date_filter)

    if method_filter:
        payments = payments.filter(payment_method=method_filter)

    payments = payments.order_by("-created_at")

    all_payment_methods = ReceptionPayment.PAYMENT_METHOD_CHOICES
    used_payment_methods = payments.values_list("payment_method", flat=True).distinct()
    payment_methods = [choice for choice in all_payment_methods if choice[0] in used_payment_methods or not method_filter]

    context = {
        "payments": payments,
        "payment_methods": payment_methods,
        "date_filter": date_filter,
        "method_filter": method_filter,
    }
    return render(request, "restaurant/payment_list.html", context)


def daily_payment_report(request):
    business = Business.objects.first()
    today = date.today()

    if business:
        all_cash_payments = ReceptionPayment.objects.filter(
            business=business,
            payment_method="CASH",
            payment_status="COMPLETED"
        )
        cash_total = all_cash_payments.aggregate(total=Sum("amount"))["total"] or 0

        all_qr_payments = ReceptionPayment.objects.filter(
            business=business,
            payment_method="QR",
            payment_status="COMPLETED"
        )
        qr_total = all_qr_payments.aggregate(total=Sum("amount"))["total"] or 0

        today_other_payments = ReceptionPayment.objects.filter(
            business=business,
            payment_status="COMPLETED",
            created_at__date=today
        ).exclude(payment_method__in=["CASH", "QR"])

        other_total = today_other_payments.aggregate(total=Sum("amount"))["total"] or 0
        grand_total = cash_total + qr_total + other_total
        show_qr = qr_total > 0

        daily_revenues = []
        for days_ago in range(6, -1, -1):
            current_date = today - timedelta(days=days_ago)

            cash_daily = ReceptionPayment.objects.filter(
                business=business,
                payment_method="CASH",
                payment_status="COMPLETED",
                created_at__date=current_date
            ).aggregate(total=Sum("amount"))["total"] or 0

            khalti_daily = ReceptionPayment.objects.filter(
                business=business,
                payment_method="KHALTI",
                payment_status="COMPLETED",
                created_at__date=current_date
            ).aggregate(total=Sum("amount"))["total"] or 0

            esewa_daily = ReceptionPayment.objects.filter(
                business=business,
                payment_method="ESEWA",
                payment_status="COMPLETED",
                created_at__date=current_date
            ).aggregate(total=Sum("amount"))["total"] or 0

            qr_daily = ReceptionPayment.objects.filter(
                business=business,
                payment_method="QR",
                payment_status="COMPLETED",
                created_at__date=current_date
            ).aggregate(total=Sum("amount"))["total"] or 0

            daily_total = cash_daily + khalti_daily + esewa_daily + qr_daily

            daily_revenues.append({
                "date": current_date,
                "cash": cash_daily,
                "khalti": khalti_daily,
                "esewa": esewa_daily,
                "qr": qr_daily,
                "total": daily_total,
                "is_today": days_ago == 0,
            })
    else:
        cash_total = qr_total = other_total = grand_total = 0
        show_qr = False
        daily_revenues = []

    context = {
        "today": today,
        "cash_total": cash_total,
        "qr_total": qr_total,
        "other_total": other_total,
        "grand_total": grand_total,
        "show_qr": show_qr,
        "daily_revenues": daily_revenues,
    }
    return render(request, "restaurant/daily_payment_report.html", context)


def process_payment(request, invoice_id):
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")

        if not payment_method:
            messages.error(request, "Please select a payment method!")
            return redirect("process_payment", invoice_id=invoice.id)

        amount = _safe_money(request.POST.get("amount", 0))

        if payment_method == "CASH":
            payment = ReceptionPayment.objects.create(
                business=invoice.business,
                invoice=invoice,
                payment_method=payment_method,
                amount=amount,
                payment_status="COMPLETED",
                processed_by=request.user if request.user.is_authenticated else invoice.created_by,
                transaction_id=f"CASH-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                processed_at=timezone.now(),
            )

            total_paid = ReceptionPayment.objects.filter(
                invoice=invoice,
                payment_status="COMPLETED"
            ).aggregate(total=Sum("amount"))["total"] or 0

            if total_paid >= invoice.total_amount:
                _mark_invoice_paid(invoice)
                _award_loyalty_points(
                    invoice,
                    created_by=request.user if request.user.is_authenticated else invoice.created_by
                )
                messages.success(request, "Cash payment completed successfully! Table is now available.")
                return redirect("payment_success", payment_id=payment.id)

            messages.info(request, f"Partial payment received. Remaining: Rs. {invoice.total_amount - total_paid}")
            return redirect("guest_bill", invoice_id=invoice.id)

        elif payment_method == "ESEWA":
            return redirect("esewa_payment", invoice_id=invoice.id)

        else:
            messages.error(request, "Invalid payment method selected!")
            return redirect("process_payment", invoice_id=invoice.id)

    context = {"invoice": invoice}
    return render(request, "restaurant/process_payment.html", context)