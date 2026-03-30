from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from django import forms
from decimal import Decimal

from .models import Offer, OfferUsage
from pos.models import Item, Category
from core.decorators import business_required


# ==================== FORMS ====================

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ['offer_name', 'offer_type', 'description', 'discount_value', 
                  'start_date', 'end_date', 'product', 'category', 'minimum_purchase', 'status']
        widgets = {
            'offer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Dashain Sale'}),
            'offer_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_offer_type'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'minimum_purchase': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        if business:
            self.fields['product'].queryset = Item.objects.filter(business=business, is_active=True)
            self.fields['category'].queryset = Category.objects.filter(business=business, is_active=True)
        self.fields['product'].required = False
        self.fields['category'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        if offer_type == 'PRODUCT' and not cleaned_data.get('product'):
            self.add_error('product', 'Product is required for Product Wise Offer')
        if offer_type == 'CATEGORY' and not cleaned_data.get('category'):
            self.add_error('category', 'Category is required for Category Wise Offer')
        return cleaned_data


# ==================== VIEWS ====================

def offer_list(request):
    # Get first business if user not logged in
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    status_filter = request.GET.get('status', '')
    offer_type_filter = request.GET.get('offer_type', '')
    search = request.GET.get('search', '')
    
    offers = Offer.objects.filter(business=business)
    
    if status_filter:
        offers = offers.filter(status=status_filter)
    if offer_type_filter:
        offers = offers.filter(offer_type=offer_type_filter)
    if search:
        offers = offers.filter(Q(offer_name__icontains=search) | Q(description__icontains=search))
    
    # Auto-update expired offers
    today = timezone.now().date()
    offers.filter(status='ACTIVE', end_date__lt=today).update(status='EXPIRED')
    
    offers = offers.select_related('product', 'category', 'created_by')
    
    context = {
        'offers': offers,
        'active_count': offers.filter(status='ACTIVE').count(),
        'inactive_count': offers.filter(status='INACTIVE').count(),
        'expired_count': offers.filter(status='EXPIRED').count(),
        'status_filter': status_filter,
        'offer_type_filter': offer_type_filter,
        'search': search,
        'offer_types': Offer.OFFER_TYPE_CHOICES,
        'status_choices': Offer.STATUS_CHOICES,
    }
    return render(request, 'clothing/offer_list.html', context)


def offer_create(request):
    # Get first business if user not logged in
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    if request.method == 'POST':
        form = OfferForm(request.POST, business=business)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.business = business
            offer.created_by = request.user
            offer.save()
            messages.success(request, f'Offer "{offer.offer_name}" created successfully!')
            return redirect('clothing_offer_list')
    else:
        form = OfferForm(business=business)
    
    return render(request, 'clothing/offer_form.html', {
        'form': form, 'title': 'Create New Offer', 'button_text': 'Create Offer'
    })


def offer_edit(request, offer_id):
    # Get first business if user not logged in
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer, business=business)
        if form.is_valid():
            form.save()
            messages.success(request, f'Offer "{offer.offer_name}" updated successfully!')
            return redirect('clothing_offer_list')
    else:
        form = OfferForm(instance=offer, business=business)
    
    return render(request, 'clothing/offer_form.html', {
        'form': form, 'offer': offer, 'title': 'Edit Offer', 'button_text': 'Update Offer'
    })


def offer_delete(request, offer_id):
    # Get first business if user not logged in
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    if request.method == 'POST':
        offer_name = offer.offer_name
        offer.delete()
        messages.success(request, f'Offer "{offer_name}" deleted successfully!')
        return redirect('clothing_offer_list')
    
    return render(request, 'clothing/offer_confirm_delete.html', {'offer': offer})


def offer_detail(request, offer_id):
    # Get first business if user not logged in
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    usages = OfferUsage.objects.filter(offer=offer).select_related('order')
    
    context = {
        'offer': offer,
        'total_usage': usages.count(),
        'total_discount': usages.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00'),
        'recent_usages': usages.order_by('-applied_at')[:10],
    }
    return render(request, 'clothing/offer_detail.html', context)


