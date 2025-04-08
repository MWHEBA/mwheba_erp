from django.urls import path
from . import views

app_name = 'sale'

urlpatterns = [
    # فواتير المبيعات
    path('', views.sale_list, name='sale_list'),
    path('create/', views.sale_create, name='sale_create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('<int:pk>/edit/', views.sale_edit, name='sale_edit'),
    path('<int:pk>/delete/', views.sale_delete, name='sale_delete'),
    path('<int:pk>/print/', views.sale_print, name='sale_print'),
    path('<int:pk>/payment/', views.add_payment, name='sale_add_payment'),
    
    # مدفوعات المبيعات
    path('payments/', views.sale_payment_list, name='sale_payment_list'),
    
    # مرتجعات المبيعات
    path('returns/', views.sale_return_list, name='sale_return_list'),
    path('<int:pk>/return/', views.sale_return, name='sale_return'),
    path('returns/<int:pk>/', views.sale_return_detail, name='sale_return_detail'),
    path('returns/<int:pk>/confirm/', views.sale_return_confirm, name='sale_return_confirm'),
    path('returns/<int:pk>/cancel/', views.sale_return_cancel, name='sale_return_cancel'),
] 