"""
eSewa payment integration for the clothing cashier POS.

Flow:
  1. Cashier clicks "Pay via eSewa" on POS
  2. POST /clothing/cashier/esewa/initiate/  → creates a pending EsewaPayment,
     returns form data to redirect the customer to eSewa
  3. eSewa redirects to success_url or failure_url with Base64 `data` param
  4. Success view verifies signature + status API, marks order complete
  5. Failure view marks payment failed, lets cashier retry
"""

import base64
import hashlib
import hmac
import json
import uuid
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.db import transaction as db_transaction

from pos.models import Order, OrderItem, Item, ItemVariant


# ── Helpers (mirrors restaurant/esewa_utils.py) ───────────────────────────────

def _format_amount(amount):
    try:
        return format(Decimal(str(amount)), ".2f")
    except (InvalidOperation, ValueError, TypeError):
        return "0.00"


def _hmac_signature(message: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _esewa_signature(total_amount, transaction_uuid, product_code):
    msg = (
        f"total_amount={_format_amount(total_amount)},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )
    return _hmac_signature(msg, settings.ESEWA_SECRET_KEY)


def _decode_callback(encoded: str) -> dict:
    return json.loads(base64.b64decode(encoded).decode("utf-8"))


def _verify_callback_signature(payload: dict) -> bool:
    signed_fields = payload.get("signed_field_names", "")
    received_sig  = payload.get("signature", "")
    if not signed_fields or not received_sig:
        return False
    parts = [
        f"{f}={payload.get(f, '')}"
        for f in [x.strip() for x in signed_fields.split(",")]
        if f != "signature"
    ]
    return hmac.compare_digest(
        _hmac_signature(",".join(parts), settings.ESEWA_SECRET_KEY),
        received_sig,
    )


def _verify_with_api(transaction_uuid, total_amount, product_code=None):
    product_code = product_code or settings.ESEWA_PRODUCT_CODE
    try:
        resp = requests.get(
            settings.ESEWA_STATUS_URL,
            params={
                "product_code": product_code,
                "total_amount": _format_amount(total_amount),
                "transaction_uuid": transaction_uuid,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"success": False, "message": str(e), "data": {}}

    if str(data.get("status", "")).upper() == "COMPLETE":
        return {"success": True, "data": data}
    return {"success": False, "message": f"eSewa status: {data.get('status')}", "data": data}


def _get_business(request):
    return getattr(request.user, "business", None)


# ── Model import (lazy to avoid circular) ────────────────────────────────────

def _esewa_model():
    from clothing.models import ClothingEsewaPayment
    return ClothingEsewaPayment


# ── Views ─────────────────────────────────────────────────────────────────────

@login_required
def esewa_initiate(request):
    """
    POST — receives cart JSON, creates Order (PENDING) + EsewaPayment,
    returns eSewa form fields so the frontend can redirect.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    business = _get_business(request)
    if not business:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        data = json.loads(request.body)
        items_data = data.get("items", [])
        if not items_data:
            return JsonResponse({"error": "Cart is empty"}, status=400)

        customer_phone = (data.get("customer_phone") or "").strip()
        customer_name  = (data.get("customer_name") or "Walk-in").strip()

        # ── compute totals ────────────────────────────────────────────────
        from decimal import Decimal as D
        subtotal = sum(D(str(r["price"])) * D(str(r["quantity"])) for r in items_data)

        # apply loyalty discount if any
        discount_pct = D(str(data.get("discount_pct", "0") or "0"))
        discount_amt = (subtotal * discount_pct / 100).quantize(D("0.01"))
        after_discount = subtotal - discount_amt
        vat   = (after_discount * D("0.13")).quantize(D("0.01"))
        total = after_discount + vat

        with db_transaction.atomic():
            # create PENDING order
            order_no = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            order = Order.objects.create(
                business=business,
                order_no=order_no,
                order_type="COUNTER",
                status="OPEN",          # stays OPEN until eSewa confirms
                opened_at=timezone.now(),
                business_date=timezone.now().date(),
                created_by=request.user,
            )

            for row in items_data:
                item = get_object_or_404(Item, id=row["item_id"], business=business)
                variant = None
                if row.get("variant_id"):
                    variant = get_object_or_404(ItemVariant, id=row["variant_id"], item=item)
                qty   = D(str(row["quantity"]))
                price = D(str(row["price"]))
                OrderItem.objects.create(
                    order=order,
                    item=item,
                    variant=variant,
                    item_name_snapshot=item.name,
                    variant_name_snapshot=variant.name if variant else "",
                    sku_snapshot=variant.sku if variant else (item.sku or ""),
                    unit_price=price,
                    quantity=qty,
                    line_total=price * qty,
                )

            # create eSewa payment record
            txn_uuid = str(uuid.uuid4())
            EsewaPayment = _esewa_model()
            ep = EsewaPayment.objects.create(
                business=business,
                order=order,
                transaction_uuid=txn_uuid,
                amount=total,
                customer_phone=customer_phone,
                customer_name=customer_name,
                discount_amt=discount_amt,
                discount_pct=discount_pct,
                status="PENDING",
                created_by=request.user,
            )

        # ── build eSewa form data ─────────────────────────────────────────
        success_url = request.build_absolute_uri(reverse("clothing_esewa_success"))
        failure_url = request.build_absolute_uri(reverse("clothing_esewa_failure"))
        product_code = settings.ESEWA_PRODUCT_CODE
        signature = _esewa_signature(total, txn_uuid, product_code)

        form_data = {
            "action": settings.ESEWA_FORM_URL,
            "fields": {
                "amount":                    _format_amount(total),
                "tax_amount":                "0.00",
                "total_amount":              _format_amount(total),
                "transaction_uuid":          txn_uuid,
                "product_code":              product_code,
                "product_service_charge":    "0.00",
                "product_delivery_charge":   "0.00",
                "success_url":               success_url,
                "failure_url":               failure_url,
                "signed_field_names":        "total_amount,transaction_uuid,product_code",
                "signature":                 signature,
            },
        }

        return JsonResponse({"success": True, "form_data": form_data, "payment_id": ep.id})

    except Exception as e:
        import traceback; traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def esewa_success(request):
    """eSewa redirects here after payment attempt."""
    encoded = request.GET.get("data") or request.POST.get("data")
    if not encoded:
        return HttpResponseBadRequest("Missing eSewa callback data.")

    try:
        payload = _decode_callback(encoded)
    except Exception:
        return HttpResponseBadRequest("Invalid eSewa callback data.")

    txn_uuid = payload.get("transaction_uuid")
    total_amount_str = payload.get("total_amount", "0")

    EsewaPayment = _esewa_model()
    try:
        ep = EsewaPayment.objects.select_related("order", "business").get(
            transaction_uuid=txn_uuid
        )
    except EsewaPayment.DoesNotExist:
        return HttpResponseBadRequest("Payment record not found.")

    # 1. verify callback signature
    if not _verify_callback_signature(payload):
        ep.status = "FAILED"
        ep.failure_reason = "Invalid callback signature"
        ep.save(update_fields=["status", "failure_reason"])
        return render(request, "cashier/esewa_failed.html", {
            "reason": "Invalid eSewa response signature.",
            "order": ep.order,
        })

    # 2. verify via status API
    result = _verify_with_api(txn_uuid, total_amount_str)
    if not result["success"]:
        ep.status = "FAILED"
        ep.failure_reason = result.get("message", "")
        ep.save(update_fields=["status", "failure_reason"])
        return render(request, "cashier/esewa_failed.html", {
            "reason": result.get("message"),
            "order": ep.order,
        })

    # 3. mark payment + order complete, deduct stock
    with db_transaction.atomic():
        ep.status = "COMPLETED"
        ep.esewa_ref_id = result["data"].get("transaction_code", "")
        ep.completed_at = timezone.now()
        ep.save(update_fields=["status", "esewa_ref_id", "completed_at"])

        order = ep.order
        order.status = "COMPLETED"
        order.closed_at = timezone.now()
        order.save(update_fields=["status", "closed_at"])

        # deduct stock
        for oi in order.items.select_related("item", "variant").all():
            if oi.variant:
                oi.variant.stock_qty = (oi.variant.stock_qty or 0) - oi.quantity
                oi.variant.save(update_fields=["stock_qty"])
            elif oi.item.track_stock:
                oi.item.stock_qty = (oi.item.stock_qty or 0) - oi.quantity
                oi.item.save(update_fields=["stock_qty"])

        # loyalty points
        _handle_loyalty(ep)

    receipt_url = (
        reverse("cashier_receipt", args=[order.id])
        + f"?method=ESEWA"
        + f"&discount={ep.discount_amt}"
        + f"&discount_pct={ep.discount_pct}"
        + f"&points={ep.points_earned}"
        + f"&customer={ep.customer_name}"
    )
    return redirect(receipt_url)


@login_required
def esewa_failure(request):
    """eSewa redirects here on failure / cancel."""
    encoded = request.GET.get("data") or request.POST.get("data")
    txn_uuid = None

    if encoded:
        try:
            payload = _decode_callback(encoded)
            txn_uuid = payload.get("transaction_uuid")
        except Exception:
            pass

    EsewaPayment = _esewa_model()
    ep = None
    if txn_uuid:
        ep = EsewaPayment.objects.filter(transaction_uuid=txn_uuid).first()
        if ep and ep.status == "PENDING":
            ep.status = "FAILED"
            ep.failure_reason = "Cancelled or failed at eSewa"
            ep.save(update_fields=["status", "failure_reason"])

            # cancel the order too
            if ep.order and ep.order.status == "OPEN":
                ep.order.status = "CANCELLED"
                ep.order.save(update_fields=["status"])

    return render(request, "cashier/esewa_failed.html", {
        "reason": "Payment was cancelled or failed.",
        "order": ep.order if ep else None,
    })


# ── Loyalty helper ────────────────────────────────────────────────────────────

def _handle_loyalty(ep):
    """Earn loyalty points after successful eSewa payment."""
    if not ep.customer_phone:
        return
    try:
        from clothing.models import CashierCustomer, CashierLoyaltyTransaction, ClothingLoyaltySetting
        business = ep.business
        customer, _ = CashierCustomer.objects.get_or_create(
            business=business,
            phone=ep.customer_phone,
            defaults={"name": ep.customer_name or f"Customer {ep.customer_phone}"},
        )
        try:
            ls = ClothingLoyaltySetting.objects.get(business=business, is_active=True)
            points = ls.calc_points(ep.amount)
        except ClothingLoyaltySetting.DoesNotExist:
            points = int(ep.amount // 100)   # fallback: 1 pt per Rs.100

        if points > 0:
            customer.loyalty_points += points
            CashierLoyaltyTransaction.objects.create(
                customer=customer,
                transaction_type="EARNED",
                points=points,
                amount=ep.amount,
                invoice_number=ep.order.order_no,
            )

        customer.total_purchases += ep.amount
        customer.purchase_count  += 1
        customer.last_purchase_date = timezone.now()
        customer.save()

        ep.points_earned = points
        ep.save(update_fields=["points_earned"])
    except Exception:
        pass   # loyalty failure must never break the payment confirmation
