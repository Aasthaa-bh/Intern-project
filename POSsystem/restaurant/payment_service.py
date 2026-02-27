"""Payment service for handling payment verification and status updates"""
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal


def calculate_invoice_paid_amount(invoice):
    """Calculate total amount paid for an invoice"""
    total = invoice.payments.filter(payment_status='COMPLETED').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    return total


def update_invoice_status(invoice):
    """Update invoice status to PAID if fully paid"""
    total_paid = calculate_invoice_paid_amount(invoice)
    
    if total_paid >= invoice.total_amount:
        invoice.status = 'PAID'
        invoice.save()
        return True
    return False


def update_table_status(table):
    """Update table status to AVAILABLE if all invoices are paid"""
    if not table:
        return False
    
    # Check if there are any pending invoices for this table
    from .models import ReceptionInvoice
    pending_invoices = ReceptionInvoice.objects.filter(
        table=table,
        status='PENDING'
    ).exists()
    
    if not pending_invoices and table.status == 'OCCUPIED':
        table.status = 'AVAILABLE'
        table.save()
        return True
    return False


@transaction.atomic
def verify_payment(payment_id, transaction_id, verified_by):
    """
    Verify a pending payment and update related records
    
    Returns: dict with success, message, invoice_paid, table_freed
    """
    from .models import ReceptionPayment
    
    # Validate transaction ID
    if not transaction_id or not transaction_id.strip():
        return {
            'success': False,
            'message': 'Transaction ID is required',
            'invoice_paid': False,
            'table_freed': False
        }
    
    if len(transaction_id) > 100:
        return {
            'success': False,
            'message': 'Transaction ID too long (max 100 characters)',
            'invoice_paid': False,
            'table_freed': False
        }
    
    try:
        payment = ReceptionPayment.objects.select_for_update().get(id=payment_id)
    except ReceptionPayment.DoesNotExist:
        return {
            'success': False,
            'message': 'Payment not found',
            'invoice_paid': False,
            'table_freed': False
        }
    
    # Check if already completed
    if payment.payment_status == 'COMPLETED':
        return {
            'success': False,
            'message': 'Payment already verified and completed',
            'invoice_paid': False,
            'table_freed': False
        }
    
    # Update payment
    payment.transaction_id = transaction_id.strip()
    payment.payment_status = 'COMPLETED'
    payment.processed_by = verified_by
    payment.save()
    
    # Update invoice status
    invoice = payment.invoice
    invoice_paid = update_invoice_status(invoice)
    
    # Update table status if invoice is paid
    table_freed = False
    if invoice_paid and invoice.table:
        table_freed = update_table_status(invoice.table)
    
    return {
        'success': True,
        'message': 'Payment verified successfully',
        'invoice_paid': invoice_paid,
        'table_freed': table_freed
    }


def get_pending_payments(business):
    """Get all pending payments for a business"""
    from .models import ReceptionPayment
    return ReceptionPayment.objects.filter(
        business=business,
        payment_status='PENDING'
    ).select_related('invoice', 'invoice__table', 'processed_by').order_by('-processed_at')
