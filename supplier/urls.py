from django.urls import path
from . import views

app_name = 'supplier'

urlpatterns = [
    path('', views.supplier_list, name='supplier_list'),
    path('add/', views.supplier_add, name='supplier_add'),
    path('<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('<int:pk>/detail/', views.supplier_detail, name='supplier_detail'),
    path('payment/add/', views.supplier_payment_add, name='supplier_payment_add'),
    path('<int:supplier_id>/payment/add/', views.supplier_payment_add, name='supplier_payment_add_for_supplier'),
] 