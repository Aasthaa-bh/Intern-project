from django.urls import path
from . import views

urlpatterns = [

    # SUPERADMIN
    path("packages/", views.package_list, name="package_list"),
    path("packages/create/", views.package_create, name="package_create"),
    path("packages/update/<int:pk>/", views.package_update, name="package_update"),
    path("packages/delete/<int:pk>/", views.package_delete, name="package_delete"),
    path("subscriptions/", views.subscription_list, name="subscription_list"),
    path("payments/", views.payment_list, name="payment_list"),
    # BUSINESS
    path("plans/", views.business_package_list, name="business_package_list"),
    path("choose/<int:pk>/", views.choose_package, name="choose_package"),
    path("payment/<int:subscription_id>/", views.payment_page, name="payment_page"),
    path("esewa/success/", views.esewa_success, name="esewa_success"),
    path("esewa/failure/", views.esewa_failure, name="esewa_failure"),

]