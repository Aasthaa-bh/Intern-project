from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F
from decimal import Decimal
from .models import Order, OrderItem, Item, Customer
from restaurant.models import DiningTable, KitchenOrder
import json
from django.utils import timezone

@login_required
def waiter_dashboard(request):
    """Main waiter dashboard showing available tables"""
    business = request.user.business
    tables = DiningTable.objects.filter(business=business).select_related('category')
    ready_orders = list(
        KitchenOrder.objects.filter(
            business=business,
            status='READY',
            order__status='OPEN'
        )
        .select_related('order__table')
        .order_by('ready_at', 'sent_at', 'created_at')
    )

    now = timezone.now()
    for kitchen_order in ready_orders:
        ready_time = kitchen_order.ready_at or kitchen_order.sent_at or kitchen_order.created_at
        kitchen_order.ready_wait_minutes = int(max(0, (now - ready_time).total_seconds() // 60))
    
    context = {
        'tables': tables,
        'user': request.user,
        'ready_orders': ready_orders,
        'ready_orders_count': len(ready_orders),
    }
    return render(request, 'pos/waiter_dashboard.html', context)


@login_required
def select_table(request, table_id):
    """Select a table and show menu to create order"""
    table = get_object_or_404(DiningTable, id=table_id, business=request.user.business)
    
    # Get order type from query parameter
    order_type = request.GET.get('order_type', 'DINE_IN')
    
    # Check if table is reserved
    if table.status == 'RESERVED':
        from django.contrib import messages
        messages.error(request, f'Table {table.name} is reserved. Please check with management.')
        return redirect('waiter_dashboard')
    
    # Check if table already has an open order
    existing_order = Order.objects.filter(
        table=table, 
        status='OPEN',
        business=request.user.business
    ).first()
    
    if existing_order:
        return redirect('order_detail', order_id=existing_order.id)
    
    # Get menu items
    menu_items = Item.objects.filter(
        business=request.user.business,
        item_type='MENU',
        is_active=True
    ).select_related('category')
    
    context = {
        'table': table,
        'menu_items': menu_items,
        'order_type': order_type,
        'user': request.user
    }
    return render(request, 'pos/select_menu.html', context)


@login_required
def create_order_direct(request):
    """Create order without table (for TAKEAWAY/DELIVERY)"""
    order_type = request.GET.get('order_type', 'TAKEAWAY')
    
    # Get menu items
    menu_items = Item.objects.filter(
        business=request.user.business,
        item_type='MENU',
        is_active=True
    ).select_related('category')
    
    context = {
        'table': None,
        'menu_items': menu_items,
        'order_type': order_type,
        'user': request.user
    }
    return render(request, 'pos/select_menu.html', context)


@login_required
@transaction.atomic
def create_order(request, table_id=None):
    """Create a new order for the selected table or direct order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        order_type = data.get('order_type', 'DINE_IN')
        
        if not items_data:
            return JsonResponse({'error': 'No items selected'}, status=400)
        
        table = None
        if table_id:
            table = get_object_or_404(DiningTable, id=table_id, business=request.user.business)
            
            # Check if table is reserved
            if table.status == 'RESERVED':
                return JsonResponse({'error': 'Cannot create order. Table is reserved.'}, status=400)
            
            # Check if table is available
            if table.status == 'OCCUPIED':
                return JsonResponse({'error': 'Table is already occupied'}, status=400)
        
        # Generate order number
        last_order = Order.objects.filter(business=request.user.business).order_by('-id').first()
        order_no = f"ORD-{(last_order.id + 1) if last_order else 1:05d}"
        
        # Create order
        order = Order.objects.create(
            business=request.user.business,
            order_no=order_no,
            table=table,
            order_type=order_type,
            status='OPEN',
            opened_at=timezone.now(),
            created_by=request.user,
            notes=data.get('notes', '')
        )
        
        # Add order items
        for item_data in items_data:
            item = Item.objects.get(id=item_data['item_id'], business=request.user.business)
            quantity = Decimal(str(item_data['quantity']))
            
            # Check stock if tracking is enabled
            if item.track_stock:
                if item.stock_qty < quantity:
                    raise Exception(f'Insufficient stock for {item.name}')
                
                # Deduct stock
                item.stock_qty -= quantity
                item.save()
            
            # Calculate line total
            unit_price = item.price
            line_total = unit_price * quantity
            
            OrderItem.objects.create(
                order=order,
                item=item,
                item_name_snapshot=item.name,
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total
            )
        
        # Update table status only for DINE_IN
        if table and order_type == 'DINE_IN':
            table.status = 'OCCUPIED'
            table.save()
        
        # Create kitchen order and send to kitchen immediately
        KitchenOrder.objects.create(
            business=request.user.business,
            order=order,
            status='SENT_TO_KITCHEN',
            sent_at=timezone.now()
        )
        
        message = f'Order created successfully'
        if table:
            message += f' - Table {table.name} is now occupied'
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_no': order.order_no,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def order_detail(request, order_id):
    """View order details and add more items"""
    order = get_object_or_404(
        Order.objects.select_related('table', 'created_by')
        .prefetch_related('items__item'),
        id=order_id,
        business=request.user.business
    )
    
    # Calculate totals
    subtotal = order.items.aggregate(
        total=Sum('line_total')
    )['total'] or Decimal('0')
    
    # Get menu items for adding more
    menu_items = Item.objects.filter(
        business=request.user.business,
        item_type='MENU',
        is_active=True
    ).select_related('category')
    
    # Get or create kitchen order
    kitchen_order, created = KitchenOrder.objects.get_or_create(
        order=order,
        business=request.user.business,
        defaults={'status': 'PENDING'}
    )
    
    # Order is locked ONLY if sent to cashier
    is_locked = kitchen_order.status == 'SENT_TO_CASHIER'
    
    context = {
        'order': order,
        'subtotal': subtotal,
        'menu_items': menu_items,
        'is_locked': is_locked,
        'kitchen_order': kitchen_order,
        'user': request.user
    }
    return render(request, 'pos/order_detail.html', context)


@login_required
@transaction.atomic
def add_order_items(request, order_id):
    """Add more items to an existing order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id, business=request.user.business)
    
    # Check if order is locked (sent to cashier)
    kitchen_order = KitchenOrder.objects.filter(order=order).first()
    if kitchen_order and kitchen_order.status == 'SENT_TO_CASHIER':
        return JsonResponse({'error': 'Order is locked. Cannot add items after sending to cashier'}, status=400)
    
    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        
        if not items_data:
            return JsonResponse({'error': 'No items selected'}, status=400)
        
        # Add order items
        for item_data in items_data:
            item = Item.objects.get(id=item_data['item_id'], business=request.user.business)
            quantity = Decimal(str(item_data['quantity']))
            
            # Check stock if tracking is enabled
            if item.track_stock:
                if item.stock_qty < quantity:
                    raise Exception(f'Insufficient stock for {item.name}')
                
                # Deduct stock
                item.stock_qty -= quantity
                item.save()
            
            # Calculate line total
            unit_price = item.price
            line_total = unit_price * quantity
            
            OrderItem.objects.create(
                order=order,
                item=item,
                item_name_snapshot=item.name,
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total
            )
        
        order.updated_by = request.user
        order.save()
        
        # Update sent_at timestamp every time items are added
        if kitchen_order:
            kitchen_order.sent_at = timezone.now()
            kitchen_order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Items added successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@transaction.atomic
def send_to_kitchen(request, order_id):
    """Send order to kitchen - updates timestamp but doesn't lock"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id, business=request.user.business)
    
    # Get or create kitchen order
    kitchen_order, created = KitchenOrder.objects.get_or_create(
        order=order,
        business=request.user.business,
        defaults={'status': 'PENDING'}
    )
    
    # Check if already sent to cashier (locked)
    if kitchen_order.status == 'SENT_TO_CASHIER':
        return JsonResponse({'error': 'Order already sent to cashier and locked'}, status=400)
    
    # Update status and timestamp
    kitchen_order.status = 'SENT_TO_KITCHEN'
    kitchen_order.sent_at = timezone.now()
    kitchen_order.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Order sent to kitchen successfully. You can still add more items.'
    })


@login_required
@transaction.atomic
def send_to_cashier(request, order_id):
    """Send order to cashier - LOCKS the order permanently"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id, business=request.user.business)
    
    # Get kitchen order
    kitchen_order = KitchenOrder.objects.filter(order=order).first()
    if not kitchen_order:
        return JsonResponse({'error': 'Order not found in kitchen'}, status=400)
    
    # Check if already sent to cashier
    if kitchen_order.status == 'SENT_TO_CASHIER':
        return JsonResponse({'error': 'Order already sent to cashier'}, status=400)
    
    # Lock the order by setting status to SENT_TO_CASHIER
    kitchen_order.status = 'SENT_TO_CASHIER'
    kitchen_order.sent_to_cashier_at = timezone.now()
    kitchen_order.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Order sent to cashier and locked. No more changes allowed.'
    })