def offer_toggle_status(request, offer_id):
    # Get first business if user not logged in
    from core.models import Business
    business = request.user.business if request.user.is_authenticated else Business.objects.first()
    offer = get_object_or_404(Offer, id=offer_id, business=business)
    
    if request.method == 'POST':
        if offer.status == 'ACTIVE':
            offer.status = 'INACTIVE'
            messages.success(request, f'Offer "{offer.offer_name}" deactivated.')
        elif offer.status == 'INACTIVE':
            offer.status = 'ACTIVE'
            messages.success(request, f'Offer "{offer.offer_name}" activated.')
        else:
            messages.error(request, 'Cannot toggle expired offer status.')
            return redirect('clothing_offer_list')
        offer.save()
    
    return redirect('clothing_offer_list')
from datetime import timedelta
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
from django.utils import timezone

from pos.inventory_services import create_adjustment, recalculate_purchase_totals, receive_purchase_lines
from pos.models import Brand, Category, Item, ItemVariant, OrderItem, Purchase, PurchaseItem, StockBatch, StockMovement, Supplier
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


def _purchase_variant_item_map(business):
    variants = _filter_by_business(ItemVariant.objects.all(), business).values_list("id", "item_id")
    return {str(variant_id): item_id for variant_id, item_id in variants}


def _product_delete_block_reasons(product):
    reasons = []
    variant_qs = ItemVariant.objects.filter(item=product)

    if PurchaseItem.objects.filter(item=product).exists():
        reasons.append("Used in purchase transactions")
    if OrderItem.objects.filter(item=product).exists():
        reasons.append("Used in sales transactions")
    if StockMovement.objects.filter(item=product).exists():
        reasons.append("Used in stock movement history")
    if StockBatch.objects.filter(item=product).exists():
        reasons.append("Used in FIFO batch history")

    if variant_qs.exists():
        if PurchaseItem.objects.filter(variant__in=variant_qs).exists():
            reasons.append("Variants used in purchase transactions")
        if OrderItem.objects.filter(variant__in=variant_qs).exists():
            reasons.append("Variants used in sales transactions")
        if StockMovement.objects.filter(variant__in=variant_qs).exists():
            reasons.append("Variants used in stock movement history")
        if StockBatch.objects.filter(variant__in=variant_qs).exists():
            reasons.append("Variants used in FIFO batch history")

    unique_reasons = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)
    return unique_reasons


def inventory_access_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # Allow access without login for demo purposes
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        user = request.user
        user_role = getattr(user, "role", None)
        if user.is_staff or user_role in {"OWNER", "SUPERADMIN"}:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You do not have permission to access the clothing inventory dashboard.")

    return _wrapped


