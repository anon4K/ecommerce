from django.urls import path
from . import views

urlpatterns = [
    path('create-intent/', views.CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('confirm/', views.ConfirmPaymentView.as_view(), name='confirm-payment'),
]