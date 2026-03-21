from django.urls import path
from . import views_offer, views_payment

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
]