@login_required
def get_menu_items_json(request):
    """API endpoint to get menu items as JSON"""
    menu_items = Item.objects.filter(
        business=request.user.business,
        item_type='MENU',
        is_active=True
    ).select_related('category').values(
        'id', 'name', 'price', 'stock_qty', 'track_stock', 'category__name'
    )
    
    return JsonResponse(list(menu_items), safe=False)


@login_required
def kitchen_display(request):
    """Kitchen display showing all orders sent to kitchen organized by type"""
    kitchen_orders = KitchenOrder.objects.filter(
        business=request.user.business,
        status__in=['SENT_TO_KITCHEN', 'PREPARING', 'READY', 'SENT_TO_CASHIER'],
        order__status='OPEN'
    ).select_related('order__table', 'order__created_by').prefetch_related(
        'order__items__item'
    ).order_by('-sent_at')
    
    # Organize orders by type
    dine_in_orders = []
    takeaway_orders = []
    delivery_orders = []
    
    for ko in kitchen_orders:
        if ko.order.order_type == 'DINE_IN':
            dine_in_orders.append(ko)
        elif ko.order.order_type == 'TAKEAWAY':
            takeaway_orders.append(ko)
        elif ko.order.order_type == 'DELIVERY':
            delivery_orders.append(ko)
    
    context = {
        'dine_in_orders': dine_in_orders,
        'takeaway_orders': takeaway_orders,
        'delivery_orders': delivery_orders,
        'user': request.user
    }
    return render(request, 'pos/kitchen_display.html', context)


