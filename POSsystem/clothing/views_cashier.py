from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone
from decimal import Decimal
import json

from pos.models import Order, OrderItem, Item, ItemVariant
from pos.inventory_services import create_stock_movement
from restaurant.models import ReceptionInvoice, ReceptionPayment
from core.models import Business
from .models import (
    CashierCustomer,
    CashierPromoCode,
    CashierLoyaltyTransaction,
    ClothingVariantDetail
)


@login_required
def cashier_dashboard(request):
    """Cashier dashboard with today's sales summary"""
    business = _get_cashier_business(request)
    if not business:
        return redirect('accounts:login')

    today = timezone.now().date()
    today_start = timezone.datetime.combine(today, timezone.datetime.min.time())
    today_end = timezone.datetime.combine(today, timezone.datetime.max.time())

    # Today's sales data
    today_invoices = ReceptionInvoice.objects.filter(
        business=business,
        created_at__range=(today_start, today_end)
    )

    today_sales = today_invoices.aggregate(
        total_sales=Sum('total_amount'),
        total_bills=Sum('id'),  # Count of invoices
    )

    # Total items sold today
    today_items = OrderItem.objects.filter(
        order__business=business,
        order__created_at__range=(today_start, today_end)
    ).aggregate(total_items=Sum('quantity'))['total_items'] or 0

    # Customers served today
    customers_served = today_invoices.values('customer_name').distinct().count()

    # Recent transactions
    recent_transactions = today_invoices.order_by('-created_at')[:10]

    context = {
        'today_sales': today_sales['total_sales'] or 0,
        'total_bills': today_invoices.count(),
        'total_items_sold': today_items,
        'customers_served': customers_served,
        'recent_transactions': recent_transactions,
    }

    return render(request, 'clothing/cashier/dashboard.html', context)


@login_required
def pos_new_sale(request):
    """Main POS screen for new sales"""
    business = _get_cashier_business(request)
    if not business:
        return redirect('accounts:login')

    # Create a new order for this session
    order = Order.objects.create(
        business=business,
        created_by=request.user,
        status='PENDING'
    )

    # Get categories for filtering
    categories = Item.objects.filter(
        business=business,
        is_active=True
    ).values_list('category__name', flat=True).distinct()

    context = {
        'order': order,
        'categories': categories,
    }

    return render(request, 'clothing/cashier/pos.html', context)


@login_required
def search_products(request):
    """AJAX endpoint for product search"""
    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if not query and not category:
        return JsonResponse({'products': []})

    # Build search query
    search_filter = Q(business=business, is_active=True)

    if query:
        search_filter &= (
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(barcode__icontains=query)
        )

    if category:
        search_filter &= Q(category__name__icontains=category)

    items = Item.objects.filter(search_filter)[:50]

    products = []
    for item in items:
        # Get variants with stock
        variants = item.variants.filter(
            is_active=True,
            stock_qty__gt=0
        ).select_related('clothing_detail__size', 'clothing_detail__color')

        product_data = {
            'id': item.id,
            'name': item.name,
            'sku': item.sku or '',
            'barcode': item.barcode or '',
            'price': str(item.price),
            'category': item.category.name if item.category else '',
            'image': item.image.url if item.image else '',
            'has_variants': variants.exists(),
            'variants': []
        }

        if variants.exists():
            for variant in variants:
                detail = getattr(variant, 'clothing_detail', None)
                variant_name = variant.name
                if detail:
                    parts = []
                    if detail.size:
                        parts.append(detail.size.name)
                    if detail.color:
                        parts.append(detail.color.name)
                    if parts:
                        variant_name = f"{variant.name} ({', '.join(parts)})"

                product_data['variants'].append({
                    'id': variant.id,
                    'name': variant_name,
                    'sku': variant.sku or '',
                    'barcode': variant.barcode or '',
                    'price': str(variant.price or item.price),
                    'stock_qty': variant.stock_qty or 0,
                    'size': detail.size.name if detail and detail.size else '',
                    'color': detail.color.name if detail and detail.color else '',
                })
        else:
            # No variants, use main item
            product_data['stock_qty'] = item.stock_qty or 0

        products.append(product_data)

    return JsonResponse({'products': products})


