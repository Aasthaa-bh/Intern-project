from django.urls import path
from . import views
from . import views_category, views_item, views_loyalty

urlpatterns = [
    # Waiter Dashboard & Navigation
    path("waiter/", views.waiter_dashboard, name="waiter_dashboard"),
    path("waiter/tables/", views.waiter_tables, name="waiter_tables"),
    path("waiter/done-orders/", views.waiter_done_orders, name="waiter_done_orders"),
    path("waiter/create-order/<str:order_type>/", views.create_order_by_type, name="create_order_by_type"),
    
    # Table & Order Management
    path("table/<int:table_id>/select/", views.select_table, name="select_table"),
    path("create-order-direct/", views.create_order_direct, name="create_order_direct"),
    path("table/<int:table_id>/create-order/", views.create_order, name="create_order"),
    path("create-order/", views.create_order, name="create_order_no_table"),
    
    # Order Operations
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path(
        "order/<int:order_id>/add-items/", views.add_order_items, name="add_order_items"
    ),
    path(
        "order/<int:order_id>/send-to-kitchen/",
        views.send_to_kitchen,
        name="send_to_kitchen",
    ),
    path(
        "order/<int:order_id>/send-to-cashier/",
        views.send_to_cashier,
        name="send_to_cashier",
    ),
    path(
        "order/<int:order_id>/confirm/",
        views.confirm_order,
        name="confirm_order",
    ),
    path(
        "order/<int:order_id>/complete/",
        views.complete_order,
        name="complete_order",
    ),
    path(
        "order-item/<int:order_item_id>/delete/",
        views.delete_order_item,
        name="delete_order_item",
    ),

    # Kitchen Display
    path("kitchen/", views.kitchen_display, name="kitchen_display"),
    path(
        "kitchen/<int:kitchen_order_id>/update-status/",
        views.update_kitchen_status,
        name="update_kitchen_status",
    ),
    # Cashier/Receptionist
    path("cashier/", views.cashier_view, name="cashier_view"),
    # Table Management
    path("tables/", views.table_management, name="table_management"),
    path(
        "table/<int:table_id>/update-status/",
        views.update_table_status,
        name="update_table_status",
    ),
    # API
    path("api/menu-items/", views.get_menu_items_json, name="menu_items_json"),
    
    path("owner/categories/", views_category.category_list, name="category_list"),
    path("owner/categories/create/", views_category.category_create, name="category_create"),
    path("owner/categories/<int:category_id>/edit/", views_category.category_edit, name="category_edit"),
    path("owner/items/", views_item.item_list, name="item_list"),
    path("owner/items/create/", views_item.item_create, name="item_create"),
    path("owner/items/<int:item_id>/edit/", views_item.item_edit, name="item_edit"),
    path("owner/loyalty/settings/", views_loyalty.loyalty_settings, name="loyalty_settings"),
]
