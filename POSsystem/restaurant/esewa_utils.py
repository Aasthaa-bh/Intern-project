"""eSewa Payment Integration Utilities"""
import hmac
import hashlib
import base64
import uuid
import requests
from decimal import Decimal


# eSewa Test Credentials
ESEWA_MERCHANT_ID = "EPAYTEST"
ESEWA_SECRET_KEY = "8gBm/:&EnhH.1/q"
ESEWA_PAYMENT_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
ESEWA_VERIFY_URL = "https://rc-epay.esewa.com.np/api/epay/transaction/status/"


def generate_esewa_signature(total_amount, transaction_uuid, product_code="EPAYTEST"):
    """
    Generate eSewa payment signature using HMAC-SHA256
    
    Args:
        total_amount: Total payment amount
        transaction_uuid: Unique transaction identifier
        product_code: Merchant product code (default: EPAYTEST for sandbox)
    
    Returns:
        Base64 encoded signature string
    """
    # Convert amount to string with 2 decimal places
    amount_str = f"{Decimal(total_amount):.2f}"
    
    # Create message string
    message = f"total_amount={amount_str},transaction_uuid={transaction_uuid},product_code={product_code}"
    
    # Generate HMAC-SHA256 hash
    hash_obj = hmac.new(
        ESEWA_SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    )
    
    # Encode to base64
    signature = base64.b64encode(hash_obj.digest()).decode('utf-8')
    
    return signature


def generate_transaction_uuid():
    """Generate unique transaction UUID"""
    return str(uuid.uuid4())


def verify_esewa_payment(transaction_uuid, product_code="EPAYTEST"):
    """
    Verify eSewa payment status from eSewa server
    
    Args:
        transaction_uuid: Transaction UUID to verify
        product_code: Merchant product code
    
    Returns:
        dict: Payment verification response
    """
    try:
        # Prepare verification request
        verify_url = f"{ESEWA_VERIFY_URL}?product_code={product_code}&total_amount=&transaction_uuid={transaction_uuid}"
        
        print(f"DEBUG: Verifying payment at URL: {verify_url}")
        
        response = requests.get(verify_url, timeout=15)
        
        print(f"DEBUG: eSewa response status: {response.status_code}")
        print(f"DEBUG: eSewa response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG: eSewa response data: {data}")
            
            return {
                'success': True,
                'status': data.get('status'),
                'transaction_uuid': data.get('transaction_uuid'),
                'product_code': data.get('product_code'),
                'total_amount': data.get('total_amount'),
                'ref_id': data.get('ref_id'),
                'message': 'Payment verified successfully'
            }
        else:
            return {
                'success': False,
                'message': f'Verification failed with status {response.status_code}',
                'response_text': response.text
            }
    
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'message': 'eSewa server timeout. Please try again.'
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'Network error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Verification error: {str(e)}'
        }


def prepare_esewa_payment_data(invoice, success_url, failure_url):
    """
    Prepare payment data for eSewa form submission
    
    Args:
        invoice: ReceptionInvoice object
        success_url: URL to redirect on successful payment
        failure_url: URL to redirect on failed payment
    
    Returns:
        dict: Payment form data
    """
    # Generate transaction UUID
    transaction_uuid = generate_transaction_uuid()
    
    # Calculate amounts
    total_amount = float(invoice.total_amount)
    tax_amount = float(invoice.tax_amount) if invoice.tax_amount else 0
    amount = total_amount - tax_amount
    
    # Generate signature
    signature = generate_esewa_signature(total_amount, transaction_uuid)
    
    # Prepare form data
    payment_data = {
        'amount': f"{amount:.2f}",
        'tax_amount': f"{tax_amount:.2f}",
        'total_amount': f"{total_amount:.2f}",
        'transaction_uuid': transaction_uuid,
        'product_code': ESEWA_MERCHANT_ID,
        'product_service_charge': "0",
        'product_delivery_charge': "0",
        'success_url': success_url,
        'failure_url': failure_url,
        'signed_field_names': 'total_amount,transaction_uuid,product_code',
        'signature': signature,
        'esewa_url': ESEWA_PAYMENT_URL,
    }
    
    return payment_data, transaction_uuid
