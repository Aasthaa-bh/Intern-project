from functools import wraps
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection
from django.db import transaction
from django.db.models import Count, F, Sum, Value, DecimalField, ExpressionWrapper, IntegerField, Case, When, Q, Max
from django.db.models.functions import Coalesce
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from pos.inventory_services import create_adjustment, recalculate_purchase_totals, receive_purchase_lines
from pos.models import Category, Item, ItemVariant, Purchase, PurchaseItem, StockMovement, Supplier
from .forms import (
    ClothingProductForm,
    ClothingPurchaseForm,
    ClothingPurchaseItemFormSet,
    ClothingStockAdjustmentForm,
    ClothingSupplierForm,
    ClothingVariantForm,
)
from .models import ClothingItem, ClothingVariantDetail


_TABLE_COLUMNS = {}


def _get_table_columns(table_name):
    if table_name in _TABLE_COLUMNS:
        return _TABLE_COLUMNS[table_name]
    try:
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table_name)
            }
    except Exception:
        columns = set()
    _TABLE_COLUMNS[table_name] = columns
    return columns


def _model_table_ok(model):
    table_name = model._meta.db_table
    columns = _get_table_columns(table_name)
    required = {field.column for field in model._meta.local_fields}
    return required.issubset(columns)


def _get_request_business(request):
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False) and getattr(user, "business_id", None):
        return user.business
    return None


def _filter_by_business(queryset, business):
    if business is None:
        return queryset
    return queryset.filter(business=business)


def _build_purchase_formset(data=None, instance=None, business=None):
    kwargs = {}
    if data is not None:
        kwargs["data"] = data
    if instance is not None:
        kwargs["instance"] = instance
    return ClothingPurchaseItemFormSet(form_kwargs={"business": business}, **kwargs)


def _product_has_variants(product):
    return bool(product and getattr(product, "pk", None) and product.variants.exists())


def _disable_parent_stock_tracking(product):
    if not product:
        return

    updates = []
    if product.track_stock:
        product.track_stock = False
        updates.append("track_stock")
    if (product.stock_qty or Decimal("0")) != Decimal("0"):
        product.stock_qty = Decimal("0")
        updates.append("stock_qty")
    if (product.min_stock_qty or Decimal("0")) != Decimal("0"):
        product.min_stock_qty = Decimal("0")
        updates.append("min_stock_qty")

    if updates:
        updates.append("updated_at")
        product.save(update_fields=updates)


def _variant_snapshot_name(variant):
    if not variant:
        return ""

    detail = getattr(variant, "clothing_detail", None)
    parts = []

    if detail and getattr(detail, "color_id", None):
        parts.append(detail.color.name)
    if detail and getattr(detail, "size_id", None):
        parts.append(detail.size.name)

    if parts:
        return " / ".join(parts)
    return variant.name or ""


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

    variants_enabled = _model_table_ok(ItemVariant)
    if variants_enabled:
        variants_qs = _filter_by_business(
            ItemVariant.objects.filter(item__item_type="PRODUCT"),
            business,
        )
    else:
        variants_qs = ItemVariant.objects.none()

    total_products = products_qs.count()
    total_variants = variants_qs.count()
    total_skus = total_products + total_variants

    low_stock_items = products_qs.filter(stock_qty__lte=F("min_stock_qty"), variants__isnull=True)
    if variants_enabled:
        low_stock_variants = variants_qs.filter(stock_qty__lte=F("min_stock_qty"))
        low_stock_count = low_stock_items.count() + low_stock_variants.count()
    else:
        low_stock_variants = ItemVariant.objects.none()
        low_stock_count = low_stock_items.count()

    if _model_table_ok(StockMovement):
        recent_movements = (
            _filter_by_business(
                StockMovement.objects.select_related("item", "variant"),
                business,
            )
            .order_by("-created_at")[:10]
        )
    else:
        recent_movements = []

    if _model_table_ok(Purchase):
        pending_purchase_count = _filter_by_business(
            Purchase.objects.filter(status="DRAFT"),
            business,
        ).count()
    else:
        pending_purchase_count = 0

    context = {
        "total_products": total_products,
        "total_variants": total_variants,
        "total_skus": total_skus,
        "low_stock_count": low_stock_count,
        "pending_purchase_count": pending_purchase_count,
        "recent_movements": recent_movements,
        "variants_enabled": variants_enabled,
    }
    return render(request, "clothing/inventory_dashboard.html", context)


