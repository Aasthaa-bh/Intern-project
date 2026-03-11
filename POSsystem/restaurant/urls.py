from django.urls import path
from . import views
from . import views_table
from .views import create_order

urlpatterns = [
    
    path("kitchen/", views.kitchen_dashboard, name="restaurant_kitchen_dashboard"),
    path("kitchen/stock/", views.kitchen_stock, name="restaurant_kitchen_stock"),
    path(
        "kitchen/stock/ingredients/<int:ingredient_id>/delete/",
        views.kitchen_ingredient_delete,
        name="restaurant_kitchen_ingredient_delete",
    ),
    path(
        "kitchen/stock/changes/<int:change_id>/delete/",
        views.kitchen_stock_change_delete,
        name="restaurant_kitchen_stock_change_delete",
    ),
    path(
        "kitchen/stock/changes/<int:change_id>/edit/",
        views.kitchen_stock_change_edit,
        name="restaurant_kitchen_stock_change_edit",
    ),
    path(
        "kitchen/orders/<int:order_id>/status/",
        views.kitchen_order_status_update,
        name="restaurant_kitchen_order_status_update",
    ),
  
   path("create-order/", create_order, name="create_order"),
  
  path("owner/table-categories/", views_table.table_category_list, name="table_category_list"),
    path("owner/table-categories/create/", views_table.table_category_create, name="table_category_create"),

    path("owner/tables/", views_table.table_list, name="table_list"),
    path("owner/tables/create/", views_table.table_create, name="table_create"),
    # Reception Dashboard
    path('reception/', views.reception_dashboard, name='reception_dashboard'),
    
    # Table Management
    path('reception/tables/', views.table_check, name='table_check'),
    path('reception/tables/<int:table_id>/', views.table_bill, name='table_bill'),
    path('reception/tables/<int:table_id>/update/', views.update_table_status, name='update_table_status'),
    path('reception/tables/<int:table_id>/toggle/', views.toggle_table_status, name='toggle_table_status'),
    path('reception/tables/<int:table_id>/quick-status/', views.quick_status_change, name='quick_status_change'),
    path('reception/tables/<int:table_id>/create-invoice/', views.create_invoice, name='create_invoice'),
    path('reception/bulk-update-tables/', views.bulk_update_tables, name='bulk_update_tables'),
    path('reception/bulk-update-all/', views.bulk_update_all_tables, name='bulk_update_all_tables'),
    
    # Billing
    path('reception/bill/<int:invoice_id>/', views.guest_bill, name='guest_bill'),
    path('reception/bill/<int:invoice_id>/split/', views.split_bill, name='split_bill'),
    
    # Payment
    path('reception/payment/<int:invoice_id>/', views.process_payment, name='process_payment'),
    path('reception/payment/<int:invoice_id>/partial/', views.partial_payment, name='partial_payment'),
    path('reception/payment/history/', views.payment_history, name='payment_history'),
    path('reception/payment/success/<int:payment_id>/', views.payment_success, name='payment_success'),
    
    # eSewa Payment (Mock)
    path('reception/esewa/<int:invoice_id>/', views.esewa_payment, name='esewa_payment'),
    path('reception/esewa/success/', views.restaurant_esewa_success, name='restaurant_esewa_success'),
    path('reception/esewa/failure/', views.restaurant_esewa_failure, name='restaurant_esewa_failure'),
    
    # Loyalty
    path('reception/loyalty/', views.loyalty_points_check, name='loyalty_points_check'),
    
    # QR Payments
    path('reception/qr/<int:invoice_id>/', views.qr_payment, name='qr_payment'),
    path('reception/qr/<int:invoice_id>/confirm/', views.confirm_qr_payment, name='confirm_qr_payment'),
    
    # Payment Management
    path('reception/payments/', views.payment_list, name='payment_list'),
    path('reception/payments/daily-report/', views.daily_payment_report, name='daily_payment_report'),
    
    # Pending Invoices
    path('reception/pending-invoices/', views.pending_invoices, name='pending_invoices'),
    
    # Payment Verification
    path('reception/payment/verify/<int:payment_id>/', views.verify_payment, name='verify_payment'),
    path('reception/payments/pending/', views.pending_payments_list, name='pending_payments_list'),
]
