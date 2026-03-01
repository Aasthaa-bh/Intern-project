from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
# import requests
from .models import (
    DiningTable, 
    Ingredient, 
    InventoryStockHistory,
    ReceptionInvoice,
    ReceptionPayment,
    ReceptionLoyaltyTransaction
)
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Count, Sum
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import Business
from pos.models import Order, OrderItem
from .models import Ingredient, InventoryStockHistory
from django.http import JsonResponse
from .models import DiningTable
from pos.models import Order, OrderItem, Item
from restaurant.models import KitchenOrder
from . import payment_service


KITCHEN_STATUSES = ("PENDING", "COOKING", "READY")


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

    # Last resort for local dev: any existing user in the system.
    from accounts.models import User

    return User.objects.order_by("id").first()


def _get_kitchen_status_map(request):
    data = request.session.get("kitchen_order_statuses", {})
    if isinstance(data, dict):
        return data
    return {}


def _build_stock_note(note):
    return (note or "").strip()


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
                        business=business, name__iexact=ingredient_name
                    ).first()
                    if ingredient:
                        if unit:
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
                    business=business, change_type="ADD", ingredient_id__in=ingredient_ids
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

        # get table
        table = get_object_or_404(DiningTable, table_number=table_number)

        # table status check
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


def reception_dashboard(request):
    print("DEBUG: Entered reception_dashboard view")
    """Reception Dashboard - Overview of tables, orders, payments"""
    from core.models import Business
    business = Business.objects.first()
    
    if not business:
        context = {
            'total_tables': 0,
            'occupied_tables': 0,
            'available_tables': 0,
            'today_orders': 0,
            'today_revenue': 0,
            'pending_invoices': 0,
            'pending_payments': 0,
        }
        return render(request, 'restaurant/reception_dashboard.html', context)
    
    total_tables = DiningTable.objects.filter(business=business).count()
    occupied_tables = DiningTable.objects.filter(business=business, status='OCCUPIED').count()
    available_tables = DiningTable.objects.filter(business=business, status='AVAILABLE').count()
    
    today = timezone.now().date()
    today_orders = ReceptionInvoice.objects.filter(business=business, created_at__date=today).count()
    today_revenue = ReceptionPayment.objects.filter(
        business=business,
        payment_status='COMPLETED',
        created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_invoices = ReceptionInvoice.objects.filter(business=business, status='PENDING').count()
    pending_payments = ReceptionPayment.objects.filter(business=business, payment_status='PENDING').count()
    
    # Get recent completed payments (last 5)
    recent_payments = ReceptionPayment.objects.filter(
        business=business,
        payment_status='COMPLETED'
    ).select_related('invoice').order_by('-processed_at')[:5]
    
    # Get eSewa payment summary (today)
    esewa_today = ReceptionPayment.objects.filter(
        business=business,
        payment_method='ESEWA',
        payment_status='COMPLETED',
        created_at__date=today
    ).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    esewa_today_amount = esewa_today['total'] or 0
    esewa_today_count = esewa_today['count'] or 0
    
    # Get Cash payment summary (today)
    cash_today = ReceptionPayment.objects.filter(
        business=business,
        payment_method='CASH',
        payment_status='COMPLETED',
        created_at__date=today
    ).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    cash_today_amount = cash_today['total'] or 0
    cash_today_count = cash_today['count'] or 0
    
    context = {
        'total_tables': total_tables,
        'occupied_tables': occupied_tables,
        'available_tables': available_tables,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'pending_invoices': pending_invoices,
        'pending_payments': pending_payments,
        'recent_payments': recent_payments,
        'esewa_today_amount': esewa_today_amount,
        'esewa_today_count': esewa_today_count,
        'cash_today_amount': cash_today_amount,
        'cash_today_count': cash_today_count,
    }
    return render(request, 'restaurant/reception_dashboard.html', context)


def table_check(request):
    """View all tables and their status"""
    from core.models import Business
    business = Business.objects.first()
    
    if business:
        tables = DiningTable.objects.filter(business=business).order_by('name')
        
        # Calculate table status counts dynamically
        available_count = tables.filter(status='AVAILABLE').count()
        occupied_count = tables.filter(status='OCCUPIED').count()
        reserved_count = tables.filter(status='RESERVED').count()
    else:
        tables = []
        available_count = occupied_count = reserved_count = 0
    
    context = {
        'tables': tables,
        'available_count': available_count,
        'occupied_count': occupied_count,
        'reserved_count': reserved_count
    }
    return render(request, 'restaurant/table_check.html', context)


def table_bill(request, table_id):
    """View bill for a specific table"""
    table = get_object_or_404(DiningTable, id=table_id)
    invoice = ReceptionInvoice.objects.filter(table=table, status='PENDING').order_by('-created_at').first()
    
    # Get last completed invoice for this table (for reference)
    last_completed = ReceptionInvoice.objects.filter(table=table, status='PAID').order_by('-created_at').first()
    
    # Auto-update table status to RESERVED if there's a pending invoice
    if invoice and table.status == 'AVAILABLE':
        table.status = 'RESERVED'
        table.save()
    
    context = {
        'table': table,
        'invoice': invoice,
        'last_completed': last_completed,
    }
    return render(request, 'restaurant/table_bill.html', context)


def guest_bill(request, invoice_id):
    """View guest bill for an invoice"""
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    payments = ReceptionPayment.objects.filter(invoice=invoice)
    
    context = {
        'invoice': invoice,
        'payments': payments,
    }
    return render(request, 'restaurant/guest_bill.html', context)


def payment_success(request, payment_id):
    """Display payment success page"""
    payment = get_object_or_404(ReceptionPayment, id=payment_id)
    invoice = payment.invoice
    
    context = {
        'payment': payment,
        'invoice': invoice,
    }
    return render(request, 'restaurant/payment_success.html', context)


def process_payment(request, invoice_id):
    """Process payment for an invoice"""
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        # Debug: Print what we received
        print(f"DEBUG: payment_method = {payment_method}")
        print(f"DEBUG: POST data = {request.POST}")
        
        # Check if payment method is selected
        if not payment_method:
            messages.error(request, 'Please select a payment method!')
            return redirect('process_payment', invoice_id=invoice.id)
        
        amount = float(request.POST.get('amount', 0))
        
        print(f"DEBUG: Processing {payment_method} payment for amount {amount}")
        
        if payment_method == 'CASH':
            # Direct cash payment
            payment = ReceptionPayment.objects.create(
                business=invoice.business,
                invoice=invoice,
                payment_method=payment_method,
                amount=amount,
                payment_status='COMPLETED',
                processed_by=invoice.created_by,
                transaction_id=f"CASH-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            )
            
            total_paid = ReceptionPayment.objects.filter(
                invoice=invoice, 
                payment_status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if total_paid >= invoice.total_amount:
                invoice.status = 'PAID'
                invoice.save()
                
                # Update table status to AVAILABLE
                if invoice.table:
                    invoice.table.status = 'AVAILABLE'
                    invoice.table.save()
                
                # Add loyalty points if customer phone is available
                if invoice.customer_phone:
                    points_earned = int(invoice.total_amount / 10)  # 1 point per Rs. 10
                    ReceptionLoyaltyTransaction.objects.create(
                        business=invoice.business,
                        invoice=invoice,
                        customer_phone=invoice.customer_phone,
                        customer_name=invoice.customer_name or 'Customer',
                        transaction_type='EARN',
                        points=points_earned,
                        balance_after=0,  # Will be calculated in template
                        description=f'Points earned from invoice {invoice.invoice_number}',
                        created_by=request.user if request.user.is_authenticated else invoice.created_by
                    )
                
                messages.success(request, 'Cash payment completed successfully! Table is now available.')
                return redirect('payment_success', payment_id=payment.id)
            else:
                messages.info(request, f'Partial payment received. Remaining: Rs. {invoice.total_amount - total_paid}')
            
            return redirect('guest_bill', invoice_id=invoice.id)
            
        elif payment_method == 'ESEWA':
            return redirect('esewa_payment', invoice_id=invoice.id)
            
        else:
            messages.error(request, 'Invalid payment method selected!')
            return redirect('process_payment', invoice_id=invoice.id)
    
    context = {'invoice': invoice}
    return render(request, 'restaurant/process_payment.html', context)





def esewa_payment(request, invoice_id):
    """Initiate eSewa payment"""
    from .esewa_utils import prepare_esewa_payment_data
    
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)

    # Check if invoice is already paid
    if invoice.status == 'PAID':
        messages.error(request, 'This invoice is already paid!')
        return redirect('guest_bill', invoice_id=invoice.id)

    # Prepare eSewa payment data
    success_url = request.build_absolute_uri(f"/reception/esewa/success/")
    failure_url = request.build_absolute_uri(f"/reception/esewa/failure/")
    
    payment_data, transaction_uuid = prepare_esewa_payment_data(invoice, success_url, failure_url)
    
    # Save transaction UUID to invoice for verification
    invoice.transaction_uuid = transaction_uuid
    invoice.save()
    
    # Create pending payment record
    ReceptionPayment.objects.create(
        business=invoice.business,
        invoice=invoice,
        payment_method='ESEWA',
        amount=invoice.total_amount,
        payment_status='PENDING',
        processed_by=invoice.created_by,
        transaction_uuid=transaction_uuid,
        note=f"eSewa payment initiated - UUID: {transaction_uuid}"
    )
    
    context = {
        'invoice': invoice,
        'payment_data': payment_data,
    }
    return render(request, 'restaurant/esewa_payment.html', context)


@csrf_exempt
def esewa_success(request):
    """Handle eSewa payment success callback"""
    from .esewa_utils import verify_esewa_payment
    
    print(f"DEBUG: eSewa success callback received")
    print(f"DEBUG: GET params: {request.GET}")
    print(f"DEBUG: POST params: {request.POST}")
    
    # eSewa sends data in GET parameters
    transaction_uuid = request.GET.get('transaction_uuid')
    transaction_code = request.GET.get('transaction_code')
    total_amount = request.GET.get('total_amount')
    
    print(f"DEBUG: transaction_uuid={transaction_uuid}, transaction_code={transaction_code}")
    
    if not transaction_uuid:
        messages.error(request, 'Invalid payment response - missing transaction UUID!')
        return redirect('reception_dashboard')
    
    # Find invoice by transaction UUID
    try:
        invoice = ReceptionInvoice.objects.get(transaction_uuid=transaction_uuid)
        print(f"DEBUG: Found invoice: {invoice.invoice_number}")
    except ReceptionInvoice.DoesNotExist:
        print(f"DEBUG: Invoice not found for UUID: {transaction_uuid}")
        messages.error(request, 'Invoice not found!')
        return redirect('reception_dashboard')
    
    # Check if already paid
    if invoice.status == 'PAID':
        messages.info(request, 'This invoice is already paid!')
        payment = ReceptionPayment.objects.filter(
            invoice=invoice,
            payment_status='COMPLETED'
        ).first()
        if payment:
            return redirect('payment_success', payment_id=payment.id)
        return redirect('guest_bill', invoice_id=invoice.id)
    
    # Verify payment with eSewa
    print(f"DEBUG: Verifying payment with eSewa...")
    verification = verify_esewa_payment(transaction_uuid)
    
    print(f"DEBUG: Verification result: {verification}")
    
    if verification['success'] and verification.get('status') == 'COMPLETE':
        # Update payment status
        payment = ReceptionPayment.objects.filter(
            invoice=invoice,
            transaction_uuid=transaction_uuid,
            payment_status='PENDING'
        ).first()
        
        if payment:
            payment.payment_status = 'COMPLETED'
            payment.transaction_id = verification.get('ref_id', transaction_code)
            payment.note = f"eSewa payment verified - Ref: {verification.get('ref_id', transaction_code)}"
            payment.save()
            print(f"DEBUG: Payment updated to COMPLETED")
            
            # Update invoice status
            invoice.status = 'PAID'
            invoice.save()
            print(f"DEBUG: Invoice marked as PAID")
            
            # Update table status to AVAILABLE
            if invoice.table:
                invoice.table.status = 'AVAILABLE'
                invoice.table.save()
                print(f"DEBUG: Table {invoice.table.table_number} set to AVAILABLE")
            
            # Add loyalty points
            if invoice.customer_phone:
                points_earned = int(invoice.total_amount / 10)
                ReceptionLoyaltyTransaction.objects.create(
                    business=invoice.business,
                    invoice=invoice,
                    customer_phone=invoice.customer_phone,
                    customer_name=invoice.customer_name or 'Customer',
                    transaction_type='EARN',
                    points=points_earned,
                    balance_after=0,
                    description=f'Points earned from invoice {invoice.invoice_number}',
                    created_by=invoice.created_by
                )
                print(f"DEBUG: Loyalty points added: {points_earned}")
            
            messages.success(request, 'Payment completed successfully!')
            return redirect('payment_success', payment_id=payment.id)
        else:
            print(f"DEBUG: No pending payment found for this transaction")
            messages.error(request, 'Payment record not found!')
            return redirect('guest_bill', invoice_id=invoice.id)
    
    # Payment verification failed
    error_msg = verification.get('message', 'Payment verification failed!')
    print(f"DEBUG: Verification failed: {error_msg}")
    messages.error(request, f'Payment verification failed: {error_msg}')
    return redirect('process_payment', invoice_id=invoice.id)


@csrf_exempt
def esewa_failure(request):
    """Handle eSewa payment failure callback"""
    print(f"DEBUG: eSewa failure callback received")
    print(f"DEBUG: GET params: {request.GET}")
    print(f"DEBUG: POST params: {request.POST}")
    
    transaction_uuid = request.GET.get('transaction_uuid')
    
    # Try to find and update the payment record
    if transaction_uuid:
        try:
            invoice = ReceptionInvoice.objects.get(transaction_uuid=transaction_uuid)
            payment = ReceptionPayment.objects.filter(
                invoice=invoice,
                transaction_uuid=transaction_uuid,
                payment_status='PENDING'
            ).first()
            
            if payment:
                payment.payment_status = 'FAILED'
                payment.note = 'Payment cancelled or failed by user'
                payment.save()
                print(f"DEBUG: Payment marked as FAILED")
            
            messages.error(request, 'Payment was cancelled or failed. Please try again.')
            return redirect('process_payment', invoice_id=invoice.id)
        except ReceptionInvoice.DoesNotExist:
            pass
    
    messages.error(request, 'Payment was cancelled or failed. Please try again.')
    return redirect('reception_dashboard')


def partial_payment(request, invoice_id):
    """Handle partial payment (Aadha party)"""
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        payment_method = request.POST.get('payment_method')
        
        if amount > 0 and amount <= invoice.total_amount:
            ReceptionPayment.objects.create(
                business=invoice.business,
                invoice=invoice,
                payment_method=payment_method,
                amount=amount,
                payment_status='COMPLETED',
                processed_by=invoice.created_by,
                transaction_id=f"PARTIAL-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            )
            messages.success(request, f'Partial payment of Rs. {amount} received!')
            return redirect('guest_bill', invoice_id=invoice.id)
    
    context = {'invoice': invoice}
    return render(request, 'restaurant/partial_payment.html', context)


def split_bill(request, invoice_id):
    """Split bill among multiple people (Ko bill aadha)"""
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    
    if request.method == 'POST':
        split_count = int(request.POST.get('split_count', 1))
        split_amount = invoice.total_amount / split_count
        
        context = {
            'invoice': invoice,
            'split_count': split_count,
            'split_amount': split_amount,
        }
        return render(request, 'restaurant/split_bill.html', context)
    
    context = {'invoice': invoice}
    return render(request, 'restaurant/split_bill.html', context)


def loyalty_points_check(request):
    """Check customer loyalty points"""
    if request.method == 'POST':
        phone = request.POST.get('phone')
        from core.models import Business
        business = Business.objects.first()
        
        if business:
            transactions = ReceptionLoyaltyTransaction.objects.filter(
                business=business,
                customer_phone=phone
            ).order_by('-created_at')[:10]
            
            total_earned = ReceptionLoyaltyTransaction.objects.filter(
                business=business,
                customer_phone=phone,
                transaction_type='EARN'
            ).aggregate(total=Sum('points'))['total'] or 0
            
            total_redeemed = ReceptionLoyaltyTransaction.objects.filter(
                business=business,
                customer_phone=phone,
                transaction_type='REDEEM'
            ).aggregate(total=Sum('points'))['total'] or 0
            
            current_balance = total_earned - total_redeemed
            
            if transactions.exists():
                context = {
                    'customer_phone': phone,
                    'customer_name': transactions.first().customer_name,
                    'current_balance': current_balance,
                    'transactions': transactions,
                }
                return render(request, 'restaurant/loyalty_points_check.html', context)
            else:
                messages.error(request, 'No loyalty transactions found for this customer!')
    
    return render(request, 'restaurant/loyalty_points_check.html')


def payment_history(request):
    """View payment history"""
    from core.models import Business
    business = Business.objects.first()
    
    if business:
        # Only show COMPLETED payments, not pending ones
        payments = ReceptionPayment.objects.filter(
            business=business,
            payment_status='COMPLETED'
        ).select_related(
            'invoice', 'processed_by'
        ).order_by('-processed_at')[:50]
        
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if date_from:
            payments = payments.filter(processed_at__date__gte=date_from)
        if date_to:
            payments = payments.filter(processed_at__date__lte=date_to)
    else:
        payments = []
    
    context = {'payments': payments}
    return render(request, 'restaurant/payment_history.html', context)


def update_table_status(request, table_id):
    """Update table status (Available/Occupied/Reserved)"""
    table = get_object_or_404(DiningTable, id=table_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['AVAILABLE', 'OCCUPIED', 'RESERVED']:
            table.status = new_status
            table.save()
            messages.success(request, f'Table {table.table_number} status updated!')
        return redirect('table_check')
    
    context = {'table': table}
    return render(request, 'restaurant/update_table_status.html', context)


def toggle_table_status(request, table_id):
    """Toggle table status between AVAILABLE and OCCUPIED"""
    table = get_object_or_404(DiningTable, id=table_id)
    
    if request.method == 'POST':
        # Toggle status
        if table.status == 'OCCUPIED':
            table.status = 'AVAILABLE'
            messages.success(request, f'Table {table.table_number} is now AVAILABLE')
        else:
            table.status = 'OCCUPIED'
            messages.success(request, f'Table {table.table_number} is now OCCUPIED')
        
        table.save()
    
    return redirect('table_bill', table_id=table.id)


def bulk_update_tables(request):
    """Bulk update table status"""
    if request.method == 'POST':
        table_ids = request.POST.getlist('table_ids')
        status = request.POST.get('status')
        
        if status in ['AVAILABLE', 'OCCUPIED', 'RESERVED']:
            tables = DiningTable.objects.filter(id__in=table_ids)
            count = tables.update(status=status)
            messages.success(request, f'{count} table(s) updated to {status}')
        
    return redirect('table_check')


def quick_status_change(request, table_id):
    """Quick status change from table list"""
    if request.method == 'POST':
        table = get_object_or_404(DiningTable, id=table_id)
        status = request.POST.get('status')
        
        if status in ['AVAILABLE', 'OCCUPIED', 'RESERVED']:
            table.status = status
            table.save()
            messages.success(request, f'Table {table.table_number} is now {status}')
    
    return redirect('table_check')


def bulk_update_all_tables(request):
    """Update all tables to same status"""
    if request.method == 'POST':
        status = request.POST.get('status')
        
        if status in ['AVAILABLE', 'OCCUPIED', 'RESERVED']:
            from core.models import Business
            business = Business.objects.first()
            
            if business:
                count = DiningTable.objects.filter(business=business).update(status=status)
                messages.success(request, f'All {count} tables updated to {status}')
            else:
                messages.error(request, 'No business found')
    
    return redirect('table_check')



def create_invoice(request, table_id):
    """Create new invoice for a table"""
    from accounts.models import User

    table = get_object_or_404(DiningTable, id=table_id)

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', 'Guest')
        customer_phone = request.POST.get('customer_phone', '')
        subtotal = float(request.POST.get('subtotal', 0))

        # Calculate tax (13% VAT)
        tax_amount = subtotal * 0.13
        discount = float(request.POST.get('discount', 0))
        total = subtotal + tax_amount - discount

        # Generate invoice number
        import random
        invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        # Get user for created_by field
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        # Create invoice
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
            status='PENDING',
            created_by=user
        )

        # Update table status
        table.status = 'OCCUPIED'
        table.save()

        messages.success(request, f'Invoice {invoice_number} created successfully!')
        return redirect('table_bill', table_id=table.id)

    context = {'table': table}
    return render(request, 'restaurant/create_invoice.html', context)




def pending_invoices(request):
    """View all pending invoices"""
    from core.models import Business
    business = Business.objects.first()
    
    if business:
        invoices = ReceptionInvoice.objects.filter(
            business=business,
            status='PENDING'
        ).select_related('table', 'created_by').order_by('-created_at')
    else:
        invoices = []
    
    context = {'invoices': invoices}
    return render(request, 'restaurant/pending_invoices.html', context)


def verify_payment(request, payment_id):
    """Verify a pending payment manually"""
    payment = get_object_or_404(ReceptionPayment, id=payment_id)
    
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id', '').strip()
        
        from accounts.models import User
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        
        result = payment_service.verify_payment(payment_id, transaction_id, user)
        
        if result['success']:
            msg = 'Payment verified successfully!'
            if result['invoice_paid']:
                msg += ' Invoice marked as PAID.'
            if result['table_freed']:
                msg += ' Table is now AVAILABLE.'
            messages.success(request, msg)
            return redirect('guest_bill', invoice_id=payment.invoice.id)
        else:
            messages.error(request, result['message'])
    
    context = {'payment': payment}
    return render(request, 'restaurant/verify_payment.html', context)


def pending_payments_list(request):
    """View all pending payments"""
    from core.models import Business
    business = Business.objects.first()
    
    if business:
        payments = payment_service.get_pending_payments(business)
        
        # Calculate elapsed time for each payment
        now = timezone.now()
        payments_with_time = []
        for payment in payments:
            elapsed = now - payment.processed_at
            elapsed_minutes = int(elapsed.total_seconds() / 60)
            payments_with_time.append({
                'payment': payment,
                'elapsed_minutes': elapsed_minutes,
                'highlight': elapsed_minutes > 10
            })
        
        context = {'payments_data': payments_with_time}
    else:
        context = {'payments_data': []}
    
    return render(request, 'restaurant/pending_payments_list.html', context)


def qr_payment(request, invoice_id):
    """Display QR payment page with invoice details"""
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    
    # Safety check: don't allow QR payment for already paid invoices
    if invoice.status == 'PAID':
        messages.error(request, 'This invoice is already paid!')
        return redirect('guest_bill', invoice_id=invoice_id)
    
    context = {
        'invoice': invoice,
        'qr_code_url': '/static/images/qr-code.png',  # You can update this with your actual QR code
    }
    return render(request, 'restaurant/qr_payment.html', context)


def confirm_qr_payment(request, invoice_id):
    """Confirm QR payment with reference code"""
    if request.method != 'POST':
        return redirect('qr_payment', invoice_id=invoice_id)
    
    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id)
    payer_ref_code = request.POST.get('payer_ref_code', '').strip()
    
    # Safety validations
    if invoice.status == 'PAID':
        messages.error(request, 'This invoice is already paid!')
        return redirect('guest_bill', invoice_id=invoice_id)
    
    if not payer_ref_code:
        messages.error(request, 'Transaction/Reference code is required!')
        return redirect('qr_payment', invoice_id=invoice_id)
    
    # Check if payment with this reference code already exists
    existing_payment = ReceptionPayment.objects.filter(
        invoice=invoice,
        payer_ref_code=payer_ref_code,
        payment_status='COMPLETED'
    ).first()
    
    if existing_payment:
        messages.error(request, 'Payment with this reference code has already been processed!')
        return redirect('guest_bill', invoice_id=invoice_id)
    
    from core.models import Business
    business = Business.objects.first()
    
    # Create the payment record
    payment = ReceptionPayment.objects.create(
        business=business,
        invoice=invoice,
        payment_method='QR',
        amount=invoice.total_amount,
        payer_ref_code=payer_ref_code,
        payment_status='COMPLETED',
        note=f'QR payment confirmed with reference: {payer_ref_code}',
        processed_by=request.user if request.user.is_authenticated else None
    )
    
    # Update invoice status
    invoice.status = 'PAID'
    invoice.save()
    
    messages.success(request, f'Payment of Rs. {invoice.total_amount} confirmed successfully!')
    return redirect('guest_bill', invoice_id=invoice_id)


def payment_list(request):
    """View all payments with filtering options"""
    from core.models import Business
    business = Business.objects.first()
    
    date_filter = request.GET.get('date')
    method_filter = request.GET.get('method')
    
    payments = ReceptionPayment.objects.filter(business=business).select_related('invoice', 'processed_by')
    
    if date_filter:
        payments = payments.filter(created_at__date=date_filter)
    
    if method_filter:
        payments = payments.filter(payment_method=method_filter)
    
    payments = payments.order_by('-created_at')
    
    # Get payment methods for filter dropdown (only show methods that have payments)
    all_payment_methods = ReceptionPayment.PAYMENT_METHOD_CHOICES
    used_payment_methods = payments.values_list('payment_method', flat=True).distinct()
    payment_methods = [choice for choice in all_payment_methods if choice[0] in used_payment_methods or not method_filter]
    
    context = {
        'payments': payments,
        'payment_methods': payment_methods,
        'date_filter': date_filter,
        'method_filter': method_filter,
    }
    return render(request, 'restaurant/payment_list.html', context)


def daily_payment_report(request):
    """Payment report showing totals by payment method"""
    from core.models import Business
    from django.db.models import Sum
    from datetime import date, timedelta
    
    business = Business.objects.first()
    today = date.today()
    
    if business:
        # All-time cash payments (completed)
        all_cash_payments = ReceptionPayment.objects.filter(
            business=business,
            payment_method='CASH',
            payment_status='COMPLETED'
        )
        cash_total = all_cash_payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # All-time QR payments (completed)
        all_qr_payments = ReceptionPayment.objects.filter(
            business=business,
            payment_method='QR',
            payment_status='COMPLETED'
        )
        qr_total = all_qr_payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Today's other payments (excluding CASH and QR)
        today_other_payments = ReceptionPayment.objects.filter(
            business=business,
            payment_status='COMPLETED',
            created_at__date=today
        ).exclude(payment_method__in=['CASH', 'QR'])
        other_total = today_other_payments.aggregate(total=Sum('amount'))['total'] or 0
        
        grand_total = cash_total + qr_total + other_total
        
        # Check if QR payments exist to show QR card
        show_qr = qr_total > 0
        
        # Daily revenue changes (last 7 days)
        daily_revenues = []
        for days_ago in range(6, -1, -1):
            current_date = today - timedelta(days=days_ago)
            
            cash_daily = ReceptionPayment.objects.filter(
                business=business,
                payment_method='CASH',
                payment_status='COMPLETED',
                created_at__date=current_date
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            khalti_daily = ReceptionPayment.objects.filter(
                business=business,
                payment_method='KHALTI',
                payment_status='COMPLETED',
                created_at__date=current_date
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            daily_total = cash_daily + khalti_daily
            
            daily_revenues.append({
                'date': current_date,
                'cash': cash_daily,
                'khalti': khalti_daily,
                'total': daily_total,
                'is_today': days_ago == 0
            })
    else:
        cash_total = qr_total = other_total = grand_total = 0
        show_qr = False
        daily_revenues = []
    
    context = {
        'today': today,
        'cash_total': cash_total,
        'qr_total': qr_total,
        'other_total': other_total,
        'grand_total': grand_total,
        'show_qr': show_qr,
        'daily_revenues': daily_revenues,
    }
    return render(request, 'restaurant/daily_payment_report.html', context)
