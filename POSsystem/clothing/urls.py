from django.urls import path

from . import views

urlpatterns = [
    path("", views.inventory_dashboard, name="clothing_inventory_dashboard"),
    path("products/", views.product_list, name="clothing_product_list"),
    path("products/<int:product_id>/", views.product_detail, name="clothing_product_detail"),
    path("stock-movements/", views.stock_movement_list, name="clothing_stock_movements"),
    path("purchases/", views.purchase_list, name="clothing_purchase_list"),
    path("purchases/<int:purchase_id>/", views.purchase_detail, name="clothing_purchase_detail"),
    path("suppliers/", views.supplier_list, name="clothing_supplier_list"),
    path("low-stock/", views.low_stock_alert, name="clothing_low_stock"),
]
