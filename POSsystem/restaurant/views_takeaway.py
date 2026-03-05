from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from pos.models import Order
from restaurant.models import ReceptionInvoice, ReceptionPayment
from decimal import Decimal
from django.db.models import Sum

def takeaway_bill(request, order_id):
    """Create bill for takeaway order"""
    order = get_object_or_404(Order, id=order_id, order_type='TAKEAWAY')
    
    # Calculate order total
    subtotal = order.items.aggregate(total=Sum('line_total'))['total'] or Decimal('0')
    tax_amount = subtotal * Decimal('0.13')
    total_amount = subtotal + tax_amount
    
    # Check if invoice already exists
    existing_invoice = ReceptionInvoice.objects.filter(order=order, status='PENDING').first()
    
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', 'Walk-in')
        customer_phone = request.POST.get('customer_phone', '')
        discount = Decimal(request.POST.get('discount', '0'))
        
        final_total = total_amount - discount
        
        # Generate invoice number
        import random
        invoice_number = f"TKW-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        # Get user
        from accounts.models import User
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        
        # Create or update invoice
        if existing_invoice:
            invoice = existing_invoice
            invoice.customer_name = customer_name
            invoice.customer_phone = customer_phone
            invoice.discount_amount = discount
            invoice.total_amount = final_total
            invoice.save()
        else:
            invoice = ReceptionInvoice.objects.create(
                business=order.business,
                order=order,
                invoice_number=invoice_number,
                customer_name=customer_name,
                customer_phone=customer_phone,
                subtotal=subtotal,
                tax_amount=tax_amount,
                discount_amount=discount,
                total_amount=final_total,
                status='PENDING',
                created_by=user
            )
        
        messages.success(request, f'Invoice {invoice.invoice_number} created successfully!')
        return redirect('process_payment', invoice_id=invoice.id)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'existing_invoice': existing_invoice,
    }
    return render(request, 'restaurant/takeaway_bill.html', context)