@inventory_access_required
def inventory_dashboard(request):
    from .models import Offer, OfferUsage
    from django.utils import timezone
    from decimal import Decimal
    
    business = _get_request_business(request)
    period = (request.GET.get("period") or "week").strip().lower()
    if period not in {"today", "week", "month", "all"}:
        period = "week"

    today = timezone.localdate()
    if period == "today":
        date_from = today
        period_label = "Today"
    elif period == "week":
        date_from = today - timedelta(days=6)
        period_label = "Last 7 Days"
    elif period == "month":
        date_from = today.replace(day=1)
        period_label = "This Month"
    else:
        date_from = None
        period_label = "All Time"

    period_options = [
        ("today", "Today"),
        ("week", "Last 7 Days"),
        ("month", "This Month"),
        ("all", "All Time"),
    ]

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

    standalone_products = products_qs.annotate(
        variant_count=Count("variants", distinct=True),
    ).filter(variant_count=0)

    low_stock_items = standalone_products.filter(track_stock=True, stock_qty__lte=F("min_stock_qty"))
    if variants_enabled:
        low_stock_variants = variants_qs.filter(track_stock=True, stock_qty__lte=F("min_stock_qty"))
        low_stock_count = low_stock_items.count() + low_stock_variants.count()
    else:
        low_stock_variants = ItemVariant.objects.none()
        low_stock_count = low_stock_items.count()

    money_field = DecimalField(max_digits=14, decimal_places=2)
    zero_money = Value(Decimal("0.00"), output_field=money_field)

    standalone_stock_value = standalone_products.aggregate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("stock_qty") * Coalesce(F("cost_price"), zero_money),
                    output_field=money_field,
                )
            ),
            zero_money,
        )
    )["total"]

    if variants_enabled:
        variant_stock_value = variants_qs.aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("stock_qty") * Coalesce(F("cost_price"), zero_money),
                        output_field=money_field,
                    )
                ),
                zero_money,
            )
        )["total"]
    else:
        variant_stock_value = Decimal("0.00")

    total_stock_value = (standalone_stock_value or Decimal("0.00")) + (variant_stock_value or Decimal("0.00"))

    products_without_variants = products_qs.annotate(
        variant_count=Count("variants", distinct=True),
    ).filter(variant_count=0).count()

    tracked_standalone = standalone_products.filter(track_stock=True)
    tracked_variant_count = variants_qs.filter(track_stock=True).count() if variants_enabled else 0
    tracked_sku_count = tracked_standalone.count() + tracked_variant_count

    healthy_standalone_count = tracked_standalone.filter(stock_qty__gt=F("min_stock_qty")).count()
    healthy_variant_count = (
        variants_qs.filter(track_stock=True, stock_qty__gt=F("min_stock_qty")).count()
        if variants_enabled
        else 0
    )
    healthy_sku_count = healthy_standalone_count + healthy_variant_count
    inventory_health_pct = round((healthy_sku_count / tracked_sku_count) * 100, 1) if tracked_sku_count else 100.0

    if _model_table_ok(Purchase):
        pending_purchase_count = _filter_by_business(
            Purchase.objects.filter(status="DRAFT"),
            business,
        ).count()
        recent_purchases = _filter_by_business(
            Purchase.objects.select_related("supplier"),
            business,
        )
        if date_from is not None:
            recent_purchases = recent_purchases.filter(purchase_date__gte=date_from)
        recent_purchases = recent_purchases.order_by("-purchase_date", "-created_at")[:8]
    else:
        pending_purchase_count = 0
        recent_purchases = []

    needs_attention = [
        {
            "title": "Low stock items",
            "count": low_stock_count,
            "description": "Variants and standalone products below their minimum stock.",
            "url": "clothing_current_stock",
            "query": "?low_stock=1",
            "tone": "danger",
            "empty_label": "Stable",
        },
        {
            "title": "Draft purchases",
            "count": pending_purchase_count,
            "description": "Purchase orders waiting to be received into stock.",
            "url": "clothing_purchase_list",
            "query": "?status=DRAFT",
            "tone": "warning",
            "empty_label": "Clear",
        },
        {
            "title": "Products without variants",
            "count": products_without_variants,
            "description": "Products still managed without size or color variants.",
            "url": "clothing_product_list",
            "query": "",
            "tone": "info",
            "empty_label": "Covered",
        },
    ]

    if _model_table_ok(StockMovement):
        recent_movements = _filter_by_business(
            StockMovement.objects.select_related("item", "variant"),
            business,
        )
        if date_from is not None:
            recent_movements = recent_movements.filter(created_at__date__gte=date_from)
        recent_movements = recent_movements.order_by("-created_at")[:10]
    else:
        recent_movements = []

    # Get products with variant count and total stock
    products_with_stats = []
    for product in products_qs.select_related('category')[:20]:  # Limit to 20 products
        variant_count = variants_qs.filter(item=product).count() if variants_enabled else 0
        total_stock = product.stock_qty
        if variants_enabled:
            variant_stock = variants_qs.filter(item=product).aggregate(total=Sum('stock_qty'))['total'] or 0
            total_stock += variant_stock
        
        products_with_stats.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'category': product.category,
            'variant_count': variant_count,
            'total_stock': total_stock,
            'price': product.price,
        })

    # Offer Statistics
    offer_stats = {}
    try:
        today = timezone.now().date()
        total_offers = Offer.objects.filter(business=business).count()
        active_offers = Offer.objects.filter(business=business, status='ACTIVE').count()
        
        usage_stats = OfferUsage.objects.filter(offer__business=business).aggregate(
            total_usage=Count('id'),
            total_discount=Sum('discount_amount')
        )
        
        offer_stats = {
            'total_offers': total_offers,
            'active_offers': active_offers,
            'total_usage': usage_stats['total_usage'] or 0,
            'total_discount': usage_stats['total_discount'] or Decimal('0.00'),
        }
    except:
        offer_stats = {
            'total_offers': 0,
            'active_offers': 0,
            'total_usage': 0,
            'total_discount': Decimal('0.00'),
        }

    context = {
        "period": period,
        "period_label": period_label,
        "period_options": period_options,
        "total_products": total_products,
        "total_variants": total_variants,
        "total_skus": total_skus,
        "total_stock_value": total_stock_value,
        "inventory_health_pct": inventory_health_pct,
        "healthy_sku_count": healthy_sku_count,
        "tracked_sku_count": tracked_sku_count,
        "low_stock_count": low_stock_count,
        "pending_purchase_count": pending_purchase_count,
        "needs_attention": needs_attention,
        "recent_purchases": recent_purchases,
        "recent_movements": recent_movements,
        "variants_enabled": variants_enabled,
        "products": products_with_stats,
        "offer_stats": offer_stats,
    }
    return render(request, "clothing/inventory_dashboard.html", context)