@login_required
@transaction.atomic
def update_kitchen_status(request, kitchen_order_id):
    """Update kitchen order status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    kitchen_order = get_object_or_404(
        KitchenOrder, 
        id=kitchen_order_id, 
        business=request.user.business
    )
    
    data = json.loads(request.body)
    new_status = data.get('status')
    
    if new_status not in ['PREPARING', 'READY']:
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    kitchen_order.status = new_status
    if new_status == 'READY':
        kitchen_order.ready_at = timezone.now()
    kitchen_order.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Order marked as {new_status}'
    })


@login_required
def cashier_view(request):
    """Cashier/Receptionist view for orders sent to cashier"""
    ready_orders = Order.objects.filter(
        business=request.user.business,
        status='OPEN',
        kitchen_order__status='SENT_TO_CASHIER'
    ).select_related('table', 'created_by', 'kitchen_order').prefetch_related('items')
    
    orders_with_totals = []
    for order in ready_orders:
        subtotal = order.items.aggregate(total=Sum('line_total'))['total'] or Decimal('0')
        orders_with_totals.append({
            'order': order,
            'subtotal': subtotal
        })
    
    context = {
        'orders_with_totals': orders_with_totals,
        'user': request.user
    }
    return render(request, 'pos/cashier_view.html', context)


@login_required
@transaction.atomic
def complete_order(request, order_id):
    """Complete order and free up table"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id, business=request.user.business)
    
    # Mark order as completed
    order.status = 'COMPLETED'
    order.closed_at = timezone.now()
    order.updated_by = request.user
    order.save()
    
    # Free up the table
    if order.table:
        order.table.status = 'AVAILABLE'
        order.table.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Order completed and table is now available'
    })


@login_required
def table_management(request):
    """Manage table reservations"""
    tables = DiningTable.objects.filter(
        business=request.user.business
    ).select_related('category').order_by('category__name', 'number')
    
    context = {
        'tables': tables,
        'user': request.user
    }
    return render(request, 'pos/table_management.html', context)


@login_required
@transaction.atomic
def update_table_status(request, table_id):
    """Update table status (Reserve/Make Available)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    table = get_object_or_404(DiningTable, id=table_id, business=request.user.business)
    
    data = json.loads(request.body)
    new_status = data.get('status')
    
    if new_status not in ['AVAILABLE', 'RESERVED']:
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    # Check if table has active order
    if new_status == 'AVAILABLE':
        active_order = Order.objects.filter(
            table=table,
            status='OPEN'
        ).first()
        
        if active_order:
            return JsonResponse({
                'error': 'Cannot make table available. It has an active order.'
            }, status=400)
    
    table.status = new_status
    table.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Table {table.name} is now {new_status}'
    })
