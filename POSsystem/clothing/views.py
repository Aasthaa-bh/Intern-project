from functools import wraps

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum, Value, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from pos.models import Item, ItemVariant, Purchase, PurchaseItem, StockMovement, Supplier


def _get_request_business(request):
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False) and getattr(user, "business_id", None):
        return user.business
    return None


def _filter_by_business(queryset, business):
    if business is None:
        return queryset
    return queryset.filter(business=business)


def inventory_access_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        user_role = getattr(user, "role", None)
        if user.is_staff or user_role in {"OWNER", "SUPERADMIN"}:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You do not have permission to access the clothing inventory dashboard.")

    return _wrapped


@inventory_access_required
def inventory_dashboard(request):
    business = _get_request_business(request)

    products_qs = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT"),
        business,
    )

    variants_qs = _filter_by_business(
        ItemVariant.objects.filter(item__item_type="PRODUCT"),
        business,
    )

    total_products = products_qs.count()
    total_variants = variants_qs.count()
    total_skus = total_products + total_variants

    low_stock_items = products_qs.filter(stock_qty__lte=F("min_stock_qty"))
    low_stock_variants = variants_qs.filter(stock_qty__lte=F("min_stock_qty"))
    low_stock_count = low_stock_items.count() + low_stock_variants.count()

    recent_movements = (
        _filter_by_business(
            StockMovement.objects.select_related("item", "variant"),
            business,
        )
        .order_by("-created_at")[:10]
    )

    pending_purchase_count = _filter_by_business(
        Purchase.objects.filter(status="DRAFT"),
        business,
    ).count()

    context = {
        "total_products": total_products,
        "total_variants": total_variants,
        "total_skus": total_skus,
        "low_stock_count": low_stock_count,
        "pending_purchase_count": pending_purchase_count,
        "recent_movements": recent_movements,
    }
    return render(request, "clothing/inventory_dashboard.html", context)


@inventory_access_required
def product_list(request):
    business = _get_request_business(request)

    products = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT").select_related("category", "brand"),
        business,
    )

    products = products.annotate(
        variant_count=Count("variants", distinct=True),
        variants_stock=Coalesce(Sum("variants__stock_qty"), Value(0)),
    ).annotate(
        total_stock=ExpressionWrapper(
            F("stock_qty") + F("variants_stock"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    context = {
        "products": products.order_by("name"),
    }
    return render(request, "clothing/product_list.html", context)


@inventory_access_required
def product_detail(request, product_id):
    business = _get_request_business(request)

    base_qs = Item.objects.filter(item_type="PRODUCT").select_related("category", "brand", "clothing")
    if business is not None:
        base_qs = base_qs.filter(business=business)

    product = get_object_or_404(base_qs, id=product_id)

    variants = (
        ItemVariant.objects.filter(item=product)
        .select_related("clothing_detail__size", "clothing_detail__color")
        .order_by("name")
    )

    context = {
        "product": product,
        "variants": variants,
    }
    return render(request, "clothing/product_detail.html", context)


@inventory_access_required
def stock_movement_list(request):
    business = _get_request_business(request)
    movement_type = (request.GET.get("type") or "").strip().upper()

    movements = _filter_by_business(
        StockMovement.objects.select_related("item", "variant"),
        business,
    )

    movement_types = [choice[0] for choice in StockMovement.MOVEMENT_TYPE]
    if movement_type in movement_types:
        movements = movements.filter(movement_type=movement_type)
    else:
        movement_type = ""

    context = {
        "movements": movements.order_by("-created_at")[:200],
        "movement_type": movement_type,
        "movement_type_choices": StockMovement.MOVEMENT_TYPE,
    }
    return render(request, "clothing/stock_movements.html", context)


@inventory_access_required
def purchase_list(request):
    business = _get_request_business(request)
    purchases = _filter_by_business(
        Purchase.objects.select_related("supplier"),
        business,
    ).order_by("-created_at")

    context = {
        "purchases": purchases,
    }
    return render(request, "clothing/purchase_list.html", context)


@inventory_access_required
def purchase_detail(request, purchase_id):
    business = _get_request_business(request)

    base_qs = Purchase.objects.select_related("supplier")
    if business is not None:
        base_qs = base_qs.filter(business=business)

    purchase = get_object_or_404(base_qs, id=purchase_id)

    items = (
        PurchaseItem.objects.filter(purchase=purchase)
        .select_related("item", "variant")
        .order_by("id")
    )

    context = {
        "purchase": purchase,
        "items": items,
    }
    return render(request, "clothing/purchase_detail.html", context)


@inventory_access_required
def supplier_list(request):
    business = _get_request_business(request)
    suppliers = _filter_by_business(
        Supplier.objects.all(),
        business,
    ).order_by("name")

    context = {
        "suppliers": suppliers,
    }
    return render(request, "clothing/supplier_list.html", context)


@inventory_access_required
def low_stock_alert(request):
    business = _get_request_business(request)

    low_stock_items = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT", stock_qty__lte=F("min_stock_qty")),
        business,
    ).order_by("name")

    low_stock_variants = _filter_by_business(
        ItemVariant.objects.filter(item__item_type="PRODUCT", stock_qty__lte=F("min_stock_qty")),
        business,
    ).select_related("item").order_by("item__name", "name")

    context = {
        "low_stock_items": low_stock_items,
        "low_stock_variants": low_stock_variants,
    }
    return render(request, "clothing/low_stock.html", context)