@login_required
def add_to_cart(request):
    """Add item to cart"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        item_id = data.get('item_id')
        variant_id = data.get('variant_id')
        quantity = int(data.get('quantity', 1))

        order = get_object_or_404(Order, id=order_id, business=business, status='PENDING')

        # Get item and variant
        item = get_object_or_404(Item, id=item_id, business=business)

        if variant_id:
            variant = get_object_or_404(ItemVariant, id=variant_id, item=item)
            stock_qty = variant.stock_qty or 0
            price = variant.price or item.price
            item_name = variant.name
        else:
            variant = None
            stock_qty = item.stock_qty or 0
            price = item.price
            item_name = item.name

        # Check stock
        if quantity > stock_qty:
            return JsonResponse({'error': f'Insufficient stock. Available: {stock_qty}'}, status=400)

        # Check if item already in cart
        cart_item = OrderItem.objects.filter(
            order=order,
            item=item,
            variant=variant
        ).first()

        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > stock_qty:
                return JsonResponse({'error': f'Insufficient stock. Available: {stock_qty}'}, status=400)
            cart_item.quantity = new_quantity
            cart_item.save()
        else:
            OrderItem.objects.create(
                order=order,
                item=item,
                variant=variant,
                quantity=quantity,
                unit_price=price,
                line_total=price * quantity
            )

        # Update order total
        _update_order_totals(order)

        return JsonResponse({
            'success': True,
            'message': f'Added {quantity} x {item_name} to cart'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def update_cart_item(request):
    """Update cart item quantity"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        order_item_id = data.get('order_item_id')
        quantity = int(data.get('quantity', 1))

        order_item = get_object_or_404(OrderItem, id=order_item_id, order__business=business)

        if quantity <= 0:
            order_item.delete()
        else:
            # Check stock
            stock_qty = order_item.variant.stock_qty if order_item.variant else order_item.item.stock_qty
            stock_qty = stock_qty or 0

            if quantity > stock_qty:
                return JsonResponse({'error': f'Insufficient stock. Available: {stock_qty}'}, status=400)

            order_item.quantity = quantity
            order_item.line_total = order_item.unit_price * quantity
            order_item.save()

        # Update order total
        _update_order_totals(order_item.order)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def remove_cart_item(request):
    """Remove item from cart"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        order_item_id = data.get('order_item_id')

        order_item = get_object_or_404(OrderItem, id=order_item_id, order__business=business)
        order_item.delete()

        # Update order total
        _update_order_totals(order_item.order)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_cart(request, order_id):
    """Get cart items for an order"""
    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    order = get_object_or_404(Order, id=order_id, business=business, status='PENDING')

    cart_items = []
    for item in order.order_items.all():
        cart_items.append({
            'id': item.id,
            'item_name': item.variant.name if item.variant else item.item.name,
            'quantity': item.quantity,
            'unit_price': str(item.unit_price),
            'line_total': str(item.line_total),
            'variant_info': _get_variant_info(item.variant) if item.variant else None
        })

    totals = _calculate_order_totals(order)

    return JsonResponse({
        'cart_items': cart_items,
        'totals': totals
    })


@login_required
def apply_promo_code(request):
    """Apply promo code to order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        promo_code = data.get('promo_code', '').strip().upper()

        order = get_object_or_404(Order, id=order_id, business=business, status='PENDING')

        # Find promo code
        promo = CashierPromoCode.objects.filter(
            business=business,
            code=promo_code
        ).first()

        if not promo:
            return JsonResponse({'error': 'Invalid promo code'}, status=400)

        # Calculate current subtotal
        subtotal = sum(item.line_total for item in order.order_items.all())

        if not promo.can_apply(subtotal):
            return JsonResponse({'error': 'Promo code cannot be applied'}, status=400)

        # Store promo code in session for this order
        request.session[f'promo_{order_id}'] = {
            'code': promo.code,
            'discount': str(promo.apply_discount(subtotal))
        }

        return JsonResponse({
            'success': True,
            'message': f'Promo code {promo.code} applied',
            'discount': str(promo.apply_discount(subtotal))
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def apply_loyalty_points(request):
    """Apply loyalty points discount"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        customer_phone = data.get('customer_phone', '').strip()
        points = int(data.get('points', 0))

        order = get_object_or_404(Order, id=order_id, business=business, status='PENDING')

        # Find customer
        customer = CashierCustomer.objects.filter(
            business=business,
            phone=customer_phone
        ).first()

        if not customer:
            return JsonResponse({'error': 'Customer not found'}, status=400)

        if points > customer.loyalty_points:
            return JsonResponse({'error': f'Insufficient points. Available: {customer.loyalty_points}'}, status=400)

        # Calculate discount
        discount = customer.redeem_loyalty_points(points)

        # Store loyalty discount in session
        request.session[f'loyalty_{order_id}'] = {
            'customer_id': customer.id,
            'points': points,
            'discount': str(discount)
        }

        return JsonResponse({
            'success': True,
            'message': f'{points} points redeemed for Rs. {discount}',
            'discount': str(discount)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def select_customer(request):
    """Select customer for order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        customer_phone = data.get('customer_phone', '').strip()

        order = get_object_or_404(Order, id=order_id, business=business, status='PENDING')

        # Find or create customer
        customer, created = CashierCustomer.objects.get_or_create(
            business=business,
            phone=customer_phone,
            defaults={'name': f'Customer {customer_phone}'}
        )

        # Store customer in session
        request.session[f'customer_{order_id}'] = {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'loyalty_points': customer.loyalty_points
        }

        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'loyalty_points': customer.loyalty_points,
                'total_purchases': str(customer.total_purchases)
            },
            'created': created
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def complete_sale(request):
    """Complete the sale and create invoice"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        with transaction.atomic():
            data = json.loads(request.body)
            order_id = data.get('order_id')
            payment_method = data.get('payment_method')
            cash_received = Decimal(data.get('cash_received', '0'))

            order = get_object_or_404(Order, id=order_id, business=business, status='PENDING')

            # Calculate totals
            totals = _calculate_order_totals(order, request.session)

            if not order.order_items.exists():
                return JsonResponse({'error': 'Cart is empty'}, status=400)

            # Create invoice
            invoice = ReceptionInvoice.objects.create(
                business=business,
                invoice_number=_generate_invoice_number(),
                customer_name=request.session.get(f'customer_{order_id}', {}).get('name', 'Walk-in Customer'),
                customer_phone=request.session.get(f'customer_{order_id}', {}).get('phone', ''),
                total_amount=totals['total_amount'],
                discount_amount=totals['total_discount'],
                tax_amount=totals['vat_amount'],
                created_by=request.user
            )

            # Create payment
            payment = ReceptionPayment.objects.create(
                invoice=invoice,
                amount=totals['total_amount'],
                payment_method=payment_method,
                cash_received=cash_received if payment_method == 'CASH' else totals['total_amount'],
                change_amount=cash_received - totals['total_amount'] if payment_method == 'CASH' else 0,
                created_by=request.user
            )

            # Update order status
            order.status = 'COMPLETED'
            order.invoice = invoice
            order.save()

            # Update inventory
            for order_item in order.order_items.all():
                item = order_item.variant or order_item.item
                create_stock_movement(
                    item=item,
                    quantity=-order_item.quantity,
                    movement_type='SALE',
                    reference=f'Invoice #{invoice.invoice_number}',
                    created_by=request.user
                )

            # Handle loyalty points
            customer_data = request.session.get(f'customer_{order_id}')
            if customer_data:
                customer = CashierCustomer.objects.get(id=customer_data['id'])

                # Add earned points
                earned_points = int(totals['subtotal'] // 100)
                if earned_points > 0:
                    customer.add_loyalty_points(totals['subtotal'])
                    CashierLoyaltyTransaction.objects.create(
                        customer=customer,
                        transaction_type='EARNED',
                        points=earned_points,
                        amount=totals['subtotal'],
                        invoice_number=invoice.invoice_number
                    )

                # Record redeemed points
                loyalty_data = request.session.get(f'loyalty_{order_id}')
                if loyalty_data:
                    CashierLoyaltyTransaction.objects.create(
                        customer=customer,
                        transaction_type='REDEEMED',
                        points=loyalty_data['points'],
                        amount=Decimal(loyalty_data['discount']),
                        invoice_number=invoice.invoice_number
                    )

                # Update customer purchase history
                customer.total_purchases += totals['total_amount']
                customer.last_purchase_date = timezone.now()
                customer.save()

            # Mark promo code as used
            promo_data = request.session.get(f'promo_{order_id}')
            if promo_data:
                promo = CashierPromoCode.objects.filter(code=promo_data['code']).first()
                if promo:
                    promo.mark_used()

            # Clear session data
            for key in list(request.session.keys()):
                if key.startswith(f'customer_{order_id}') or key.startswith(f'promo_{order_id}') or key.startswith(f'loyalty_{order_id}'):
                    del request.session[key]

            return JsonResponse({
                'success': True,
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'receipt_url': f'/clothing/cashier/receipt/{invoice.id}/'
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def sales_history(request):
    """View sales history"""
    business = _get_cashier_business(request)
    if not business:
        return redirect('accounts:login')

    # Get filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    customer_phone = request.GET.get('customer_phone', '').strip()
    payment_method = request.GET.get('payment_method')
    status = request.GET.get('status')

    # Base queryset
    invoices = ReceptionInvoice.objects.filter(business=business)

    # Apply filters
    if date_from:
        invoices = invoices.filter(created_at__date__gte=date_from)
    if date_to:
        invoices = invoices.filter(created_at__date__lte=date_to)
    if customer_phone:
        invoices = invoices.filter(customer_phone__icontains=customer_phone)
    if payment_method:
        invoices = invoices.filter(payments__payment_method=payment_method.upper())
    if status:
        invoices = invoices.filter(status=status)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(invoices.order_by('-created_at'), 25)
    page_number = request.GET.get('page')
    sales = paginator.get_page(page_number)

    # Calculate stats
    total_sales = invoices.count()
    total_amount = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_items = sum(invoice.order.order_items.aggregate(Sum('quantity'))['quantity__sum'] or 0
                     for invoice in invoices if hasattr(invoice, 'order') and invoice.order)

    context = {
        'sales': sales,
        'date_from': date_from,
        'date_to': date_to,
        'customer_phone': customer_phone,
        'payment_method': payment_method,
        'status': status,
        'total_sales': total_sales,
        'total_amount': total_amount,
        'total_items': total_items,
    }

    return render(request, 'clothing/cashier/sales_history.html', context)


@login_required
def customers(request):
    """Manage customers"""
    business = _get_cashier_business(request)
    if not business:
        return redirect('accounts:login')

    customers_list = CashierCustomer.objects.filter(business=business).annotate(
        total_orders=Sum('loyalty_transactions__points', filter=Q(loyalty_transactions__transaction_type='EARNED')),
        total_spent=Sum('loyalty_transactions__amount', filter=Q(loyalty_transactions__transaction_type='EARNED'))
    ).order_by('-last_purchase_date')

    # Stats
    total_customers = customers_list.count()
    total_loyalty_points = customers_list.aggregate(Sum('loyalty_points'))['loyalty_points__sum'] or 0
    total_spent = customers_list.aggregate(Sum('total_purchases'))['total_purchases__sum'] or 0

    context = {
        'customers': customers_list,
        'total_customers': total_customers,
        'total_loyalty_points': total_loyalty_points,
        'total_spent': total_spent,
    }

    return render(request, 'clothing/cashier/customers.html', context)


@login_required
def receipt(request, invoice_id):
    """View sale receipt"""
    business = _get_cashier_business(request)
    if not business:
        return redirect('accounts:login')

    invoice = get_object_or_404(ReceptionInvoice, id=invoice_id, business=business)
    payment = invoice.payments.first()

    # Get order items
    order_items = []
    if hasattr(invoice, 'order') and invoice.order:
        order_items = invoice.order.order_items.all()

    # Get business info
    business_info = business

    # Calculate loyalty points earned
    loyalty_points_earned = 0
    if invoice.customer_phone:
        customer = CashierCustomer.objects.filter(
            business=business,
            phone=invoice.customer_phone
        ).first()
        if customer:
            # Find loyalty transaction for this invoice
            transaction = CashierLoyaltyTransaction.objects.filter(
                customer=customer,
                invoice_number=invoice.invoice_number,
                transaction_type='EARNED'
            ).first()
            if transaction:
                loyalty_points_earned = transaction.points

    context = {
        'invoice': invoice,
        'payment': payment,
        'order_items': order_items,
        'business': business_info,
        'loyalty_points_earned': loyalty_points_earned,
    }

    return render(request, 'clothing/cashier/receipt.html', context)


@login_required
def profile(request):
    """Cashier profile management"""
    business = _get_cashier_business(request)
    if not business:
        return redirect('accounts:login')

    # Get cashier stats
    today = timezone.now().date()
    today_start = timezone.datetime.combine(today, timezone.datetime.min.time())
    today_end = timezone.datetime.combine(today, timezone.datetime.max.time())

    cashier_stats = ReceptionInvoice.objects.filter(
        business=business,
        created_by=request.user
    ).aggregate(
        total_sales=Sum('id'),
        total_amount=Sum('total_amount'),
        today_sales=Sum('id', filter=Q(created_at__range=(today_start, today_end)))
    )

    context = {
        'cashier_stats': {
            'total_sales': cashier_stats['total_sales'] or 0,
            'total_amount': cashier_stats['total_amount'] or Decimal('0'),
            'today_sales': cashier_stats['today_sales'] or 0,
            'total_items': 0,  # Could be calculated if needed
        }
    }

    return render(request, 'clothing/cashier/profile.html', context)


@login_required
def update_customer(request):
    """Update customer information"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        customer_id = request.POST.get('customer_id')
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        loyalty_points = int(request.POST.get('loyalty_points', 0))

        customer = get_object_or_404(CashierCustomer, id=customer_id, business=business)

        # Check if phone number is already used by another customer
        if CashierCustomer.objects.filter(business=business, phone=phone).exclude(id=customer_id).exists():
            return JsonResponse({'error': 'Phone number already exists'}, status=400)

        customer.name = name
        customer.phone = phone
        customer.email = email
        customer.loyalty_points = loyalty_points
        customer.save()

        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'loyalty_points': customer.loyalty_points,
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def loyalty_history(request):
    """Get customer loyalty history"""
    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    customer_id = request.GET.get('customer_id')
    customer = get_object_or_404(CashierCustomer, id=customer_id, business=business)

    transactions = CashierLoyaltyTransaction.objects.filter(
        customer=customer
    ).order_by('-created_at')[:50]

    history = []
    for transaction in transactions:
        history.append({
            'id': transaction.id,
            'transaction_type': transaction.transaction_type,
            'points': transaction.points,
            'amount': str(transaction.amount),
            'invoice_number': transaction.invoice_number,
            'created_at': transaction.created_at.isoformat(),
            'description': transaction.get_description()
        })

    return JsonResponse({
        'success': True,
        'history': history
    })


@login_required
def sale_details(request):
    """Get sale details for modal"""
    business = _get_cashier_business(request)
    if not business:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    sale_id = request.GET.get('sale_id')
    invoice = get_object_or_404(ReceptionInvoice, id=sale_id, business=business)

    # Get order items
    items = []
    if hasattr(invoice, 'order') and invoice.order:
        for order_item in invoice.order.order_items.all():
            item_data = {
                'item_name': order_item.variant.name if order_item.variant else order_item.item.name,
                'quantity': order_item.quantity,
                'unit_price': str(order_item.unit_price),
                'line_total': str(order_item.line_total),
                'variant_info': _get_variant_info(order_item.variant) if order_item.variant else None
            }
            items.append(item_data)

    sale_data = {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'created_at': invoice.created_at.isoformat(),
        'customer': {
            'name': invoice.customer_name,
            'phone': invoice.customer_phone,
        } if invoice.customer_name else None,
        'payment_method': invoice.payments.first().payment_method if invoice.payments.exists() else 'Unknown',
        'status': invoice.status,
        'subtotal': str(invoice.total_amount - invoice.discount_amount - invoice.tax_amount),
        'promo_discount': str(invoice.discount_amount),
        'vat_amount': str(invoice.tax_amount),
        'total_amount': str(invoice.total_amount),
        'items': items
    }

    return JsonResponse({
        'success': True,
        'sale': sale_data
    })


@login_required
def update_profile(request):
    """Update user profile"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.username = request.POST.get('username', '').strip()
        user.save()

        return JsonResponse({
            'success': True,
            'user': {
                'full_name': user.get_full_name(),
                'username': user.username,
                'first_name': user.first_name,
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def change_password(request):
    """Change user password"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        from django.contrib.auth import authenticate

        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Validate current password
        user = authenticate(username=request.user.username, password=current_password)
        if not user:
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)

        # Validate new passwords match
        if new_password != confirm_password:
            return JsonResponse({'error': 'New passwords do not match'}, status=400)

        # Validate password strength
        if len(new_password) < 8:
            return JsonResponse({'error': 'Password must be at least 8 characters long'}, status=400)

        # Change password
        user.set_password(new_password)
        user.save()

        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)

        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Helper functions

