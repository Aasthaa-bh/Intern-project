from django.urls import path

from . import views, views_cashier, esewa as esewa_views

urlpatterns = [
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
    path("variants/", views.variant_list, name="clothing_variant_list"),
    path("products/<int:product_id>/variants/create/", views.variant_create, name="clothing_variant_create"),
    path("products/<int:product_id>/variants/<int:variant_id>/edit/", views.variant_edit, name="clothing_variant_edit"),
    path("products/<int:product_id>/variants/<int:variant_id>/delete/", views.variant_delete, name="clothing_variant_delete"),
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

    # Cashier Panel (main pages)
    path("cashier/dashboard/", views.cashier_dashboard, name="cashier_dashboard"),
    path("cashier/", views.cashier_dashboard, name="clothing_cashier_dashboard"),
    path("cashier/products/", views.cashier_products, name="cashier_products"),
    path("cashier/pos/", views.cashier_pos, name="cashier_pos"),
    path("cashier/sales/", views.cashier_sales_history, name="cashier_sales_history"),
    path("cashier/profile/", views.cashier_profile, name="cashier_profile"),
    path("cashier/receipt/<int:order_id>/", views.cashier_receipt, name="cashier_receipt"),

    # Cashier AJAX / actions
    path("cashier/api/complete-sale/", views.cashier_complete_sale, name="cashier_complete_sale"),
    path("cashier/api/lookup-customer/", views.cashier_lookup_customer, name="cashier_lookup_customer"),
    path("cashier/api/update-profile/", views_cashier.update_profile, name="clothing_cashier_update_profile"),
    path("cashier/api/change-password/", views_cashier.change_password, name="clothing_cashier_change_password"),
    # eSewa payment
    path("cashier/esewa/initiate/", esewa_views.esewa_initiate, name="clothing_esewa_initiate"),
    path("cashier/esewa/success/",  esewa_views.esewa_success,  name="clothing_esewa_success"),
    path("cashier/esewa/failure/",  esewa_views.esewa_failure,  name="clothing_esewa_failure"),
]

