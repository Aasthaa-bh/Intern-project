import base64
import hashlib
import hmac
import json
import uuid
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings


def generate_transaction_uuid():
    """Generate unique transaction UUID for eSewa"""
    return str(uuid.uuid4())


def _format_amount(amount):
    """Format amount to 2 decimal places as string"""
    try:
        return format(Decimal(str(amount)), ".2f")
    except (InvalidOperation, ValueError, TypeError):
        return "0.00"


def _generate_hmac_signature(message: str, secret_key: str) -> str:
    """Generate Base64-encoded HMAC SHA256 signature"""
    digest = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def generate_esewa_signature(total_amount, transaction_uuid, product_code):
    """
    Generate eSewa request signature
    Format: total_amount=...,transaction_uuid=...,product_code=...
    """
    message = (
        f"total_amount={_format_amount(total_amount)},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )
    return _generate_hmac_signature(message, settings.ESEWA_SECRET_KEY)


def prepare_esewa_form_data(total_amount, transaction_uuid, success_url, failure_url, product_code=None):
    """Prepare data for eSewa payment form"""
    product_code = product_code or settings.ESEWA_PRODUCT_CODE

    amount = Decimal(str(total_amount))
    tax_amount = Decimal("0")
    product_service_charge = Decimal("0")
    product_delivery_charge = Decimal("0")

    final_total = amount + tax_amount + product_service_charge + product_delivery_charge

    signature = generate_esewa_signature(
        total_amount=final_total,
        transaction_uuid=transaction_uuid,
        product_code=product_code,
    )

    return {
        "action": settings.ESEWA_FORM_URL,
        "fields": {
            "amount": _format_amount(amount),
            "tax_amount": _format_amount(tax_amount),
            "total_amount": _format_amount(final_total),
            "transaction_uuid": transaction_uuid,
            "product_code": product_code,
            "product_service_charge": _format_amount(product_service_charge),
            "product_delivery_charge": _format_amount(product_delivery_charge),
            "success_url": success_url,
            "failure_url": failure_url,
            "signed_field_names": "total_amount,transaction_uuid,product_code",
            "signature": signature,
        }
    }


def decode_esewa_callback_data(encoded_data: str):
    """Decode Base64 callback data from eSewa"""
    decoded_json = base64.b64decode(encoded_data).decode("utf-8")
    return json.loads(decoded_json)


def verify_esewa_response_signature(payload: dict) -> bool:
    """Verify signature sent by eSewa in callback response"""
    signed_field_names = payload.get("signed_field_names")
    received_signature = payload.get("signature")

    if not signed_field_names or not received_signature:
        return False

    field_names = [field.strip() for field in signed_field_names.split(",") if field.strip()]

    message_parts = []
    for field in field_names:
        if field == "signature":
            continue
        value = payload.get(field, "")
        message_parts.append(f"{field}={value}")

    message = ",".join(message_parts)
    generated_signature = _generate_hmac_signature(message, settings.ESEWA_SECRET_KEY)

    return hmac.compare_digest(generated_signature, received_signature)


def verify_esewa_payment(transaction_uuid, total_amount, product_code=None, timeout=15):
    """Verify payment using eSewa status check API"""
    product_code = product_code or settings.ESEWA_PRODUCT_CODE

    params = {
        "product_code": product_code,
        "total_amount": _format_amount(total_amount),
        "transaction_uuid": transaction_uuid,
    }

    try:
        response = requests.get(
            settings.ESEWA_STATUS_URL,
            params=params,
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Status check failed: {str(e)}",
            "data": {},
        }
    except ValueError:
        return {
            "success": False,
            "message": "Invalid JSON response from eSewa",
            "data": {},
        }

    status = str(data.get("status", "")).upper()

    if status == "COMPLETE":
        return {
            "success": True,
            "message": "Payment verified successfully",
            "data": data,
        }

    return {
        "success": False,
        "message": f"Payment not complete. Status: {status or 'UNKNOWN'}",
        "data": data,
    }
