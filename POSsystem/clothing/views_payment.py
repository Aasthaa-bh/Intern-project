from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from decimal import Decimal

from .esewa_utils import (
    generate_transaction_uuid,
    prepare_esewa_form_data,
    decode_esewa_callback_data,
    verify_esewa_response_signature,
    verify_esewa_payment
)


def initiate_payment(request):
    """Initiate eSewa payment - Demo"""
    # Demo amount (replace with actual order amount)
    amount = Decimal("1500.00")
    
    # Generate unique transaction UUID
    transaction_uuid = generate_transaction_uuid()
    
    # Prepare eSewa form data
    success_url = request.build_absolute_uri('/clothing/payment/success/')
    failure_url = request.build_absolute_uri('/clothing/payment/failure/')
    
    esewa_data = prepare_esewa_form_data(
        total_amount=amount,
        transaction_uuid=transaction_uuid,
        success_url=success_url,
        failure_url=failure_url
    )
    
    context = {
        'esewa_data': esewa_data,
        'amount': amount,
        'transaction_uuid': transaction_uuid,
    }
    
    return render(request, 'clothing/esewa_payment.html', context)


@csrf_exempt
def payment_success(request):
    """Handle eSewa success callback"""
    encoded_data = request.GET.get('data')
    
    if not encoded_data:
        return render(request, 'clothing/payment_failure.html', {
            'error_message': 'No payment data received'
        })
    
    try:
        # Decode callback data
        callback_data = decode_esewa_callback_data(encoded_data)
        
        # Verify signature
        if not verify_esewa_response_signature(callback_data):
            return render(request, 'clothing/payment_failure.html', {
                'error_message': 'Invalid payment signature',
                'transaction_uuid': callback_data.get('transaction_uuid')
            })
        
        # Verify payment with eSewa API
        verification = verify_esewa_payment(
            transaction_uuid=callback_data['transaction_uuid'],
            total_amount=callback_data['total_amount']
        )
        
        if verification['success']:
            # Payment successful - Update your order/database here
            # Example:
            # order = Order.objects.get(transaction_uuid=callback_data['transaction_uuid'])
            # order.payment_status = 'PAID'
            # order.save()
            
            # Create notifications for successful payment
            from core.models import Business
            from clothing.models import Notification
            business = request.user.business if request.user.is_authenticated else Business.objects.first()
            
            if business:
                # Notification for Admin (Owner/SuperAdmin)
                Notification.objects.create(
                    business=business,
                    notification_type='PAYMENT_COMPLETED',
                    target_role='ADMIN',
                    title='Payment Received',
                    message=f'Payment of Rs {callback_data["total_amount"]} completed successfully. Transaction: {callback_data.get("transaction_code", "N/A")}',
                    link='',
                    is_read=False
                )
                
                # Notification for Cashier
                Notification.objects.create(
                    business=business,
                    notification_type='PAYMENT_COMPLETED',
                    target_role='CASHIER',
                    title='Payment Confirmed',
                    message=f'Customer payment of Rs {callback_data["total_amount"]} has been confirmed. Transaction: {callback_data.get("transaction_code", "N/A")}',
                    link='',
                    is_read=False
                )
            
            context = {
                'transaction_uuid': callback_data['transaction_uuid'],
                'total_amount': callback_data['total_amount'],
                'transaction_code': callback_data.get('transaction_code'),
            }
            return render(request, 'clothing/payment_success.html', context)
        else:
            return render(request, 'clothing/payment_failure.html', {
                'error_message': verification['message'],
                'transaction_uuid': callback_data.get('transaction_uuid')
            })
            
    except Exception as e:
        return render(request, 'clothing/payment_failure.html', {
            'error_message': f'Payment processing error: {str(e)}'
        })


@csrf_exempt
def payment_failure(request):
    """Handle eSewa failure callback"""
    import logging
    logger = logging.getLogger(__name__)
    
    encoded_data = request.GET.get('data')
    
    error_message = 'Payment was cancelled or failed'
    transaction_uuid = None
    amount = None
    
    logger.info(f"Payment failure callback received. Encoded data: {bool(encoded_data)}")
    
    if encoded_data:
        try:
            callback_data = decode_esewa_callback_data(encoded_data)
            transaction_uuid = callback_data.get('transaction_uuid')
            amount = callback_data.get('total_amount')
            error_message = callback_data.get('message', error_message)
            logger.info(f"Decoded payment failure: UUID={transaction_uuid}, Amount={amount}")
        except Exception as e:
            logger.error(f"Error decoding payment failure data: {e}")
            pass
    
    # Create notifications for payment failure/cancellation
    from core.models import Business
    from clothing.models import Notification, ClothingEsewaPayment
    
    business = None
    
    # Try to get business from authenticated user
    if request.user.is_authenticated and hasattr(request.user, 'business'):
        business = request.user.business
        logger.info(f"Got business from authenticated user: {business}")
    
    # If no business from user, try to get from ClothingEsewaPayment record
    if not business and transaction_uuid:
        try:
            esewa_payment = ClothingEsewaPayment.objects.get(transaction_uuid=transaction_uuid)
            business = esewa_payment.business
            logger.info(f"Got business from ClothingEsewaPayment: {business}")
        except ClothingEsewaPayment.DoesNotExist:
            logger.warning(f"No ClothingEsewaPayment found for UUID: {transaction_uuid}")
            pass
    
    # If still no business, get the first clothing business (fallback)
    if not business:
        business = Business.objects.filter(business_type__name__iexact='clothing').first()
        logger.info(f"Using fallback business: {business}")
    
    # ALWAYS create a notification if we have a business (for debugging)
    if business:
        logger.info(f"Payment failure view called - creating notification for {business}")
        if transaction_uuid:
            logger.info(f"Creating payment failure notifications for business: {business}")
            # Notification for Admin
            Notification.objects.create(
                business=business,
                notification_type='PAYMENT_FAILED',
                target_role='ADMIN',
                title='Payment Failed',
                message=f'Payment cancelled or failed. {f"Amount: Rs {amount}. " if amount else ""}Transaction: {transaction_uuid}',
                link='',
                is_read=False
            )
            logger.info("Created ADMIN notification")
            
            # Notification for Cashier
            Notification.objects.create(
                business=business,
                notification_type='PAYMENT_FAILED',
                target_role='CASHIER',
                title='Payment Cancelled',
                message=f'Customer payment was cancelled or failed. {f"Amount: Rs {amount}. " if amount else ""}Transaction: {transaction_uuid}',
                link='',
                is_read=False
            )
            logger.info("Created CASHIER notification")
        else:
            # No transaction UUID - user probably cancelled before payment
            logger.info(f"Creating generic payment cancellation notification for business: {business}")
            # Notification for Admin
            Notification.objects.create(
                business=business,
                notification_type='PAYMENT_FAILED',
                target_role='ADMIN',
                title='Payment Cancelled',
                message='A payment attempt was cancelled by the customer.',
                link='',
                is_read=False
            )
            
            # Notification for Cashier
            Notification.objects.create(
                business=business,
                notification_type='PAYMENT_FAILED',
                target_role='CASHIER',
                title='Payment Cancelled',
                message='Customer cancelled the payment.',
                link='',
                is_read=False
            )
            logger.info("Created generic cancellation notifications")
    else:
        logger.error(f"CRITICAL: Cannot create notifications. Business is None!")
    
    context = {
        'error_message': error_message,
        'transaction_uuid': transaction_uuid,
    }
    
    return render(request, 'clothing/payment_failure.html', context)
