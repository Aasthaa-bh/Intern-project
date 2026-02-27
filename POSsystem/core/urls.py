from django.urls import path

from .views_staff import staff_list, staff_create, staff_edit, staff_toggle_active, staff_reset_password 
from .views import (home_view, get_started_view, superadmin_dashboard,  superadmin_requests, approve_request,reject_request, request_detail, owner_dashboard,)

urlpatterns = [
    path("", home_view, name="home"),
    path("get-started/", get_started_view, name="get_started"),
    path("superadmin/dashboard/", superadmin_dashboard, name="superadmin_dashboard"),
    path("superadmin/requests/", superadmin_requests, name="superadmin_requests"),
    path("superadmin/approve/<int:request_id>/", approve_request, name="approve_request"),
    path("superadmin/reject/<int:request_id>/", reject_request, name="reject_request"),
    path("superadmin/request/<int:request_id>/", request_detail, name="request_detail"),
    path("owner/dashboard/", owner_dashboard, name="owner_dashboard"),
    path("owner/staff/", staff_list, name="staff_list"),
    path("owner/staff/create/", staff_create, name="staff_create"),
    path("owner/staff/<int:staff_id>/edit/", staff_edit, name="staff_edit"),
    path("owner/staff/<int:staff_id>/toggle-active/", staff_toggle_active, name="staff_toggle_active"),
    path("owner/staff/<int:staff_id>/reset-password/", staff_reset_password, name="staff_reset_password"),
]