@inventory_access_required
def product_list(request):
    business = _get_request_business(request)
    search_query = (request.GET.get("q") or "").strip()
    category_id = (request.GET.get("category") or "").strip()
    brand_id = (request.GET.get("brand") or "").strip()
    gender = (request.GET.get("gender") or "").strip().upper()

    products = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT").select_related("category", "brand"),
        business,
    )

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    if brand_id:
        products = products.filter(brand_id=brand_id)

    valid_genders = {choice[0] for choice in ClothingItem.GENDER}
    if gender in valid_genders:
        products = products.filter(clothing__gender=gender)
    else:
        gender = ""

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

    brands = _filter_by_business(
        Brand.objects.filter(item__item_type="PRODUCT", is_active=True),
        business,
    ).distinct().order_by("name")

    context = {
        "products": products.order_by("name"),
        "categories": categories,
        "brands": brands,
        "genders": ClothingItem.GENDER,
        "selected_category": category_id,
        "selected_brand": brand_id,
        "selected_gender": gender,
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
    active_tab = (request.GET.get("tab") or "overview").strip().lower()
    if active_tab not in {"overview", "variants", "purchases"}:
        active_tab = "overview"

    base_qs = Item.objects.filter(item_type="PRODUCT").select_related("category", "brand", "clothing")
    if business is not None:
        base_qs = base_qs.filter(business=business)

    product = get_object_or_404(base_qs, id=product_id)

    if _model_table_ok(ItemVariant):
        variants = list(
            ItemVariant.objects.filter(item=product)
            .select_related("clothing_detail__size", "clothing_detail__color")
            .order_by("name")
        )
    else:
        variants = []
    variant_ids = [variant.id for variant in variants]

    if variants and _model_table_ok(StockBatch):
        batch_history_map = {variant_id: [] for variant_id in variant_ids}
        batch_summary_map = {
            variant_id: {
                "total_layers": 0,
                "open_layers": 0,
                "open_qty": Decimal("0"),
                "open_value": Decimal("0"),
            }
            for variant_id in variant_ids
        }

        batches = (
            StockBatch.objects.filter(item=product, variant_id__in=variant_ids)
            .select_related("purchase", "purchase_item", "variant")
            .order_by("variant_id", "-received_at", "-id")
        )

        for batch in batches:
            quantity = batch.quantity or Decimal("0")
            remaining_qty = batch.remaining_qty or Decimal("0")
            consumed_qty = quantity - remaining_qty
            summary = batch_summary_map[batch.variant_id]
            summary["total_layers"] += 1
            if remaining_qty > 0:
                summary["open_layers"] += 1
                summary["open_qty"] += remaining_qty
                summary["open_value"] += remaining_qty * (batch.unit_cost or Decimal("0"))

            batch_history_map[batch.variant_id].append(
                {
                    "id": batch.id,
                    "received_at": batch.received_at,
                    "purchase_no": batch.purchase.purchase_no if batch.purchase_id else "-",
                    "unit_cost": batch.unit_cost,
                    "selling_price": batch.purchase_item.selling_price if batch.purchase_item_id else None,
                    "quantity": quantity,
                    "remaining_qty": remaining_qty,
                    "consumed_qty": consumed_qty,
                    "is_open": remaining_qty > 0,
                }
            )

        for variant in variants:
            variant.batch_history = batch_history_map.get(variant.id, [])
            variant.batch_summary = batch_summary_map.get(
                variant.id,
                {
                    "total_layers": 0,
                    "open_layers": 0,
                    "open_qty": Decimal("0"),
                    "open_value": Decimal("0"),
                },
            )
    else:
        for variant in variants:
            variant.batch_history = []
            variant.batch_summary = {
                "total_layers": 0,
                "open_layers": 0,
                "open_qty": Decimal("0"),
                "open_value": Decimal("0"),
            }

    purchase_lines = []
    purchase_summary = {
        "purchase_count": 0,
        "ordered_qty": Decimal("0"),
        "received_qty": Decimal("0"),
        "total_amount": Decimal("0"),
    }

    if _model_table_ok(PurchaseItem):
        purchase_filters = Q(item=product)
        if variant_ids:
            purchase_filters |= Q(variant_id__in=variant_ids)

        purchase_qs = PurchaseItem.objects.filter(purchase_filters).select_related(
            "purchase",
            "purchase__supplier",
            "variant",
        )

        if business is not None:
            purchase_qs = purchase_qs.filter(purchase__business=business)

        purchase_lines = list(
            purchase_qs.order_by("-purchase__purchase_date", "-purchase_id", "-id")
        )

        purchase_summary = purchase_qs.aggregate(
            ordered_qty=Coalesce(
                Sum("quantity"),
                Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
            received_qty=Coalesce(
                Sum("received_quantity"),
                Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
            total_amount=Coalesce(
                Sum("line_total"),
                Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2)),
            ),
        )
        purchase_summary["purchase_count"] = purchase_qs.values("purchase_id").distinct().count()

    context = {
        "product": product,
        "variants": variants,
        "active_tab": active_tab,
        "purchase_lines": purchase_lines,
        "purchase_summary": purchase_summary,
    }
    return render(request, "clothing/product_detail.html", context)


@inventory_access_required
def product_delete(request, product_id):
    business = _get_request_business(request)
    base_qs = Item.objects.filter(item_type="PRODUCT")
    if business is not None:
        base_qs = base_qs.filter(business=business)
    product = get_object_or_404(base_qs, id=product_id)

    block_reasons = _product_delete_block_reasons(product)
    can_delete = not block_reasons

    if request.method == "POST":
        if not can_delete:
            messages.error(
                request,
                "Product cannot be deleted because it has linked transactions or variants in use. Use Inactive instead.",
            )
            return redirect("clothing_product_detail", product_id=product.id)

        try:
            product.delete()
            messages.success(request, "Product deleted successfully.")
            return redirect("clothing_product_list")
        except ProtectedError:
            messages.error(
                request,
                "Product cannot be deleted because it has linked transactions. Use Inactive instead.",
            )
            return redirect("clothing_product_detail", product_id=product.id)

    return render(
        request,
        "clothing/product_delete.html",
        {
            "product": product,
            "can_delete": can_delete,
            "block_reasons": block_reasons,
        },
    )


@inventory_access_required
def variant_list(request):
    business = _get_request_business(request)
    search_query = (request.GET.get("q") or "").strip()
    product_id = (request.GET.get("product") or "").strip()

    if _model_table_ok(ItemVariant):
        variants = _filter_by_business(
            ItemVariant.objects.filter(item__item_type="PRODUCT").select_related(
                "item",
                "clothing_detail__size",
                "clothing_detail__color",
            ),
            business,
        )
    else:
        variants = ItemVariant.objects.none()

    if search_query:
        variants = variants.filter(
            Q(name__icontains=search_query)
            | Q(sku__icontains=search_query)
            | Q(barcode__icontains=search_query)
            | Q(item__name__icontains=search_query)
            | Q(clothing_detail__size__name__icontains=search_query)
            | Q(clothing_detail__color__name__icontains=search_query)
        )

    if product_id:
        variants = variants.filter(item_id=product_id)

    products = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT"),
        business,
    ).order_by("name")

    context = {
        "variants": variants.order_by("item__name", "name"),
        "products": products,
        "selected_product": product_id,
        "search_query": search_query,
    }
    return render(request, "clothing/variant_list.html", context)


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
def variant_barcode_label(request, product_id, variant_id):
    business = _get_request_business(request)

    product_qs = Item.objects.filter(item_type="PRODUCT")
    if business is not None:
        product_qs = product_qs.filter(business=business)
    product = get_object_or_404(product_qs, id=product_id)

    variant_qs = ItemVariant.objects.filter(item=product).select_related(
        "item",
        "clothing_detail__size",
        "clothing_detail__color",
    )
    if business is not None:
        variant_qs = variant_qs.filter(business=business)
    variant = get_object_or_404(variant_qs, id=variant_id)

    # Safety: generate barcode if missing
    if not variant.barcode:
        variant.save()

    return render(
        request,
        "clothing/barcode_label.html",
        {
            "product": product,
            "variant": variant,
        },
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
def current_stock(request):
    business = _get_request_business(request)
    search_query = (request.GET.get("q") or "").strip()
    category_id = (request.GET.get("category") or "").strip()
    product_id = (request.GET.get("product") or "").strip()
    low_stock_only = (request.GET.get("low_stock") or "").strip() == "1"

    products = _filter_by_business(
        Item.objects.filter(item_type="PRODUCT").select_related("category"),
        business,
    )

    categories = _filter_by_business(
        Category.objects.filter(item__item_type="PRODUCT", is_active=True),
        business,
    ).distinct().order_by("name")

    product_choices = products.order_by("name")

    if category_id:
        products = products.filter(category_id=category_id)

    if product_id:
        products = products.filter(id=product_id)

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(sku__icontains=search_query)
            | Q(barcode__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    if _model_table_ok(ItemVariant):
        standalone_products = products.annotate(
            variant_count=Count("variants", distinct=True),
        ).filter(variant_count=0)
    else:
        standalone_products = products

    if low_stock_only:
        standalone_products = standalone_products.filter(track_stock=True, stock_qty__lte=F("min_stock_qty"))

    stock_rows = []
    total_qty = Decimal("0")
    total_value = Decimal("0")

    for product in standalone_products.order_by("name"):
        quantity = product.stock_qty or Decimal("0")
        cost_price = product.cost_price or Decimal("0")
        selling_price = product.price or Decimal("0")
        stock_value = quantity * cost_price
        min_stock_qty = product.min_stock_qty or Decimal("0")
        is_low_stock = bool(product.track_stock and quantity <= min_stock_qty)

        total_qty += quantity
        total_value += stock_value

        stock_rows.append(
            {
                "product": product,
                "variant": None,
                "variant_label": "-",
                "category_name": product.category.name if product.category_id else "-",
                "sku": product.sku or "-",
                "barcode": product.barcode or "-",
                "quantity": quantity,
                "min_stock_qty": min_stock_qty,
                "cost_price": cost_price,
                "selling_price": selling_price,
                "stock_value": stock_value,
                "is_low_stock": is_low_stock,
            }
        )

    if _model_table_ok(ItemVariant):
        variants = _filter_by_business(
            ItemVariant.objects.filter(item__item_type="PRODUCT").select_related(
                "item",
                "item__category",
                "clothing_detail__size",
                "clothing_detail__color",
            ),
            business,
        )

        if category_id:
            variants = variants.filter(item__category_id=category_id)

        if product_id:
            variants = variants.filter(item_id=product_id)

        if search_query:
            variants = variants.filter(
                Q(item__name__icontains=search_query)
                | Q(name__icontains=search_query)
                | Q(sku__icontains=search_query)
                | Q(barcode__icontains=search_query)
                | Q(item__category__name__icontains=search_query)
                | Q(clothing_detail__size__name__icontains=search_query)
                | Q(clothing_detail__color__name__icontains=search_query)
            )

        if low_stock_only:
            variants = variants.filter(track_stock=True, stock_qty__lte=F("min_stock_qty"))

        for variant in variants.order_by("item__name", "name"):
            quantity = variant.stock_qty or Decimal("0")
            cost_price = variant.cost_price if variant.cost_price is not None else (variant.item.cost_price or Decimal("0"))
            selling_price = variant.price if variant.price is not None else (variant.item.price or Decimal("0"))
            stock_value = quantity * cost_price
            min_stock_qty = variant.min_stock_qty or Decimal("0")
            is_low_stock = bool(variant.track_stock and quantity <= min_stock_qty)

            total_qty += quantity
            total_value += stock_value

            stock_rows.append(
                {
                    "product": variant.item,
                    "variant": variant,
                    "variant_label": _variant_snapshot_name(variant) or variant.name,
                    "category_name": variant.item.category.name if variant.item.category_id else "-",
                    "sku": variant.sku or "-",
                    "barcode": variant.barcode or "-",
                    "quantity": quantity,
                    "min_stock_qty": min_stock_qty,
                    "cost_price": cost_price,
                    "selling_price": selling_price,
                    "stock_value": stock_value,
                    "is_low_stock": is_low_stock,
                }
            )

    context = {
        "stock_rows": stock_rows,
        "categories": categories,
        "products": product_choices,
        "search_query": search_query,
        "selected_category": category_id,
        "selected_product": product_id,
        "low_stock_only": low_stock_only,
        "total_qty": total_qty,
        "total_value": total_value,
        "row_count": len(stock_rows),
    }
    return render(request, "clothing/current_stock.html", context)


@inventory_access_required
def purchase_list(request):
    business = _get_request_business(request)
    search_query = (request.GET.get("q") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    status = (request.GET.get("status") or "").strip().upper()
    if not _model_table_ok(Purchase):
        return HttpResponseForbidden("Purchase table schema is out of date. Run migrations.")
    purchases = _filter_by_business(
        Purchase.objects.select_related("supplier"),
        business,
    )

    if search_query:
        purchases = purchases.filter(
            Q(purchase_no__icontains=search_query)
            | Q(supplier__name__icontains=search_query)
            | Q(items__item_name_snapshot__icontains=search_query)
            | Q(items__variant_name_snapshot__icontains=search_query)
        )

    valid_statuses = {choice[0] for choice in Purchase.STATUS}
    if status in valid_statuses:
        purchases = purchases.filter(status=status)
    else:
        status = ""

    if date_from:
        purchases = purchases.filter(purchase_date__gte=date_from)
    if date_to:
        purchases = purchases.filter(purchase_date__lte=date_to)

    remaining_expr = ExpressionWrapper(
        F("items__quantity") - F("items__received_quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    purchases = purchases.annotate(
        remaining_total=Coalesce(
            Sum(remaining_expr),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        )
    ).distinct().order_by("-purchase_date", "-created_at")

    context = {
        "purchases": purchases,
        "search_query": search_query,
        "date_from": date_from,
        "date_to": date_to,
        "status": status,
        "status_choices": Purchase.STATUS,
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
        {
            "form": form,
            "formset": formset,
            "mode": "create",
            "variant_item_map": _purchase_variant_item_map(business),
        },
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

    items = list(
        PurchaseItem.objects.filter(purchase=purchase)
        .select_related("item", "variant")
        .order_by("id")
    )

    has_remaining_items = any(
        (line.quantity or Decimal("0")) > (line.received_quantity or Decimal("0"))
        for line in items
    )

    can_receive_stock = purchase.status != "CANCELLED" and has_remaining_items
    can_edit_purchase = purchase.status != "RECEIVED"

    context = {
        "purchase": purchase,
        "items": items,
        "can_receive_stock": can_receive_stock,
        "can_edit_purchase": can_edit_purchase,
    }
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
        {
            "form": form,
            "formset": formset,
            "mode": "edit",
            "purchase": purchase,
            "variant_item_map": _purchase_variant_item_map(business),
        },
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

    for line in lines:
        target = line.variant if line.variant_id else line.item
        current_cost_price = Decimal(str(target.cost_price)) if target.cost_price is not None else None
        current_selling_price = Decimal(str(target.price)) if target.price is not None else None
        incoming_unit_cost = Decimal(str(line.unit_cost or 0))
        incoming_selling_price = Decimal(str(line.selling_price)) if line.selling_price is not None else None

        open_batches = StockBatch.objects.filter(
            business=purchase.business,
            item=line.item,
            variant=line.variant,
            remaining_qty__gt=0,
        ).order_by("received_at", "id")

        line.open_batch_preview = [
            f"{batch.remaining_qty} @ {batch.unit_cost}"
            for batch in open_batches[:5]
        ]
        line.open_batch_count = open_batches.count()
        line.current_cost_price = current_cost_price
        line.current_selling_price = current_selling_price
        line.incoming_unit_cost = incoming_unit_cost
        line.incoming_selling_price = incoming_selling_price

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

