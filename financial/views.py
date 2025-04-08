from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import csv
import json

from .models import Account, Transaction, Expense, Income, Category, TransactionLine, BankReconciliation
from .forms import AccountForm, TransactionForm, ExpenseForm, IncomeForm, BankReconciliationForm, CategoryForm


@login_required
def account_list(request):
    """
    عرض قائمة الحسابات المالية
    """
    accounts = Account.objects.filter(is_active=True)
    
    # إحصائيات
    total_assets = accounts.filter(balance__gt=0).aggregate(Sum('balance')).get('balance__sum', 0) or 0
    total_income = Transaction.objects.filter(transaction_type='income').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    total_expenses = Transaction.objects.filter(transaction_type='expense').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    
    context = {
        'accounts': accounts,
        'total_assets': total_assets,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'page_title': 'الحسابات المالية',
        'page_icon': 'fas fa-landmark',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'الحسابات المالية', 'active': True}
        ],
    }
    
    return render(request, 'financial/account_list.html', context)


@login_required
def account_detail(request, pk):
    """
    عرض تفاصيل حساب مالي محدد
    """
    account = get_object_or_404(Account, pk=pk)
    
    # آخر 10 معاملات للحساب
    transactions = Transaction.objects.filter(
        Q(account=account) | Q(to_account=account)
    ).order_by('-date', '-id')[:10]
    
    # إحصائيات الحساب
    income_sum = Transaction.objects.filter(account=account, transaction_type='income').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    expense_sum = Transaction.objects.filter(account=account, transaction_type='expense').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    
    # تعريف رؤوس الأعمدة للجدول الموحد
    transaction_headers = [
        {
            'key': 'transaction_type', 
            'label': 'النوع', 
            'sortable': False, 
            'format': 'icon_text',
            'icon_callback': 'get_type_class', 
            'icon_class_callback': 'get_type_icon',
            'width': '8%'
        },
        {
            'key': 'date', 
            'label': 'التاريخ', 
            'sortable': True, 
            'format': 'date',
            'class': 'text-center',
            'width': '10%'
        },
        {
            'key': 'description', 
            'label': 'الوصف', 
            'sortable': False, 
            'ellipsis': True,
            'width': 'auto'
        },
        {
            'key': 'deposit', 
            'label': 'الإيراد', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'positive',
            'width': '10%',
            'decimals': 2
        },
        {
            'key': 'withdraw', 
            'label': 'المصروف', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'negative',
            'width': '10%',
            'decimals': 2
        },
        {
            'key': 'reference_number', 
            'label': 'المرجع', 
            'sortable': False, 
            'format': 'reference',
            'class': 'text-center',
            'width': '10%'
        },
    ]
    
    # تعريف أزرار الإجراءات
    transaction_actions = [
        {
            'url': 'financial:transaction_detail', 
            'icon': 'fa-eye', 
            'label': 'عرض', 
            'class': 'action-view'
        },
        {
            'url': 'financial:transaction_edit', 
            'icon': 'fa-edit', 
            'label': 'تعديل', 
            'class': 'action-edit'
        }
    ]
    
    context = {
        'account': account,
        'transactions': transactions,
        'income_sum': income_sum,
        'expense_sum': expense_sum,
        'title': f'حساب: {account.name}',
        'transaction_headers': transaction_headers,
        'transaction_actions': transaction_actions,
    }
    
    return render(request, 'financial/account_detail.html', context)


@login_required
def account_create(request):
    """
    إنشاء حساب مالي جديد
    """
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.created_by = request.user
            
            # التعامل مع الرصيد الافتتاحي
            initial_balance = form.cleaned_data.get('initial_balance', 0)
            account.balance = initial_balance
            
            account.save()
            
            # إنشاء معاملة افتتاحية إذا كان الرصيد الافتتاحي موجودًا
            if initial_balance > 0:
                transaction = Transaction.objects.create(
                    account=account,
                    transaction_type='income',
                    amount=initial_balance,
                    date=timezone.now().date(),
                    description=f'رصيد افتتاحي - {account.name}',
                    reference=f'INIT-{account.code}',
                    created_by=request.user
                )
                
                # إنشاء بنود القيد المحاسبي
                TransactionLine.objects.create(
                    transaction=transaction,
                    account=account,
                    debit=initial_balance,
                    credit=0,
                    description='رصيد افتتاحي'
                )
                
                # حساب رأس المال أو الأصول
                capital_account = Account.objects.filter(account_type='equity').first()
                if not capital_account:
                    # إنشاء حساب رأس المال إذا لم يكن موجودًا
                    capital_account = Account.objects.create(
                        name='رأس المال',
                        code='EQ001',
                        account_type='equity',
                        created_by=request.user
                    )
                
                TransactionLine.objects.create(
                    transaction=transaction,
                    account=capital_account,
                    debit=0,
                    credit=initial_balance,
                    description='رصيد افتتاحي'
                )
                
            messages.success(request, f'تم إنشاء الحساب "{account.name}" بنجاح.')
            return redirect('financial:account_detail', pk=account.pk)
    else:
        form = AccountForm()
    
    context = {
        'form': form,
        'title': 'إنشاء حساب جديد',
    }
    
    return render(request, 'financial/account_form.html', context)


@login_required
def account_edit(request, pk):
    """
    تعديل حساب مالي
    """
    account = get_object_or_404(Account, pk=pk)
    
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تعديل الحساب "{account.name}" بنجاح.')
            return redirect('financial:account_detail', pk=account.pk)
    else:
        form = AccountForm(instance=account)
    
    context = {
        'form': form,
        'account': account,
        'title': f'تعديل حساب: {account.name}',
    }
    
    return render(request, 'financial/account_form.html', context)


