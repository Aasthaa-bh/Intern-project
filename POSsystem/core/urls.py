from django.urls import path
from .views_staff import staff_delete, staff_list, staff_create, staff_edit, staff_toggle_active, staff_reset_password 
from .views import (home_view, get_started_view, superadmin_dashboard,  superadmin_requests, approve_request,reject_request, request_detail,  business_dashboard_router)
from .views import (home_view, get_started_view, superadmin_dashboard,  superadmin_requests, approve_request,reject_request, request_detail, owner_dashboard_redirect,restaurant_owner_dashboard,
    clothing_owner_dashboard, mart_owner_dashboard, mark_notification_read, mark_all_notifications_read)

urlpatterns = [
    path("", home_view, name="home"),
    path("get-started/", get_started_view, name="get_started"),
    path("superadmin/dashboard/", superadmin_dashboard, name="superadmin_dashboard"),
    path("superadmin/requests/", superadmin_requests, name="superadmin_requests"),
    path("superadmin/approve/<int:request_id>/", approve_request, name="approve_request"),
    path("superadmin/reject/<int:request_id>/", reject_request, name="reject_request"),
    path("superadmin/request/<int:request_id>/", request_detail, name="request_detail"),

    path("owner/dashboard/", owner_dashboard_redirect, name="owner_dashboard"),

    
    path("owner/dashboard/restaurant/", restaurant_owner_dashboard, name="restaurant_owner_dashboard"),
    path("owner/dashboard/clothing/", clothing_owner_dashboard, name="clothing_owner_dashboard"),
    path("owner/dashboard/mart/", mart_owner_dashboard, name="mart_owner_dashboard"),

    path("owner/staff/", staff_list, name="staff_list"),
    path("owner/staff/create/", staff_create, name="staff_create"),
    path("owner/staff/<int:staff_id>/edit/", staff_edit, name="staff_edit"),
    path("owner/staff/<int:staff_id>/toggle-active/", staff_toggle_active, name="staff_toggle_active"),
    path("owner/staff/<int:staff_id>/reset-password/", staff_reset_password, name="staff_reset_password"),
    path("owner/staff/<int:staff_id>/delete/", staff_delete, name="staff_delete"),
    path("dashboard/", business_dashboard_router, name="business_dashboard_router"),

  
]