@inventory_access_required
def product_list(request):
    business = _get_request_business(request)
    search_query = (request.GET.get("q") or "").strip()
    category_id = (request.GET.get("category") or "").strip()

    products = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT").select_related("category", "brand"),
        business,
    )

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    if _model_table_ok(ItemVariant):
        products = products.annotate(
            variant_count=Count("variants", distinct=True),
            variants_stock=Coalesce(
                Sum("variants__stock_qty"),
                Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
        ).annotate(
            total_stock=Case(
                When(variant_count__gt=0, then=F("variants_stock")),
                default=F("stock_qty"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    else:
        products = products.annotate(
            variant_count=Value(0, output_field=IntegerField()),
            total_stock=ExpressionWrapper(
                F("stock_qty"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

    categories = _filter_by_business(
        Category.objects.filter(item__item_type="PRODUCT", is_active=True),
        business,
    ).distinct().order_by("name")

    context = {
        "products": products.order_by("name"),
        "categories": categories,
        "selected_category": category_id,
        "search_query": search_query,
    }
    return render(request, "clothing/product_list.html", context)


@inventory_access_required
def product_create(request):
    business = _get_request_business(request)
    if business is None:
        return HttpResponseForbidden("Business context is required for product creation.")

    if request.method == "POST":
        form = ClothingProductForm(request.POST, business=business)
        if form.is_valid():
            product = form.save(commit=False)
            product.business = business
            product.item_type = "PRODUCT"
            product.save()
            if _product_has_variants(product):
                _disable_parent_stock_tracking(product)

            clothing_item, _ = ClothingItem.objects.get_or_create(item=product)
            clothing_item.gender = form.cleaned_data.get("gender") or clothing_item.gender
            clothing_item.material = form.cleaned_data.get("material", "")
            clothing_item.fit = form.cleaned_data.get("fit", "")
            clothing_item.care_note = form.cleaned_data.get("care_note", "")
            clothing_item.save()

            messages.success(request, "Product created successfully.")
            return redirect("clothing_product_detail", product_id=product.id)
    else:
        form = ClothingProductForm(business=business)

    return render(request, "clothing/product_form.html", {"form": form, "mode": "create"})


@inventory_access_required
def product_edit(request, product_id):
    business = _get_request_business(request)
    base_qs = Item.objects.filter(item_type="PRODUCT")
    if business is not None:
        base_qs = base_qs.filter(business=business)
    product = get_object_or_404(base_qs, id=product_id)

    if request.method == "POST":
        form = ClothingProductForm(request.POST, instance=product, business=business)
        if form.is_valid():
            product = form.save()
            if _product_has_variants(product):
                _disable_parent_stock_tracking(product)
            clothing_item, _ = ClothingItem.objects.get_or_create(item=product)
            clothing_item.gender = form.cleaned_data.get("gender") or clothing_item.gender
            clothing_item.material = form.cleaned_data.get("material", "")
            clothing_item.fit = form.cleaned_data.get("fit", "")
            clothing_item.care_note = form.cleaned_data.get("care_note", "")
            clothing_item.save()
            messages.success(request, "Product updated successfully.")
            return redirect("clothing_product_detail", product_id=product.id)
    else:
        form = ClothingProductForm(instance=product, business=business)

    return render(
        request,
        "clothing/product_form.html",
        {"form": form, "mode": "edit", "product": product},
    )


@inventory_access_required
def product_detail(request, product_id):
    business = _get_request_business(request)

    base_qs = Item.objects.filter(item_type="PRODUCT").select_related("category", "brand", "clothing")
    if business is not None:
        base_qs = base_qs.filter(business=business)

    product = get_object_or_404(base_qs, id=product_id)

    if _model_table_ok(ItemVariant):
        variants = (
            ItemVariant.objects.filter(item=product)
            .select_related("clothing_detail__size", "clothing_detail__color")
            .order_by("name")
        )
    else:
        variants = []

    context = {
        "product": product,
        "variants": variants,
    }
    return render(request, "clothing/product_detail.html", context)


@inventory_access_required
def variant_create(request, product_id):
    business = _get_request_business(request)
    base_qs = Item.objects.filter(item_type="PRODUCT")
    if business is not None:
        base_qs = base_qs.filter(business=business)
    product = get_object_or_404(base_qs, id=product_id)

    if request.method == "POST":
        form = ClothingVariantForm(request.POST, business=business, product=product)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.item = product
            variant.business = product.business
            variant.save()
            _disable_parent_stock_tracking(product)

            detail, _ = ClothingVariantDetail.objects.get_or_create(variant=variant)
            detail.size = form.cleaned_data.get("size")
            detail.color = form.cleaned_data.get("color")
            detail.save()

            messages.success(request, "Variant added successfully.")
            return redirect("clothing_product_detail", product_id=product.id)
    else:
        form = ClothingVariantForm(business=business, product=product)

    return render(
        request,
        "clothing/variant_form.html",
        {"form": form, "product": product, "mode": "create"},
    )


@inventory_access_required
def variant_edit(request, product_id, variant_id):
    business = _get_request_business(request)

    product_qs = Item.objects.filter(item_type="PRODUCT")
    if business is not None:
        product_qs = product_qs.filter(business=business)
    product = get_object_or_404(product_qs, id=product_id)

    variant_qs = ItemVariant.objects.filter(item=product)
    if business is not None:
        variant_qs = variant_qs.filter(business=business)
    variant = get_object_or_404(variant_qs, id=variant_id)

    if request.method == "POST":
        form = ClothingVariantForm(request.POST, instance=variant, business=business, product=product)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.item = product
            variant.business = product.business
            variant.save()
            _disable_parent_stock_tracking(product)

            detail, _ = ClothingVariantDetail.objects.get_or_create(variant=variant)
            detail.size = form.cleaned_data.get("size")
            detail.color = form.cleaned_data.get("color")
            detail.save()

            messages.success(request, "Variant updated successfully.")
            return redirect("clothing_product_detail", product_id=product.id)
    else:
        form = ClothingVariantForm(instance=variant, business=business, product=product)

    return render(
        request,
        "clothing/variant_form.html",
        {"form": form, "product": product, "variant": variant, "mode": "edit"},
    )


@inventory_access_required
def variant_delete(request, product_id, variant_id):
    business = _get_request_business(request)

    product_qs = Item.objects.filter(item_type="PRODUCT")
    if business is not None:
        product_qs = product_qs.filter(business=business)
    product = get_object_or_404(product_qs, id=product_id)

    variant_qs = ItemVariant.objects.filter(item=product)
    if business is not None:
        variant_qs = variant_qs.filter(business=business)
    variant = get_object_or_404(variant_qs, id=variant_id)

    if request.method == "POST":
        try:
            variant.delete()
            messages.success(request, "Variant deleted successfully.")
        except ProtectedError:
            messages.error(request, "Variant cannot be deleted because it is used in transactions.")
        return redirect("clothing_product_detail", product_id=product.id)

    return render(
        request,
        "clothing/variant_delete.html",
        {"product": product, "variant": variant},
    )


@inventory_access_required
def stock_movement_list(request):
    business = _get_request_business(request)
    movement_type = (request.GET.get("type") or "").strip().upper()
    movement_date = (request.GET.get("date") or "").strip()

    if not _model_table_ok(StockMovement):
        return HttpResponseForbidden("Stock movement table schema is out of date. Run migrations.")

    movements = _filter_by_business(
        StockMovement.objects.select_related("item", "variant"),
        business,
    )

    movement_types = [choice[0] for choice in StockMovement.MOVEMENT_TYPE]
    if movement_type in movement_types:
        movements = movements.filter(movement_type=movement_type)
    else:
        movement_type = ""

    if movement_date:
        movements = movements.filter(created_at__date=movement_date)

    context = {
        "movements": movements.order_by("-created_at")[:200],
        "movement_type": movement_type,
        "movement_date": movement_date,
        "movement_type_choices": StockMovement.MOVEMENT_TYPE,
    }
    return render(request, "clothing/stock_movements.html", context)


@inventory_access_required
def purchase_list(request):
    business = _get_request_business(request)
    if not _model_table_ok(Purchase):
        return HttpResponseForbidden("Purchase table schema is out of date. Run migrations.")
    purchases = _filter_by_business(
        Purchase.objects.select_related("supplier"),
        business,
    ).order_by("-created_at")

    context = {
        "purchases": purchases,
    }
    return render(request, "clothing/purchase_list.html", context)


@inventory_access_required
def purchase_create(request):
    business = _get_request_business(request)
    if business is None:
        return HttpResponseForbidden("Business context is required for purchase creation.")

    if request.method == "POST":
        form = ClothingPurchaseForm(request.POST, business=business)
        formset = _build_purchase_formset(data=request.POST, business=business)

        if form.is_valid() and formset.is_valid():
            purchase = form.save(commit=False)
            purchase.business = business
            purchase.created_by = request.user
            purchase.status = "DRAFT"
            purchase.save()

            formset.instance = purchase
            lines = formset.save(commit=False)

            for deleted_obj in formset.deleted_objects:
                deleted_obj.delete()

            for line in lines:
                line.item_name_snapshot = line.item.name
                line.variant_name_snapshot = _variant_snapshot_name(line.variant)
                line.sku_snapshot = line.variant.sku if line.variant else (line.item.sku or "")
                line.expected_quantity = line.quantity
                line.received_quantity = Decimal("0")
                line.line_total = (line.quantity or Decimal("0")) * (line.unit_cost or Decimal("0"))
                line.save()

            if purchase.items.count() == 0:
                purchase.delete()
                messages.error(request, "Please add at least one purchase line.")
            else:
                recalculate_purchase_totals(purchase)
                messages.success(request, "Purchase created successfully.")
                return redirect("clothing_purchase_detail", purchase_id=purchase.id)
    else:
        form = ClothingPurchaseForm(business=business)
        formset = _build_purchase_formset(business=business)

    return render(
        request,
        "clothing/purchase_form.html",
        {"form": form, "formset": formset, "mode": "create"},
    )


@inventory_access_required
def purchase_detail(request, purchase_id):
    business = _get_request_business(request)

    if not _model_table_ok(Purchase) or not _model_table_ok(PurchaseItem):
        return HttpResponseForbidden("Purchase tables schema is out of date. Run migrations.")

    base_qs = Purchase.objects.select_related("supplier")
    if business is not None:
        base_qs = base_qs.filter(business=business)

    purchase = get_object_or_404(base_qs, id=purchase_id)

    items = (
        PurchaseItem.objects.filter(purchase=purchase)
        .select_related("item", "variant")
        .order_by("id")
    )

    context = {"purchase": purchase, "items": items}
    return render(request, "clothing/purchase_detail.html", context)


@inventory_access_required
def purchase_edit(request, purchase_id):
    business = _get_request_business(request)

    if not _model_table_ok(Purchase) or not _model_table_ok(PurchaseItem):
        return HttpResponseForbidden("Purchase tables schema is out of date. Run migrations.")

    base_qs = Purchase.objects.select_related("supplier")
    if business is not None:
        base_qs = base_qs.filter(business=business)

    purchase = get_object_or_404(base_qs, id=purchase_id)

    if purchase.status == "RECEIVED":
        messages.error(request, "Received purchases cannot be edited.")
        return redirect("clothing_purchase_detail", purchase_id=purchase.id)

    if request.method == "POST":
        form = ClothingPurchaseForm(request.POST, instance=purchase, business=business)
        formset = _build_purchase_formset(data=request.POST, instance=purchase, business=business)

        if form.is_valid() and formset.is_valid():
            purchase = form.save(commit=False)
            purchase.status = "DRAFT"
            purchase.save()

            formset.instance = purchase
            lines = formset.save(commit=False)

            for deleted_obj in formset.deleted_objects:
                deleted_obj.delete()

            for line in lines:
                line.item_name_snapshot = line.item.name
                line.variant_name_snapshot = _variant_snapshot_name(line.variant)
                line.sku_snapshot = line.variant.sku if line.variant else (line.item.sku or "")
                if not line.received_quantity:
                    line.received_quantity = Decimal("0")
                line.expected_quantity = line.quantity
                line.line_total = (line.quantity or Decimal("0")) * (line.unit_cost or Decimal("0"))
                line.save()

            recalculate_purchase_totals(purchase)
            messages.success(request, "Purchase updated successfully.")
            return redirect("clothing_purchase_detail", purchase_id=purchase.id)
    else:
        form = ClothingPurchaseForm(instance=purchase, business=business)
        formset = _build_purchase_formset(instance=purchase, business=business)

    return render(
        request,
        "clothing/purchase_form.html",
        {"form": form, "formset": formset, "mode": "edit", "purchase": purchase},
    )


@inventory_access_required
@transaction.atomic
def purchase_receive(request, purchase_id):
    business = _get_request_business(request)

    if not _model_table_ok(Purchase) or not _model_table_ok(PurchaseItem):
        return HttpResponseForbidden("Purchase tables schema is out of date. Run migrations.")

    base_qs = Purchase.objects.select_for_update()
    if business is not None:
        base_qs = base_qs.filter(business=business)

    purchase = get_object_or_404(base_qs, id=purchase_id)

    if purchase.status == "CANCELLED":
        messages.error(request, "Cancelled purchase cannot be received.")
        return redirect("clothing_purchase_detail", purchase_id=purchase.id)

    lines = list(
        PurchaseItem.objects.filter(purchase=purchase)
        .select_related("item", "variant")
        .order_by("id")
    )
    if not lines:
        messages.error(request, "Purchase has no items to receive.")
        return redirect("clothing_purchase_detail", purchase_id=purchase.id)

    if request.method == "POST":
        received_map = {}
        try:
            for line in lines:
                remaining = (line.quantity or Decimal("0")) - (line.received_quantity or Decimal("0"))
                raw = request.POST.get(f"received_{line.id}", "").strip()
                if not raw:
                    continue

                qty = Decimal(raw)
                if qty < 0:
                    raise ValueError("Received quantity cannot be negative.")
                if qty > remaining:
                    raise ValueError(f"Received quantity exceeds remaining for {line.item_name_snapshot}.")

                received_map[line.id] = qty
        except (InvalidOperation, ValueError) as exc:
            messages.error(request, str(exc))
            return redirect("clothing_purchase_receive", purchase_id=purchase.id)

        if not received_map:
            messages.error(request, "Enter at least one received quantity.")
            return redirect("clothing_purchase_receive", purchase_id=purchase.id)

        try:
            any_received, all_received = receive_purchase_lines(purchase, received_map, request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("clothing_purchase_receive", purchase_id=purchase.id)

        if any_received and all_received:
            messages.success(request, "Purchase fully received and stock updated.")
        elif any_received:
            messages.success(request, "Partial receive completed and stock updated.")
        else:
            messages.error(request, "No items were received.")

        return redirect("clothing_purchase_detail", purchase_id=purchase.id)

    return render(
        request,
        "clothing/purchase_receive.html",
        {"purchase": purchase, "items": lines},
    )


@inventory_access_required
def supplier_list(request):
    business = _get_request_business(request)
    search_query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "active").strip().lower()
    if not _model_table_ok(Supplier):
        return HttpResponseForbidden("Supplier table schema is out of date. Run migrations.")
    suppliers = _filter_by_business(
        Supplier.objects.all(),
        business,
    )

    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query)
            | Q(contact_person__icontains=search_query)
            | Q(phone_no__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(pan_vat_no__icontains=search_query)
        )

    if status == "active":
        suppliers = suppliers.filter(is_active=True)
    elif status == "inactive":
        suppliers = suppliers.filter(is_active=False)
    else:
        status = "all"

    suppliers = suppliers.annotate(
        total_purchases=Count("purchase", distinct=True),
        last_purchase_date=Max("purchase__purchase_date"),
        total_purchased=Coalesce(
            Sum("purchase__total_amount"),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
    ).order_by("name")

    context = {
        "suppliers": suppliers,
        "search_query": search_query,
        "status": status,
    }
    return render(request, "clothing/supplier_list.html", context)


@inventory_access_required
def supplier_create(request):
    business = _get_request_business(request)
    if business is None:
        return HttpResponseForbidden("Business context is required for supplier creation.")

    if request.method == "POST":
        form = ClothingSupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.business = business
            supplier.save()
            messages.success(request, "Supplier created successfully.")
            return redirect("clothing_supplier_list")
    else:
        form = ClothingSupplierForm()

    return render(
        request,
        "clothing/supplier_form.html",
        {"form": form, "mode": "create"},
    )


@inventory_access_required
def supplier_edit(request, supplier_id):
    business = _get_request_business(request)

    base_qs = Supplier.objects.all()
    if business is not None:
        base_qs = base_qs.filter(business=business)

    supplier = get_object_or_404(base_qs, id=supplier_id)

    if request.method == "POST":
        form = ClothingSupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier updated successfully.")
            return redirect("clothing_supplier_list")
    else:
        form = ClothingSupplierForm(instance=supplier)

    return render(
        request,
        "clothing/supplier_form.html",
        {"form": form, "mode": "edit", "supplier": supplier},
    )


@inventory_access_required
def supplier_delete(request, supplier_id):
    business = _get_request_business(request)

    base_qs = Supplier.objects.all()
    if business is not None:
        base_qs = base_qs.filter(business=business)

    supplier = get_object_or_404(base_qs, id=supplier_id)
    purchase_count = Purchase.objects.filter(supplier=supplier).count()

    if request.method == "POST":
        if purchase_count:
            if supplier.is_active:
                supplier.is_active = False
                supplier.save(update_fields=["is_active", "updated_at"])
                messages.success(request, "Supplier is used in purchases, so it was archived instead of deleted.")
            else:
                messages.info(request, "Supplier is already inactive and kept for purchase history.")
        else:
            try:
                supplier.delete()
                messages.success(request, "Supplier deleted successfully.")
            except ProtectedError:
                messages.error(request, "Supplier cannot be deleted because it is used in purchases.")
        return redirect("clothing_supplier_list")

    return render(
        request,
        "clothing/supplier_delete.html",
        {"supplier": supplier, "purchase_count": purchase_count},
    )


@inventory_access_required
def stock_adjustment_create(request):
    business = _get_request_business(request)
    if business is None:
        return HttpResponseForbidden("Business context is required for stock adjustment.")

    if request.method == "POST":
        form = ClothingStockAdjustmentForm(request.POST, business=business)
        if form.is_valid():
            try:
                create_adjustment(
                    business=business,
                    item=form.cleaned_data["item"],
                    variant=form.cleaned_data.get("variant"),
                    movement_type=form.cleaned_data["movement_type"],
                    quantity=form.cleaned_data["quantity"],
                    user=request.user,
                    note=form.cleaned_data.get("note", ""),
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Stock adjustment recorded successfully.")
                return redirect("clothing_stock_movements")
    else:
        form = ClothingStockAdjustmentForm(business=business)

    return render(request, "clothing/stock_adjustment_form.html", {"form": form})


@inventory_access_required
def low_stock_alert(request):
    business = _get_request_business(request)

    low_stock_items = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT", stock_qty__lte=F("min_stock_qty"), variants__isnull=True),
        business,
    ).order_by("name")

    if _model_table_ok(ItemVariant):
        low_stock_variants = _filter_by_business(
            ItemVariant.objects.filter(item__item_type="PRODUCT", stock_qty__lte=F("min_stock_qty")),
            business,
        ).select_related("item").order_by("item__name", "name")
    else:
        low_stock_variants = ItemVariant.objects.none()

    context = {
        "low_stock_items": low_stock_items,
        "low_stock_variants": low_stock_variants,
    }
    return render(request, "clothing/low_stock.html", context)

