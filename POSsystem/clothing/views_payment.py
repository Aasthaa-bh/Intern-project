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
    encoded_data = request.GET.get('data')
    
    error_message = 'Payment was cancelled or failed'
    transaction_uuid = None
    
    if encoded_data:
        try:
            callback_data = decode_esewa_callback_data(encoded_data)
            transaction_uuid = callback_data.get('transaction_uuid')
            error_message = callback_data.get('message', error_message)
        except:
            pass
    
    context = {
        'error_message': error_message,
        'transaction_uuid': transaction_uuid,
    }
    
    return render(request, 'clothing/payment_failure.html', context)
