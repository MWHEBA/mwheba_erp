from django.urls import path
from . import views

app_name = 'purchase'

urlpatterns = [
    # طلبات الشراء
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    
    # فواتير المشتريات
    path('', views.purchase_list, name='purchase_list'),
    path('create/', views.purchase_create, name='purchase_create'),
    path('<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('<int:pk>/edit/', views.purchase_update, name='purchase_edit'),
    path('<int:pk>/delete/', views.purchase_delete, name='purchase_delete'),
    path('<int:pk>/print/', views.purchase_print, name='purchase_print'),
    
    # المدفوعات
    path('<int:pk>/add-payment/', views.add_payment, name='purchase_add_payment'),
    
    # مرتجعات المشتريات
    path('<int:pk>/return/', views.purchase_return, name='purchase_return'),
    path('returns/', views.purchase_return_list, name='purchase_return_list'),
    path('returns/<int:pk>/', views.purchase_return_detail, name='purchase_return_detail'),
    path('returns/<int:pk>/confirm/', views.purchase_return_confirm, name='purchase_return_confirm'),
    path('returns/<int:pk>/cancel/', views.purchase_return_cancel, name='purchase_return_cancel'),
]