@login_required
def account_transactions(request, pk):
    """
    عرض معاملات حساب محدد
    """
    account = get_object_or_404(Account, pk=pk)
    transactions = Transaction.objects.filter(
        Q(account=account) | Q(to_account=account)
    ).order_by('-date', '-id')
    
    # تعريف رؤوس الأعمدة للجدول الموحد
    transaction_headers = [
        {
            'key': 'transaction_type', 
            'label': 'النوع', 
            'sortable': False, 
            'format': 'icon_text',
            'icon_callback': 'get_type_class', 
            'icon_class_callback': 'get_type_icon',
            'width': '8%'
        },
        {
            'key': 'date', 
            'label': 'التاريخ', 
            'sortable': True, 
            'format': 'date',
            'class': 'text-center',
            'width': '10%'
        },
        {
            'key': 'description', 
            'label': 'الوصف', 
            'sortable': False, 
            'ellipsis': True,
            'width': 'auto'
        },
        {
            'key': 'deposit', 
            'label': 'الإيراد', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'positive',
            'width': '10%',
            'decimals': 2
        },
        {
            'key': 'withdraw', 
            'label': 'المصروف', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'negative',
            'width': '10%',
            'decimals': 2
        },
        {
            'key': 'balance_after', 
            'label': 'الرصيد بعد', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center fw-bold',
            'variant': 'neutral',
            'width': '12%',
            'decimals': 2
        },
        {
            'key': 'reference_number', 
            'label': 'المرجع', 
            'sortable': False, 
            'format': 'reference',
            'class': 'text-center',
            'width': '10%'
        },
    ]
    
    # تعريف أزرار الإجراءات
    transaction_actions = [
        {
            'url': 'financial:transaction_detail', 
            'icon': 'fa-eye', 
            'label': 'عرض', 
            'class': 'action-view'
        },
        {
            'url': 'financial:transaction_edit', 
            'icon': 'fa-edit', 
            'label': 'تعديل', 
            'class': 'action-edit'
        },
        {
            'url': 'financial:transaction_delete', 
            'icon': 'fa-trash-alt', 
            'label': 'حذف', 
            'class': 'action-delete'
        },
    ]
    
    context = {
        'account': account,
        'transactions': transactions,
        'title': f'معاملات حساب: {account.name}',
        'transaction_headers': transaction_headers,
        'transaction_actions': transaction_actions,
        'page_title': f'معاملات حساب: {account.name}',
        'page_icon': 'fas fa-exchange-alt',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'الحسابات', 'url': reverse('financial:account_list'), 'icon': 'fas fa-wallet'},
            {'title': account.name, 'url': reverse('financial:account_detail', kwargs={'pk': account.pk}), 'icon': 'fas fa-info-circle'},
            {'title': 'المعاملات', 'active': True}
        ],
    }
    
    return render(request, 'financial/account_transactions.html', context)


@login_required
def account_delete(request, pk):
    """
    حذف حساب مالي
    """
    account = get_object_or_404(Account, pk=pk)
    
    # التحقق من عدم وجود معاملات مرتبطة بالحساب
    has_transactions = Transaction.objects.filter(
        Q(account=account) | Q(to_account=account)
    ).exists()
    
    if request.method == 'POST':
        account_name = account.name
        
        # تعديل حالة الحساب بدلاً من الحذف الفعلي (حذف ناعم)
        account.is_active = False
        account.save()
        
        messages.success(request, f'تم حذف الحساب "{account_name}" بنجاح.')
        return redirect('financial:account_list')
    
    context = {
        'object': account,
        'object_name': 'الحساب',
        'title': f'حذف حساب: {account.name}',
        'cancel_url': reverse('financial:account_detail', kwargs={'pk': account.pk}),
        'warning_message': 'سيتم تعطيل الحساب وعدم ظهوره في قوائم الحسابات النشطة.' + 
                          (' كما أن هذا الحساب مرتبط بمعاملات مالية.' if has_transactions else '')
    }
    
    return render(request, 'financial/account_confirm_delete.html', context)


@login_required
def transaction_list(request):
    """
    عرض قائمة المعاملات المالية باستخدام نظام الجداول الموحد
    """
    # بدء الاستعلام بدون أخذ شريحة
    transactions = Transaction.objects.all().order_by('-date', '-id')
    accounts = Account.objects.filter(is_active=True)
    
    # فلترة
    account_id = request.GET.get('account')
    trans_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if account_id:
        account = get_object_or_404(Account, id=account_id)
        transactions = transactions.filter(Q(account=account) | Q(to_account=account))
    
    if trans_type:
        transactions = transactions.filter(transaction_type=trans_type)
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        transactions = transactions.filter(date__gte=date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        transactions = transactions.filter(date__lte=date_to)
    
    # إحصائيات - تطبيق على الاستعلام بعد الفلترة
    total_transactions = transactions.count()
    total_income = transactions.filter(transaction_type='income').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    total_expenses = transactions.filter(transaction_type='expense').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    total_balance = total_income - total_expenses
    
    # تعريف رؤوس الأعمدة للجدول الموحد
    headers = [
        {
            'key': 'transaction_type', 
            'label': 'النوع', 
            'sortable': False, 
            'format': 'icon_text',
            'icon_callback': 'get_type_class', 
            'icon_class_callback': 'get_type_icon',
            'width': '8%'
        },
        {
            'key': 'date', 
            'label': 'التاريخ', 
            'sortable': True, 
            'format': 'date',
            'class': 'text-center',
            'width': '10%'
        },
        {
            'key': 'account', 
            'label': 'الحساب', 
            'sortable': False,
            'width': '12%'
        },
        {
            'key': 'description', 
            'label': 'الوصف', 
            'sortable': False, 
            'ellipsis': True,
            'width': 'auto'
        },
        {
            'key': 'deposit', 
            'label': 'الإيراد', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'positive',
            'width': '10%',
            'decimals': 2
        },
        {
            'key': 'withdraw', 
            'label': 'المصروف', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'negative',
            'width': '10%',
            'decimals': 2
        },
        {
            'key': 'balance_after', 
            'label': 'الرصيد بعد', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center fw-bold',
            'variant': 'neutral',
            'width': '12%',
            'decimals': 2
        },
        {
            'key': 'reference_number', 
            'label': 'المرجع', 
            'sortable': False, 
            'format': 'reference',
            'class': 'text-center',
            'width': '10%'
        },
    ]
    
    # تعريف أزرار الإجراءات
    action_buttons = [
        {
            'url': 'financial:transaction_detail', 
            'icon': 'fa-eye', 
            'label': 'عرض', 
            'class': 'action-view'
        },
        {
            'url': 'financial:transaction_edit', 
            'icon': 'fa-edit', 
            'label': 'تعديل', 
            'class': 'action-edit'
        },
        {
            'url': 'financial:transaction_delete', 
            'icon': 'fa-trash-alt', 
            'label': 'حذف', 
            'class': 'action-delete'
        },
    ]
    
    # معالجة الترتيب
    current_order_by = request.GET.get('order_by', '')
    current_order_dir = request.GET.get('order_dir', '')
    
    # إعداد الترقيم الصفحي
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'transactions': page_obj,
        'headers': headers,
        'action_buttons': action_buttons,
        'accounts': accounts,
        'total_transactions': total_transactions,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_balance': total_balance,
        'page_title': 'المعاملات المالية',
        'page_icon': 'fas fa-exchange-alt',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'المعاملات المالية', 'active': True}
        ],
        'current_order_by': current_order_by,
        'current_order_dir': current_order_dir,
    }
    
    return render(request, 'financial/transaction_list.html', context)


@login_required
def transaction_detail(request, pk):
    """
    عرض تفاصيل معاملة مالية معينة
    """
    transaction = get_object_or_404(Transaction, pk=pk)
    
    context = {
        'transaction': transaction,
        'title': f'معاملة: {transaction.id}',
    }
    
    return render(request, 'financial/transaction_detail.html', context)


