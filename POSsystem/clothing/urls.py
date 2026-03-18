from django.urls import path

from . import views

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
    path("products/<int:product_id>/variants/create/", views.variant_create, name="clothing_variant_create"),
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
