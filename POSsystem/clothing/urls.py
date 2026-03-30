from django.urls import path
from . import views_offer, views_payment, views

urlpatterns = [
    # Dashboard
    path("offers/dashboard/", views_offer.offer_dashboard, name="clothing_offer_dashboard"),
    
    # Offer Management
    path("offers/", views_offer.offer_list, name="clothing_offer_list"),
    path("offers/create/", views_offer.offer_create, name="clothing_offer_create"),
    path("offers/<int:offer_id>/", views_offer.offer_detail, name="clothing_offer_detail"),
    path("offers/<int:offer_id>/edit/", views_offer.offer_edit, name="clothing_offer_edit"),
    path("offers/<int:offer_id>/delete/", views_offer.offer_delete, name="clothing_offer_delete"),
    path("offers/<int:offer_id>/toggle/", views_offer.offer_toggle_status, name="clothing_offer_toggle_status"),
    
    # eSewa Payment
    path("payment/initiate/", views_payment.initiate_payment, name="clothing_payment_initiate"),
    path("payment/success/", views_payment.payment_success, name="clothing_payment_success"),
    path("payment/failure/", views_payment.payment_failure, name="clothing_payment_failure"),

    path("", views.inventory_dashboard, name="clothing_inventory_dashboard"),
    path("", views.inventory_dashboard, name="inventory_dashboard"),
    path("inventory/", views.inventory_dashboard, name="clothing_inventory_dashboard_inventory"),
    path("inventory/dashboard/", views.inventory_dashboard, name="clothing_inventory_dashboard_inventory_dashboard"),
    path("inventory_dashboard/", views.inventory_dashboard, name="clothing_inventory_dashboard_legacy"),
    path("inventory_dasgboard/", views.inventory_dashboard, name="inventory_dasgboard"),
    path("products/", views.product_list, name="clothing_product_list"),
    path("products/create/", views.product_create, name="clothing_product_create"),
    path("products/<int:product_id>/", views.product_detail, name="clothing_product_detail"),
    path("products/<int:product_id>/edit/", views.product_edit, name="clothing_product_edit"),
    path("products/<int:product_id>/delete/", views.product_delete, name="clothing_product_delete"),
    path("variants/", views.variant_list, name="clothing_variant_list"),
    path("products/<int:product_id>/variants/create/", views.variant_create, name="clothing_variant_create"),
    path("products/<int:product_id>/variants/<int:variant_id>/edit/", views.variant_edit, name="clothing_variant_edit"),
    path("products/<int:product_id>/variants/<int:variant_id>/delete/", views.variant_delete, name="clothing_variant_delete"),
    path("products/<int:product_id>/variants/<int:variant_id>/barcode/", views.variant_barcode_label, name="clothing_variant_barcode"),
    path("current-stock/", views.current_stock, name="clothing_current_stock"),
    path("stock-movements/", views.stock_movement_list, name="clothing_stock_movements"),
    path("stock-adjustments/create/", views.stock_adjustment_create, name="clothing_stock_adjustment_create"),
    path("purchases/", views.purchase_list, name="clothing_purchase_list"),
    path("purchases/create/", views.purchase_create, name="clothing_purchase_create"),
    path("purchases/<int:purchase_id>/", views.purchase_detail, name="clothing_purchase_detail"),
    path("purchases/<int:purchase_id>/edit/", views.purchase_edit, name="clothing_purchase_edit"),
    path("purchases/<int:purchase_id>/receive/", views.purchase_receive, name="clothing_purchase_receive"),
    path("suppliers/", views.supplier_list, name="clothing_supplier_list"),
    path("suppliers/create/", views.supplier_create, name="clothing_supplier_create"),
    path("suppliers/<int:supplier_id>/edit/", views.supplier_edit, name="clothing_supplier_edit"),
    path("suppliers/<int:supplier_id>/delete/", views.supplier_delete, name="clothing_supplier_delete"),
    path("low-stock/", views.low_stock_alert, name="clothing_low_stock"),
    
]