@login_required
def transaction_create(request):
    """
    إنشاء معاملة مالية جديدة
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            from django.db import transaction as db_transaction
            
            with db_transaction.atomic():
                # إنشاء المعاملة
                trans = form.save(commit=False)
                trans.created_by = request.user
                trans.save()
                
                # استخراج البيانات الأخرى من النموذج
                account = form.cleaned_data['account']
                transaction_type = form.cleaned_data['transaction_type']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data.get('description', '')
                
                # حساب مقابل افتراضي حسب نوع المعاملة
                contra_account = None
                if transaction_type == 'income':
                    # بحث عن حساب إيرادات افتراضي
                    contra_account = Account.objects.filter(account_type='income').first()
                    if not contra_account:
                        contra_account = Account.objects.create(
                            name='الإيرادات',
                            code='INC001',
                            account_type='income',
                            created_by=request.user
                        )
                elif transaction_type == 'expense':
                    # بحث عن حساب مصروفات افتراضي
                    contra_account = Account.objects.filter(account_type='expense').first()
                    if not contra_account:
                        contra_account = Account.objects.create(
                            name='المصروفات',
                            code='EXP001',
                            account_type='expense',
                            created_by=request.user
                        )
                
                # التأكد من وجود حساب قبل الاستمرار
                if not account:
                    messages.error(request, 'يجب تحديد الحساب الرئيسي للمعاملة')
                    return redirect('financial:transaction_create')
                
                # إنشاء بنود القيد المحاسبي
                if transaction_type == 'income':
                    # التأكد من وجود الحسابات المطلوبة
                    if not contra_account:
                        messages.error(request, 'لم يتم العثور على حساب الإيرادات')
                        return redirect('financial:transaction_create')
                        
                    # مدين: الحساب المختار (زيادة في الأصول)
                    TransactionLine.objects.create(
                        transaction=trans,
                        account=account,
                        debit=amount,
                        credit=0,
                        description=description
                    )
                    # دائن: حساب الإيرادات
                    TransactionLine.objects.create(
                        transaction=trans,
                        account=contra_account,
                        debit=0,
                        credit=amount,
                        description=description
                    )
                    
                    # تحديث رصيد الحساب
                    account.update_balance(amount, 'add')
                    
                elif transaction_type == 'expense':
                    # التأكد من وجود الحسابات المطلوبة
                    if not contra_account:
                        messages.error(request, 'لم يتم العثور على حساب المصروفات')
                        return redirect('financial:transaction_create')
                        
                    # مدين: حساب المصروفات
                    TransactionLine.objects.create(
                        transaction=trans,
                        account=contra_account,
                        debit=amount,
                        credit=0,
                        description=description
                    )
                    # دائن: الحساب المختار (نقص في الأصول)
                    TransactionLine.objects.create(
                        transaction=trans,
                        account=account,
                        debit=0,
                        credit=amount,
                        description=description
                    )
                    
                    # تحديث رصيد الحساب
                    account.update_balance(amount, 'subtract')
                
                elif transaction_type == 'transfer':
                    to_account = form.cleaned_data.get('to_account')
                    if to_account:
                        # مدين: حساب الوجهة (زيادة)
                        TransactionLine.objects.create(
                            transaction=trans,
                            account=to_account,
                            debit=amount,
                            credit=0,
                            description=description
                        )
                        # دائن: حساب المصدر (نقص)
                        TransactionLine.objects.create(
                            transaction=trans,
                            account=account,
                            debit=0,
                            credit=amount,
                            description=description
                        )
                        
                        # تحديث رصيد الحسابين
                        account.update_balance(amount, 'subtract')
                        to_account.update_balance(amount, 'add')
                    else:
                        # في حالة عدم وجود حساب وجهة (يجب ألا يحدث بسبب التحقق في النموذج)
                        messages.error(request, 'يجب تحديد حساب الوجهة للتحويل')
                        return redirect('financial:transaction_create')
                
            messages.success(request, 'تم إنشاء المعاملة المالية بنجاح.')
            return redirect('financial:transaction_detail', pk=trans.pk)
    else:
        form = TransactionForm()
    
    context = {
        'form': form,
        'title': 'إنشاء معاملة مالية',
    }
    
    return render(request, 'financial/transaction_form.html', context)


@login_required
def transaction_edit(request, pk):
    """
    تعديل معاملة مالية
    """
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            # تحديث المعاملة فقط
            form.save()
            messages.success(request, 'تم تعديل المعاملة المالية بنجاح.')
            return redirect('financial:transaction_detail', pk=transaction.pk)
    else:
        form = TransactionForm(instance=transaction)
    
    context = {
        'form': form,
        'transaction': transaction,
        'title': f'تعديل معاملة: {transaction.id}',
    }
    
    return render(request, 'financial/transaction_form.html', context)


@login_required
def transaction_delete(request, pk):
    """
    حذف معاملة مالية
    """
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        # إلغاء تأثير المعاملة على الحساب
        if transaction.transaction_type == 'income' and transaction.account:
            # التأكد من وجود الحساب قبل تعديل رصيده
            if hasattr(transaction.account, 'balance'):
                transaction.account.balance -= transaction.amount
                transaction.account.save()
            else:
                messages.warning(request, 'لم يتم العثور على الحساب المرتبط بالمعاملة أو تم حذفه مسبقاً.')
        
        elif transaction.transaction_type == 'expense' and transaction.account:
            # التأكد من وجود الحساب قبل تعديل رصيده
            if hasattr(transaction.account, 'balance'):
                transaction.account.balance += transaction.amount
                transaction.account.save()
            else:
                messages.warning(request, 'لم يتم العثور على الحساب المرتبط بالمعاملة أو تم حذفه مسبقاً.')
        
        elif transaction.transaction_type == 'transfer':
            # التحقق من وجود الحساب المصدر
            if transaction.account and hasattr(transaction.account, 'balance'):
                transaction.account.balance += transaction.amount
                transaction.account.save()
            else:
                messages.warning(request, 'لم يتم العثور على الحساب المصدر أو تم حذفه مسبقاً.')
            
            # التحقق من وجود الحساب المستلم
            if transaction.to_account and hasattr(transaction.to_account, 'balance'):
                transaction.to_account.balance -= transaction.amount
                transaction.to_account.save()
            else:
                messages.warning(request, 'لم يتم العثور على الحساب المستلم أو تم حذفه مسبقاً.')
        
        # حذف المعاملة بغض النظر عن حالة الحسابات
        transaction.delete()
        messages.success(request, 'تم حذف المعاملة بنجاح.')
        return redirect('financial:transaction_list')
    
    context = {
        'object': transaction,
        'title': 'حذف معاملة',
    }
    
    return render(request, 'financial/confirm_delete.html', context)


@login_required
def expense_list(request):
    """
    عرض قائمة المصروفات
    """
    expenses = Expense.objects.all().order_by('-date', '-id')
    accounts = Account.objects.filter(is_active=True)
    categories = Category.objects.filter(type='expense', is_active=True)
    
    # فلترة
    account_id = request.GET.get('account')
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if account_id:
        expenses = expenses.filter(account_id=account_id)
    
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    
    if status:
        expenses = expenses.filter(status=status)
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        expenses = expenses.filter(date__gte=date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        expenses = expenses.filter(date__lte=date_to)
    
    # إحصائيات
    total_expense = expenses.aggregate(Sum('amount')).get('amount__sum', 0) or 0
    paid_expenses = expenses.filter(status='paid').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    pending_expenses = expenses.filter(status='pending').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    
    # حساب متوسط المصروفات الشهرية
    today = timezone.now().date()
    six_months_ago = today - timedelta(days=180)
    monthly_expenses = expenses.filter(date__gte=six_months_ago).aggregate(Sum('amount')).get('amount__sum', 0) or 0
    monthly_average = monthly_expenses / 6 if monthly_expenses > 0 else 0
    
    # تعريف رؤوس الأعمدة للجدول الموحد
    headers = [
        {
            'key': 'title', 
            'label': 'العنوان', 
            'sortable': True,
            'width': '15%'
        },
        {
            'key': 'date', 
            'label': 'التاريخ', 
            'sortable': True, 
            'format': 'date',
            'class': 'text-center',
            'width': '10%'
        },
        {
            'key': 'category', 
            'label': 'الفئة', 
            'sortable': False,
            'width': '12%'
        },
        {
            'key': 'amount', 
            'label': 'المبلغ', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'negative',
            'width': '12%',
            'decimals': 2
        },
        {
            'key': 'payee', 
            'label': 'المستفيد', 
            'sortable': False,
            'width': '15%'
        },
        {
            'key': 'reference_number', 
            'label': 'رقم المرجع', 
            'sortable': False, 
            'format': 'reference',
            'class': 'text-center',
            'width': '10%'
        },
        {
            'key': 'status', 
            'label': 'الحالة', 
            'sortable': False, 
            'format': 'status',
            'class': 'text-center',
            'width': '10%'
        }
    ]
    
    # تعريف أزرار الإجراءات
    action_buttons = [
        {
            'url': 'financial:expense_detail', 
            'icon': 'fa-eye', 
            'label': 'عرض', 
            'class': 'action-view'
        },
        {
            'url': 'financial:expense_edit', 
            'icon': 'fa-edit', 
            'label': 'تعديل', 
            'class': 'action-edit'
        }
    ]
    
    # إضافة زر تسديد للمصروفات المعلقة (غير المدفوعة)
    expense_statuses = set(expenses.values_list('status', flat=True))
    if 'pending' in expense_statuses:
        action_buttons.append({
            'url': 'financial:expense_mark_paid', 
            'icon': 'fa-check-circle', 
            'label': 'تسديد', 
            'class': 'action-paid'
        })
    
    # معالجة الترتيب
    current_order_by = request.GET.get('order_by', '')
    current_order_dir = request.GET.get('order_dir', '')
    
    # ترقيم الصفحات
    paginator = Paginator(expenses, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'expenses': page_obj,
        'accounts': accounts,
        'categories': categories,
        'total_expense': total_expense,
        'paid_expenses': paid_expenses,
        'pending_expenses': pending_expenses,
        'monthly_average': monthly_average,
        'headers': headers,
        'action_buttons': action_buttons,
        'current_order_by': current_order_by,
        'current_order_dir': current_order_dir,
        'page_title': 'المصروفات',
        'page_icon': 'fas fa-hand-holding-usd',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'المصروفات', 'active': True}
        ],
    }
    
    return render(request, 'financial/expense_list.html', context)


@login_required
def expense_detail(request, pk):
    """
    عرض تفاصيل مصروف معين
    """
    expense = get_object_or_404(Expense, pk=pk)
    
    # الحصول على المعاملات المرتبطة
    related_transactions = Transaction.objects.filter(
        description__contains=f'تسديد مصروف: {expense.title}'
    )
    
    # تعريف رؤوس الأعمدة للجدول الموحد
    transaction_headers = [
        {
            'key': 'date', 
            'label': 'التاريخ', 
            'sortable': True, 
            'format': 'date',
            'class': 'text-center',
            'width': '10%'
        },
        {
            'key': 'account', 
            'label': 'الحساب', 
            'sortable': False,
            'width': '15%'
        },
        {
            'key': 'amount', 
            'label': 'المبلغ', 
            'sortable': False, 
            'format': 'currency', 
            'class': 'text-center',
            'variant': 'negative',
            'width': '12%',
            'decimals': 2
        },
        {
            'key': 'description', 
            'label': 'الوصف', 
            'sortable': False, 
            'ellipsis': True,
            'width': 'auto'
        },
        {
            'key': 'reference_number', 
            'label': 'المرجع', 
            'sortable': False, 
            'format': 'reference',
            'class': 'text-center',
            'width': '10%'
        },
    ]
    
    # تعريف أزرار الإجراءات
    transaction_actions = [
        {
            'url': 'financial:transaction_detail', 
            'icon': 'fa-eye', 
            'label': 'عرض', 
            'class': 'action-view'
        }
    ]
    
    context = {
        'expense': expense,
        'related_transactions': related_transactions,
        'transaction_headers': transaction_headers,
        'transaction_actions': transaction_actions,
        'title': f'مصروف: {expense.title}',
    }
    
    return render(request, 'financial/expense_detail.html', context)


@login_required
def expense_create(request):
    """
    إنشاء مصروف جديد
    """
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            
            messages.success(request, 'تم إنشاء المصروف بنجاح.')
            return redirect('financial:expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm()
    
    context = {
        'form': form,
        'title': 'إضافة مصروف جديد',
    }
    
    return render(request, 'financial/expense_form.html', context)


@login_required
def expense_edit(request, pk):
    """
    تعديل مصروف
    """
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تعديل المصروف بنجاح.')
            return redirect('financial:expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm(instance=expense)
    
    context = {
        'form': form,
        'expense': expense,
        'title': f'تعديل مصروف: {expense.title}',
    }
    
    return render(request, 'financial/expense_form.html', context)


@login_required
def expense_mark_paid(request, pk):
    """
    تحديد مصروف كمدفوع
    """
    expense = get_object_or_404(Expense, pk=pk)
    
    if expense.status == 'paid':
        messages.info(request, 'هذا المصروف مدفوع بالفعل.')
        return redirect('financial:expense_detail', pk=pk)
    
    if request.method == 'POST':
        account_id = request.POST.get('account')
        account = get_object_or_404(Account, id=account_id)
        
        # تحقق من كفاية الرصيد
        if expense.amount > account.balance:
            messages.error(request, 'رصيد الحساب غير كافي لتسديد هذا المصروف.')
            return redirect('financial:expense_detail', pk=pk)
        
        # تحديث حالة المصروف
        expense.status = 'paid'
        expense.payment_date = timezone.now().date()
        expense.save()
        
        # إنشاء معاملة مصروف
        transaction = Transaction.objects.create(
            account=account,
            transaction_type='expense',
            amount=expense.amount,
            date=timezone.now().date(),
            description=f'تسديد مصروف: {expense.title}',
            reference_number=expense.reference_number,
        )
        
        # تحديث رصيد الحساب
        account.balance -= expense.amount
        account.save()
        
        messages.success(request, 'تم تحديد المصروف كمدفوع بنجاح.')
        return redirect('financial:expense_detail', pk=pk)
    
    accounts = Account.objects.filter(is_active=True)
    
    context = {
        'expense': expense,
        'accounts': accounts,
        'title': 'تسديد مصروف',
    }
    
    return render(request, 'financial/expense_mark_paid.html', context)


@login_required
def expense_cancel(request, pk):
    """
    إلغاء مصروف
    """
    expense = get_object_or_404(Expense, pk=pk)
    
    if expense.status == 'cancelled':
        messages.info(request, 'هذا المصروف ملغي بالفعل.')
        return redirect('financial:expense_detail', pk=pk)
    
    if request.method == 'POST':
        expense.status = 'cancelled'
        expense.save()
        
        messages.success(request, 'تم إلغاء المصروف بنجاح.')
        return redirect('financial:expense_detail', pk=pk)
    
    context = {
        'object': expense,
        'title': 'إلغاء مصروف',
    }
    
    return render(request, 'financial/confirm_delete.html', context)


@login_required
def income_list(request):
    """
    عرض قائمة الإيرادات
    """
    incomes = Income.objects.all().order_by('-date', '-id')
    accounts = Account.objects.filter(is_active=True)
    categories = Category.objects.filter(type='income', is_active=True)
    
    # فلترة
    account_id = request.GET.get('account')
    category_id = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if account_id:
        incomes = incomes.filter(account_id=account_id)
    
    if category_id:
        incomes = incomes.filter(category_id=category_id)
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        incomes = incomes.filter(date__gte=date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        incomes = incomes.filter(date__lte=date_to)
    
    # إحصائيات
    total_income = incomes.aggregate(Sum('amount')).get('amount__sum', 0) or 0
    received_incomes = incomes.filter(status='received').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    pending_incomes = incomes.filter(status='pending').aggregate(Sum('amount')).get('amount__sum', 0) or 0
    
    # حساب متوسط الإيرادات الشهرية
    current_date = timezone.now().date()
    start_of_year = current_date.replace(month=1, day=1)
    months_passed = (current_date.year - start_of_year.year) * 12 + current_date.month - start_of_year.month + 1
    monthly_average = total_income / months_passed if months_passed > 0 else 0
    
    # تعريف أعمدة الجدول
    headers = [
        {'key': 'title', 'label': 'العنوان', 'sortable': True, 'class': 'col-title'},
        {'key': 'amount', 'label': 'المبلغ', 'sortable': True, 'class': 'text-center', 'format': 'currency', 'decimals': 2},
        {'key': 'category__name', 'label': 'الفئة', 'sortable': True},
        {'key': 'date', 'label': 'التاريخ', 'sortable': True, 'class': 'col-date', 'format': 'date'},
        {'key': 'status', 'label': 'الحالة', 'sortable': True, 'class': 'col-status', 'format': 'status'},
    ]
    
    # تعريف أزرار الإجراءات
    action_buttons = [
        {'url': 'financial:income_detail', 'icon': 'fa-eye', 'label': 'عرض', 'class': 'btn-primary action-view'},
        {'url': 'financial:income_edit', 'icon': 'fa-edit', 'label': 'تعديل', 'class': 'btn-secondary action-edit'},
        {'url': 'financial:income_mark_received', 'icon': 'fa-check-circle', 'label': 'استلام', 'class': 'btn-success action-received'},
        {'url': 'financial:income_cancel', 'icon': 'fa-ban', 'label': 'إلغاء', 'class': 'btn-danger action-cancel'},
    ]
    
    # ترقيم الصفحات
    paginator = Paginator(incomes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'incomes': page_obj,
        'accounts': accounts,
        'categories': categories,
        'total_income': total_income,
        'received_incomes': received_incomes,
        'pending_incomes': pending_incomes,
        'monthly_average': monthly_average,
        'headers': headers,
        'action_buttons': action_buttons,
        'page_title': 'الإيرادات',
        'page_icon': 'fas fa-cash-register',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'الإيرادات', 'active': True}
        ],
    }
    
    return render(request, 'financial/income_list.html', context)


@login_required
def income_detail(request, pk):
    """
    عرض تفاصيل إيراد معين
    """
    income = get_object_or_404(Income, pk=pk)
    
    context = {
        'income': income,
        'title': f'إيراد: {income.title}',
    }
    
    return render(request, 'financial/income_detail.html', context)


@login_required
def income_create(request):
    """
    إنشاء إيراد جديد
    """
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.created_by = request.user
            
            # تعيين حساب الإيراد بناءً على حساب الاستلام
            receiving_account = form.cleaned_data.get('receiving_account')
            if receiving_account:
                income.account = receiving_account
            else:
                # استخدام حساب افتراضي
                default_account = Account.objects.filter(name__icontains='خزينة', is_active=True).first()
                if not default_account:
                    default_account = Account.objects.filter(type='cash', is_active=True).first()
                if not default_account:
                    default_account = Account.objects.filter(is_active=True).first()
                
                if default_account:
                    income.account = default_account
                    income.receiving_account = default_account
            
            income.save()
            
            messages.success(request, 'تم إنشاء الإيراد بنجاح.')
            return redirect('financial:income_detail', pk=income.pk)
    else:
        form = IncomeForm()
    
    context = {
        'form': form,
        'title': 'إضافة إيراد جديد',
    }
    
    return render(request, 'financial/income_form.html', context)


@login_required
def income_edit(request, pk):
    """
    تعديل إيراد
    """
    income = get_object_or_404(Income, pk=pk)
    
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income)
        if form.is_valid():
            income = form.save(commit=False)
            
            # تعيين حساب الإيراد بناءً على حساب الاستلام
            receiving_account = form.cleaned_data.get('receiving_account')
            if receiving_account:
                income.account = receiving_account
            else:
                # استخدام حساب افتراضي
                default_account = Account.objects.filter(name__icontains='خزينة', is_active=True).first()
                if not default_account:
                    default_account = Account.objects.filter(type='cash', is_active=True).first()
                if not default_account:
                    default_account = Account.objects.filter(is_active=True).first()
                
                if default_account:
                    income.account = default_account
                    income.receiving_account = default_account
            
            income.save()
            
            messages.success(request, 'تم تعديل الإيراد بنجاح.')
            return redirect('financial:income_detail', pk=income.pk)
    else:
        form = IncomeForm(instance=income)
    
    context = {
        'form': form,
        'income': income,
        'title': f'تعديل إيراد: {income.title}',
    }
    
    return render(request, 'financial/income_form.html', context)


@login_required
def income_mark_received(request, pk):
    """
    تحديد إيراد كمستلم
    """
    income = get_object_or_404(Income, pk=pk)
    
    if income.status == 'received':
        messages.info(request, 'هذا الإيراد مستلم بالفعل.')
        return redirect('financial:income_detail', pk=pk)
    
    if request.method == 'POST':
        account_id = request.POST.get('account')
        
        # تسجيل بيانات الطلب للتشخيص
        print(f"DEBUG: POST Data: {request.POST}")
        print(f"DEBUG: Account ID: {account_id}")
        
        if not account_id:
            messages.error(request, 'لم يتم تحديد الحساب! يرجى اختيار حساب لاستلام الإيراد.')
            accounts = Account.objects.filter(is_active=True)
            context = {
                'income': income,
                'accounts': accounts,
                'title': 'استلام إيراد',
                'debug_info': f'POST Data: {request.POST}'
            }
            return render(request, 'financial/income_mark_received.html', context)
        
        account = get_object_or_404(Account, id=account_id)
        
        # تحديث حالة الإيراد
        income.status = 'received'
        income.received_date = timezone.now().date()
        income.save()
        
        # إنشاء معاملة إيراد
        transaction = Transaction.objects.create(
            account=account,
            transaction_type='income',
            amount=income.amount,
            date=timezone.now().date(),
            description=f'استلام إيراد: {income.title}',
            reference_number=income.reference_number,
        )
        
        # تحديث رصيد الحساب
        account.balance += income.amount
        account.save()
        
        messages.success(request, 'تم تحديد الإيراد كمستلم بنجاح.')
        return redirect('financial:income_detail', pk=pk)
    
    accounts = Account.objects.filter(is_active=True)
    
    context = {
        'income': income,
        'accounts': accounts,
        'title': 'استلام إيراد',
    }
    
    return render(request, 'financial/income_mark_received.html', context)


@login_required
def income_cancel(request, pk):
    """
    إلغاء إيراد
    """
    income = get_object_or_404(Income, pk=pk)
    
    if income.status == 'cancelled':
        messages.info(request, 'هذا الإيراد ملغي بالفعل.')
        return redirect('financial:income_detail', pk=pk)
    
    if request.method == 'POST':
        income.status = 'cancelled'
        income.save()
        
        messages.success(request, 'تم إلغاء الإيراد بنجاح.')
        return redirect('financial:income_detail', pk=pk)
    
    context = {
        'object': income,
        'title': 'إلغاء إيراد',
    }
    
    return render(request, 'financial/confirm_delete.html', context)


@login_required
def export_transactions(request):
    """
    تصدير المعاملات المالية
    """
    transactions = Transaction.objects.all().order_by('-date', '-id')
    
    # تطبيق الفلترة إذا كانت موجودة
    account_id = request.GET.get('account')
    trans_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if account_id:
        account = get_object_or_404(Account, id=account_id)
        transactions = transactions.filter(Q(account=account) | Q(to_account=account))
    
    if trans_type:
        transactions = transactions.filter(transaction_type=trans_type)
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        transactions = transactions.filter(date__gte=date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        transactions = transactions.filter(date__lte=date_to)
    
    # إنشاء ملف CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'التاريخ', 'النوع', 'الحساب', 'الوصف', 'المبلغ', 'الرقم المرجعي'])
    
    for transaction in transactions:
        writer.writerow([
            transaction.id,
            transaction.date,
            transaction.get_transaction_type_display(),
            transaction.account.name,
            transaction.description,
            transaction.amount,
            transaction.reference_number or '',
        ])
    
    return response


@login_required
def bank_reconciliation_list(request):
    """
    عرض قائمة التسويات البنكية
    """
    reconciliations = BankReconciliation.objects.all().order_by('-reconciliation_date')
    accounts = Account.objects.filter(is_bank_reconciliation=True, is_active=True)
    
    context = {
        'reconciliations': reconciliations,
        'accounts': accounts,
        'title': 'التسويات البنكية',
    }
    
    return render(request, 'financial/bank_reconciliation_list.html', context)


@login_required
def bank_reconciliation_create(request):
    """
    إنشاء تسوية بنكية جديدة
    """
    if request.method == 'POST':
        form = BankReconciliationForm(request.POST)
        if form.is_valid():
            reconciliation = form.save(commit=False)
            reconciliation.created_by = request.user
            
            # حساب القيم التلقائية
            account = form.cleaned_data.get('account')
            reconciliation.system_balance = account.balance
            reconciliation.difference = form.cleaned_data.get('bank_balance') - account.balance
            
            reconciliation.save()
            
            # إجراء التسوية على الحساب
            success, message, difference = account.reconcile(
                form.cleaned_data.get('bank_balance'),
                form.cleaned_data.get('reconciliation_date')
            )
            
            if success:
                messages.success(request, f'تم إجراء التسوية البنكية بنجاح. {message}')
            else:
                messages.error(request, f'حدث خطأ أثناء إجراء التسوية: {message}')
            
            return redirect('financial:bank_reconciliation_list')
    else:
        form = BankReconciliationForm()
    
    context = {
        'form': form,
        'title': 'إنشاء تسوية بنكية',
    }
    
    return render(request, 'financial/bank_reconciliation_form.html', context)


@login_required
def ledger_report(request):
    """
    تقرير دفتر الأستاذ العام
    """
    transactions = []
    accounts = Account.objects.filter(is_active=True).order_by('account_type', 'name')
    
    # فلترة
    account_id = request.GET.get('account')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # في حالة تحديد حساب معين، نعرض التفاصيل من خلال بنود المعاملات
    if account_id:
        account = get_object_or_404(Account, id=account_id)
        transaction_lines = TransactionLine.objects.filter(account=account).select_related('transaction')
        
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            transaction_lines = transaction_lines.filter(transaction__date__gte=date_from)
        
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            transaction_lines = transaction_lines.filter(transaction__date__lte=date_to)
        
        transactions = transaction_lines.order_by('transaction__date', 'transaction__id')
        
        # حساب المجاميع
        total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
        balance = total_debit - total_credit
        
        context = {
            'account': account,
            'transactions': transactions,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'balance': balance,
            'accounts': accounts,
            'date_from': date_from,
            'date_to': date_to,
            'title': f'دفتر الأستاذ - {account.name}',
        }
    else:
        # إذا لم يتم تحديد حساب، نعرض ملخص لكل الحسابات
        account_balances = []
        
        for account in accounts:
            # حساب الإجماليات لكل حساب
            transaction_lines = TransactionLine.objects.filter(account=account)
            
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                transaction_lines = transaction_lines.filter(transaction__date__gte=date_from)
            
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                transaction_lines = transaction_lines.filter(transaction__date__lte=date_to)
            
            total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
            total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
            
            # حساب الرصيد النهائي حسب نوع الحساب
            if account.account_type in ['asset', 'expense']:
                # الأصول والمصروفات لها رصيد مدين
                balance = total_debit - total_credit
            else:
                # الخصوم والإيرادات وحقوق الملكية لها رصيد دائن
                balance = total_credit - total_debit
            
            if total_debit > 0 or total_credit > 0:  # عرض الحسابات النشطة فقط
                account_balances.append({
                    'account': account,
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'balance': balance
                })
        
        context = {
            'account_balances': account_balances,
            'accounts': accounts,
            'date_from': date_from,
            'date_to': date_to,
            'title': 'دفتر الأستاذ العام',
        }
    
    return render(request, 'financial/ledger_report.html', context)


@login_required
def balance_sheet(request):
    """
    تقرير الميزانية العمومية
    """
    # تحديد تاريخ الميزانية (افتراضيًا التاريخ الحالي)
    balance_date = request.GET.get('date')
    if balance_date:
        balance_date = datetime.strptime(balance_date, '%Y-%m-%d').date()
    else:
        balance_date = timezone.now().date()
    
    # جمع الأصول
    assets = []
    assets_total = 0
    asset_accounts = Account.objects.filter(account_type='asset', is_active=True)
    
    for account in asset_accounts:
        transaction_lines = TransactionLine.objects.filter(
            account=account,
            transaction__date__lte=balance_date
        )
        
        total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
        balance = total_debit - total_credit
        
        if balance != 0:  # عرض الحسابات ذات الرصيد فقط
            assets.append({
                'account': account,
                'balance': balance
            })
            assets_total += balance
    
    # جمع الخصوم
    liabilities = []
    liabilities_total = 0
    liability_accounts = Account.objects.filter(account_type='liability', is_active=True)
    
    for account in liability_accounts:
        transaction_lines = TransactionLine.objects.filter(
            account=account,
            transaction__date__lte=balance_date
        )
        
        total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
        balance = total_credit - total_debit  # الخصوم لها رصيد دائن
        
        if balance != 0:  # عرض الحسابات ذات الرصيد فقط
            liabilities.append({
                'account': account,
                'balance': balance
            })
            liabilities_total += balance
    
    # جمع حقوق الملكية
    equity = []
    equity_total = 0
    equity_accounts = Account.objects.filter(account_type='equity', is_active=True)
    
    for account in equity_accounts:
        transaction_lines = TransactionLine.objects.filter(
            account=account,
            transaction__date__lte=balance_date
        )
        
        total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
        balance = total_credit - total_debit  # حقوق الملكية لها رصيد دائن
        
        if balance != 0:  # عرض الحسابات ذات الرصيد فقط
            equity.append({
                'account': account,
                'balance': balance
            })
            equity_total += balance
    
    # حساب صافي الربح/الخسارة من حسابات الإيرادات والمصروفات
    # (يتم حسابه فقط إذا كان تاريخ الميزانية العمومية هو تاريخ اليوم)
    net_income = 0
    if balance_date == timezone.now().date():
        # حساب إجمالي الإيرادات
        income_accounts = Account.objects.filter(account_type='income', is_active=True)
        total_income = 0
        
        for account in income_accounts:
            transaction_lines = TransactionLine.objects.filter(
                account=account,
                transaction__date__lte=balance_date
            )
            
            total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
            total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
            balance = total_credit - total_debit  # الإيرادات لها رصيد دائن
            total_income += balance
        
        # حساب إجمالي المصروفات
        expense_accounts = Account.objects.filter(account_type='expense', is_active=True)
        total_expense = 0
        
        for account in expense_accounts:
            transaction_lines = TransactionLine.objects.filter(
                account=account,
                transaction__date__lte=balance_date
            )
            
            total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
            total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
            balance = total_debit - total_credit  # المصروفات لها رصيد مدين
            total_expense += balance
        
        net_income = total_income - total_expense
        
        # إضافة صافي الربح/الخسارة إلى حقوق الملكية
        if net_income != 0:
            equity.append({
                'account': {'name': 'صافي الربح/الخسارة'},
                'balance': net_income
            })
            equity_total += net_income
    
    # إجماليات الميزانية
    total_assets = assets_total
    total_liabilities_equity = liabilities_total + equity_total
    
    context = {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': total_assets,
        'total_liabilities': liabilities_total,
        'total_equity': equity_total,
        'total_liabilities_equity': total_liabilities_equity,
        'balance_date': balance_date,
        'title': 'الميزانية العمومية',
    }
    
    return render(request, 'financial/balance_sheet.html', context)


@login_required
def income_statement(request):
    """
    تقرير قائمة الإيرادات والمصروفات (الأرباح والخسائر)
    """
    # تحديد فترة التقرير
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    else:
        # افتراضيًا، بداية الشهر الحالي
        today = timezone.now().date()
        date_from = datetime(today.year, today.month, 1).date()
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        # افتراضيًا، تاريخ اليوم
        date_to = timezone.now().date()
    
    # جمع الإيرادات
    income_items = []
    total_income = 0
    income_accounts = Account.objects.filter(account_type='income', is_active=True)
    
    for account in income_accounts:
        transaction_lines = TransactionLine.objects.filter(
            account=account,
            transaction__date__gte=date_from,
            transaction__date__lte=date_to
        )
        
        total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
        balance = total_credit - total_debit  # الإيرادات لها رصيد دائن
        
        if balance != 0:  # عرض الحسابات ذات الرصيد فقط
            income_items.append({
                'account': account,
                'amount': balance
            })
            total_income += balance
    
    # جمع المصروفات
    expense_items = []
    total_expense = 0
    expense_accounts = Account.objects.filter(account_type='expense', is_active=True)
    
    for account in expense_accounts:
        transaction_lines = TransactionLine.objects.filter(
            account=account,
            transaction__date__gte=date_from,
            transaction__date__lte=date_to
        )
        
        total_debit = transaction_lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = transaction_lines.aggregate(Sum('credit'))['credit__sum'] or 0
        balance = total_debit - total_credit  # المصروفات لها رصيد مدين
        
        if balance != 0:  # عرض الحسابات ذات الرصيد فقط
            expense_items.append({
                'account': account,
                'amount': balance
            })
            total_expense += balance
    
    # حساب صافي الربح/الخسارة
    net_income = total_income - total_expense
    
    context = {
        'income_items': income_items,
        'expense_items': expense_items,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_income': net_income,
        'date_from': date_from,
        'date_to': date_to,
        'title': 'قائمة الإيرادات والمصروفات',
    }
    
    return render(request, 'financial/income_statement.html', context)


@login_required
def financial_analytics(request):
    """
    عرض صفحة التحليلات المالية
    تعرض مجموعة من المؤشرات المالية الرئيسية والرسوم البيانية
    """
    # التحقق من تسجيل دخول المستخدم
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    # بيانات لوحة التحكم
    monthly_income = Transaction.objects.filter(
        transaction_type='income',
        date__gte=datetime.now().replace(day=1, hour=0, minute=0, second=0)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # حساب هامش الربح (يمكن تعديله حسب منطق العمل الخاص بك)
    total_income = Transaction.objects.filter(
        transaction_type='income',
        date__gte=datetime.now().replace(day=1, hour=0, minute=0, second=0) - timedelta(days=30)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_expenses = Transaction.objects.filter(
        transaction_type='expense',
        date__gte=datetime.now().replace(day=1, hour=0, minute=0, second=0) - timedelta(days=30)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    profit_margin = 0
    if total_income > 0:
        profit_margin = round(((total_income - total_expenses) / total_income) * 100)
    
    # متوسط قيمة الفاتورة
    recent_transactions = Transaction.objects.filter(
        date__gte=datetime.now() - timedelta(days=30)
    )
    
    transaction_count = recent_transactions.count()
    total_amount = recent_transactions.aggregate(total=Sum('amount'))['total'] or 0
    
    avg_invoice = 0
    if transaction_count > 0:
        avg_invoice = total_amount / transaction_count
    
    # المعاملات اليومية
    daily_transactions = Transaction.objects.filter(
        date__gte=datetime.now() - timedelta(days=1)
    ).count()
    
    # إعداد سياق البيانات
    context = {
        'page_title': _('التحليلات المالية'),
        'page_icon': 'fas fa-chart-line',
        'monthly_income': monthly_income,
        'profit_margin': profit_margin,
        'avg_invoice': avg_invoice,
        'daily_transactions': daily_transactions
    }
    
    return render(request, 'financial/analytics.html', context)


@login_required
def category_list(request):
    """
    عرض قائمة فئات المصروفات والإيرادات
    """
    # استخراج معلمات البحث
    search_query = request.GET.get('search', '')
    category_type = request.GET.get('type', '')
    
    # تحضير الاستعلام الأساسي
    categories = Category.objects.all().order_by('type', 'name')
    
    # تطبيق الفلترة حسب النوع إذا تم تحديده
    if category_type:
        categories = categories.filter(type=category_type)
    
    # تطبيق البحث إذا تم إدخال نص
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # حساب إحصائيات الفئات
    expense_count = Category.objects.filter(type='expense').count()
    income_count = Category.objects.filter(type='income').count()
    
    # ترقيم الصفحات
    paginator = Paginator(categories, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'categories': page_obj,
        'expense_count': expense_count,
        'income_count': income_count,
        'search_query': search_query,
        'category_type': category_type,
        'page_title': 'فئات المصروفات والإيرادات',
        'page_icon': 'fas fa-tags',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'فئات المصروفات والإيرادات', 'active': True}
        ],
    }
    
    return render(request, 'financial/category_list.html', context)


@login_required
def category_create(request):
    """
    إنشاء فئة جديدة
    """
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            
            messages.success(request, 'تم إنشاء الفئة بنجاح.')
            return redirect('financial:category_list')
    else:
        form = CategoryForm()
        
        # تعيين النوع بناءً على المعلمة في URL
        category_type = request.GET.get('type', '')
        if category_type in ('expense', 'income'):
            form.fields['type'].initial = category_type
    
    context = {
        'form': form,
        'page_title': 'إضافة فئة جديدة',
        'page_icon': 'fas fa-plus-circle',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'فئات المصروفات والإيرادات', 'url': reverse('financial:category_list'), 'icon': 'fas fa-tags'},
            {'title': 'إضافة فئة جديدة', 'active': True}
        ],
    }
    
    return render(request, 'financial/category_form.html', context)


@login_required
def category_edit(request, pk):
    """
    تعديل فئة موجودة
    """
    category = get_object_or_404(Category, pk=pk)
    
    # حساب عدد المعاملات المرتبطة بهذه الفئة
    transaction_count = 0
    if category.type == 'expense':
        transaction_count = Expense.objects.filter(category=category).count()
    elif category.type == 'income':
        transaction_count = Income.objects.filter(category=category).count()
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تعديل الفئة بنجاح.')
            return redirect('financial:category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'transaction_count': transaction_count,
        'page_title': f'تعديل فئة: {category.name}',
        'page_icon': 'fas fa-edit',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'فئات المصروفات والإيرادات', 'url': reverse('financial:category_list'), 'icon': 'fas fa-tags'},
            {'title': f'تعديل فئة: {category.name}', 'active': True}
        ],
    }
    
    return render(request, 'financial/category_form.html', context)


@login_required
def category_delete(request, pk):
    """
    حذف فئة
    """
    category = get_object_or_404(Category, pk=pk)
    
    # التحقق من استخدام الفئة في المعاملات
    has_transactions = False
    transaction_count = 0
    
    if category.type == 'expense':
        transaction_count = Expense.objects.filter(category=category).count()
        has_transactions = transaction_count > 0
    elif category.type == 'income':
        transaction_count = Income.objects.filter(category=category).count()
        has_transactions = transaction_count > 0
    
    if request.method == 'POST':
        # إذا تم تأكيد الحذف
        confirm_deletion = request.POST.get('confirm_deletion') == 'on' if has_transactions else True
        
        if confirm_deletion:
            category_name = category.name
            category.delete()
            messages.success(request, f'تم حذف الفئة "{category_name}" بنجاح.')
            return redirect('financial:category_list')
        else:
            messages.error(request, 'يجب تأكيد الحذف للفئات المستخدمة في معاملات.')
    
    context = {
        'category': category,
        'has_transactions': has_transactions,
        'transaction_count': transaction_count,
        'page_title': f'حذف فئة: {category.name}',
        'page_icon': 'fas fa-trash',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الإدارة المالية', 'url': '#', 'icon': 'fas fa-money-bill-wave'},
            {'title': 'فئات المصروفات والإيرادات', 'url': reverse('financial:category_list'), 'icon': 'fas fa-tags'},
            {'title': f'حذف فئة: {category.name}', 'active': True}
        ],
    }
    
    return render(request, 'financial/category_delete.html', context)
