from datetime import timedelta
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from .views import _get_request_business, _get_dev_business_fallback
from pos.models import Order, OrderItem
from .models import ReceptionInvoice, ReceptionPayment
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate

def restaurant_reports(request):
    business = _get_request_business(request)
    if business is None:
        business = _get_dev_business_fallback()

    start_date = (request.GET.get("start_date") or "").strip()
    end_date = (request.GET.get("end_date") or "").strip()
    today = timezone.localdate()

    if not business:
        context = {
            "today_sales": 0,
            "month_sales": 0,
            "completed_orders": 0,
            "avg_order_value": 0,
            "highest_sales_day": None,
            "best_selling_items": [],
            "sales_by_order_type": [],
            "payment_summary": [],
            "table_wise_sales": [],
            "sales_by_day": [],
            "start_date": start_date,
            "end_date": end_date,
        }
        return render(request, "restaurant/reports.html", context)

    invoice_qs = ReceptionInvoice.objects.filter(
        business=business
    ).exclude(status="CANCELLED")

    order_qs = Order.objects.filter(
        business=business,
        status="COMPLETED",
    )

    payment_qs = ReceptionPayment.objects.filter(
        business=business,
        payment_status="COMPLETED",
    )

    if start_date:
        invoice_qs = invoice_qs.filter(created_at__date__gte=start_date)
        order_qs = order_qs.filter(opened_at__date__gte=start_date)
        payment_qs = payment_qs.filter(created_at__date__gte=start_date)

    if end_date:
        invoice_qs = invoice_qs.filter(created_at__date__lte=end_date)
        order_qs = order_qs.filter(opened_at__date__lte=end_date)
        payment_qs = payment_qs.filter(created_at__date__lte=end_date)

    today_sales = (
        ReceptionInvoice.objects.filter(
            business=business,
            created_at__date=today,
        )
        .exclude(status="CANCELLED")
        .aggregate(total=Sum("total_amount"))["total"] or 0
    )

    month_sales = (
        ReceptionInvoice.objects.filter(
            business=business,
            created_at__year=today.year,
            created_at__month=today.month,
        )
        .exclude(status="CANCELLED")
        .aggregate(total=Sum("total_amount"))["total"] or 0
    )

    completed_orders = order_qs.count()

    avg_order_value = invoice_qs.aggregate(avg=Avg("total_amount"))["avg"] or 0

    best_selling_items = (
        OrderItem.objects.filter(
            order__business=business,
            order__status="COMPLETED",
            item__item_type="MENU",
        )
        .values("item_name_snapshot")
        .annotate(
            total_qty=Sum("quantity"),
            total_sales=Sum("line_total"),
        )
        .order_by("-total_qty", "-total_sales")[:10]
    )

    if start_date:
        best_selling_items = best_selling_items.filter(order__opened_at__date__gte=start_date)
    if end_date:
        best_selling_items = best_selling_items.filter(order__opened_at__date__lte=end_date)

    sales_by_day = (
        invoice_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            invoice_count=Count("id"),
            total_sales=Sum("total_amount"),
        )
        .order_by("day")
    )

    highest_sales_day = (
        invoice_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total_sales=Sum("total_amount"))
        .order_by("-total_sales")
        .first()
    )

    sales_by_order_type = (
        invoice_qs.filter(order__isnull=False)
        .values(order_type=F("order__order_type"))
        .annotate(
            total_orders=Count("id"),
            total_sales=Sum("total_amount"),
        )
        .order_by("-total_sales")
    )

    table_wise_sales = (
        invoice_qs.filter(table__isnull=False)
        .values(table_name=F("table__name"))
        .annotate(
            total_orders=Count("id"),
            total_sales=Sum("total_amount"),
        )
        .order_by("-total_sales")[:10]
    )

    payment_summary = (
        payment_qs.values("payment_method")
        .annotate(
            total_count=Count("id"),
            total_amount=Sum("amount"),
        )
        .order_by("-total_amount")
    )

    context = {
        "today_sales": today_sales,
        "month_sales": month_sales,
        "completed_orders": completed_orders,
        "avg_order_value": avg_order_value,
        "highest_sales_day": highest_sales_day,
        "best_selling_items": best_selling_items,
        "sales_by_order_type": sales_by_order_type,
        "payment_summary": payment_summary,
        "table_wise_sales": table_wise_sales,
        "sales_by_day": sales_by_day,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "restaurant/reports.html", context)