def _get_cashier_business(request):
    """Get business for cashier user"""
    if hasattr(request.user, 'business_users'):
        return request.user.business_users.first().business
    return None


def _update_order_totals(order):
    """Update order totals"""
    total = sum(item.line_total for item in order.order_items.all())
    order.total_amount = total
    order.save()


def _calculate_order_totals(order, session=None):
    """Calculate order totals including discounts and VAT"""
    subtotal = sum(item.line_total for item in order.order_items.all())

    # Get discounts from session
    promo_discount = 0
    loyalty_discount = 0

    if session:
        promo_data = session.get(f'promo_{order.id}')
        if promo_data:
            promo_discount = Decimal(promo_data['discount'])

        loyalty_data = session.get(f'loyalty_{order.id}')
        if loyalty_data:
            loyalty_discount = Decimal(loyalty_data['discount'])

    total_discount = promo_discount + loyalty_discount
    discounted_subtotal = subtotal - total_discount

    # VAT calculation (13%)
    vat_rate = Decimal('0.13')
    vat_amount = discounted_subtotal * vat_rate

    total_amount = discounted_subtotal + vat_amount

    return {
        'subtotal': subtotal,
        'promo_discount': promo_discount,
        'loyalty_discount': loyalty_discount,
        'total_discount': total_discount,
        'vat_amount': vat_amount,
        'total_amount': total_amount,
    }


def _get_variant_info(variant):
    """Get variant information"""
    if not variant:
        return None

    detail = getattr(variant, 'clothing_detail', None)
    if not detail:
        return None

    info = {}
    if detail.size:
        info['size'] = detail.size.name
    if detail.color:
        info['color'] = detail.color.name

    return info


def _generate_invoice_number():
    """Generate unique invoice number"""
    import uuid
    return f"INV-{uuid.uuid4().hex[:8].upper()}"
