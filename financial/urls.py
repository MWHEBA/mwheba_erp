from django.urls import path
from . import views

app_name = 'financial'

urlpatterns = [
    # الصفحات الرئيسية
    path('accounts/', views.account_list, name='account_list'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('incomes/', views.income_list, name='income_list'),
    
    # صفحات التفاصيل
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('incomes/<int:pk>/', views.income_detail, name='income_detail'),
    
    # صفحات الإنشاء والتعديل
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/transactions/', views.account_transactions, name='account_transactions'),
    path('accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),
    
    path('transactions/create/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/mark-paid/', views.expense_mark_paid, name='expense_mark_paid'),
    path('expenses/<int:pk>/cancel/', views.expense_cancel, name='expense_cancel'),
    
    path('incomes/create/', views.income_create, name='income_create'),
    path('incomes/<int:pk>/edit/', views.income_edit, name='income_edit'),
    path('incomes/<int:pk>/mark-received/', views.income_mark_received, name='income_mark_received'),
    path('incomes/<int:pk>/cancel/', views.income_cancel, name='income_cancel'),
    
    # التسوية البنكية
    path('bank-reconciliation/', views.bank_reconciliation_list, name='bank_reconciliation_list'),
    path('bank-reconciliation/create/', views.bank_reconciliation_create, name='bank_reconciliation_create'),
    
    # التقارير المالية
    path('reports/ledger/', views.ledger_report, name='ledger_report'),
    path('reports/balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('reports/income-statement/', views.income_statement, name='income_statement'),
    path('reports/analytics/', views.financial_analytics, name='financial_analytics'),
    
    # فئات المصروفات والإيرادات
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # واجهات API للتصدير
    path('api/export-transactions/', views.export_transactions, name='export_transactions'),
] 