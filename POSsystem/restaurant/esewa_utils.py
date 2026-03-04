"""eSewa Payment Integration Utilities (v2)"""
import hmac
import hashlib
import base64
import uuid
import requests
from decimal import Decimal

# eSewa Test Credentials (Sandbox)
ESEWA_MERCHANT_ID = "EPAYTEST"
ESEWA_SECRET_KEY = "8gBm/:&EnhH.1/q"
ESEWA_PAYMENT_URL = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
ESEWA_VERIFY_URL = "https://rc-epay.esewa.com.np/api/epay/transaction/status/"


def generate_transaction_uuid():
    return str(uuid.uuid4())


def generate_esewa_signature(total_amount, transaction_uuid, product_code="EPAYTEST"):
    amount_str = f"{Decimal(total_amount):.2f}"
    message = f"total_amount={amount_str},transaction_uuid={transaction_uuid},product_code={product_code}"

    hash_obj = hmac.new(
        ESEWA_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    )
    return base64.b64encode(hash_obj.digest()).decode("utf-8")


def verify_esewa_payment(transaction_uuid, total_amount, product_code="EPAYTEST"):
    """
    Server-to-server verification
    """
    try:
        amount_str = f"{Decimal(total_amount):.2f}"
        verify_url = (
            f"{ESEWA_VERIFY_URL}"
            f"?product_code={product_code}"
            f"&total_amount={amount_str}"
            f"&transaction_uuid={transaction_uuid}"
        )

        response = requests.get(verify_url, timeout=15)

        if response.status_code == 200:
            data = response.json()
            return {"success": True, "data": data}

        return {"success": False, "message": f"Verify failed: {response.status_code}", "body": response.text}

    except Exception as e:
        return {"success": False, "message": str(e)}


def prepare_esewa_payment_data(invoice, success_url, failure_url, product_code="EPAYTEST"):
    """
    Restaurant Billing (Invoice-based)
    """
    transaction_uuid = generate_transaction_uuid()

    total_amount = Decimal(invoice.total_amount or 0)
    tax_amount = Decimal(invoice.tax_amount or 0)
    amount = total_amount - tax_amount

    signature = generate_esewa_signature(total_amount, transaction_uuid, product_code)

    payment_data = {
        "amount": f"{amount:.2f}",
        "tax_amount": f"{tax_amount:.2f}",
        "total_amount": f"{total_amount:.2f}",
        "transaction_uuid": transaction_uuid,
        "product_code": product_code,
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "success_url": success_url,
        "failure_url": failure_url,
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": signature,
        "esewa_url": ESEWA_PAYMENT_URL,
    }

    return payment_data, transaction_uuid


def prepare_esewa_form_data(total_amount, transaction_uuid, success_url, failure_url, product_code="EPAYTEST"):
    """
    Subscription Upgrade (Generic)
    """
    total_amount = Decimal(total_amount or 0)
    signature = generate_esewa_signature(total_amount, transaction_uuid, product_code)

    return {
        "amount": f"{total_amount:.2f}",
        "tax_amount": "0",
        "total_amount": f"{total_amount:.2f}",
        "transaction_uuid": transaction_uuid,
        "product_code": product_code,
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "success_url": success_url,
        "failure_url": failure_url,
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": signature,
        "esewa_url": ESEWA_PAYMENT_URL,
    }