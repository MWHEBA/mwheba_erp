from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse

from .models import Customer, CustomerPayment
from .forms import CustomerForm, CustomerPaymentForm
from sale.models import Sale

# Create your views here.

@login_required
def customer_list(request):
    """
    عرض قائمة العملاء
    """
    customers = Customer.objects.filter(is_active=True)
    active_customers = customers.filter(is_active=True).count()
    total_debt = customers.aggregate(Sum('balance'))['balance__sum'] or 0
    
    # تعريف أعمدة الجدول
    headers = [
        {'key': 'name', 'label': 'اسم العميل', 'sortable': True, 'class': 'text-start'},
        {'key': 'code', 'label': 'الكود', 'sortable': True},
        {'key': 'phone', 'label': 'رقم الهاتف', 'sortable': False},
        {'key': 'email', 'label': 'البريد الإلكتروني', 'sortable': False},
        {'key': 'balance', 'label': 'المديونية', 'sortable': True, 'format': 'currency', 'decimals': 2},
        {'key': 'is_active', 'label': 'الحالة', 'sortable': True, 'format': 'boolean'},
    ]
    
    # تعريف أزرار الإجراءات
    action_buttons = [
        {'url': 'client:customer_detail', 'icon': 'fa-eye', 'class': 'action-view', 'label': 'عرض'},
        {'url': 'client:customer_edit', 'icon': 'fa-edit', 'class': 'action-edit', 'label': 'تعديل'},
        {'url': 'client:customer_delete', 'icon': 'fa-trash', 'class': 'action-delete', 'label': 'حذف'},
        {'url': 'client:customer_payment_add_for_customer', 'icon': 'fa-money-bill-wave', 'class': 'action-success', 'label': 'إضافة دفعة'}
    ]
    
    context = {
        'customers': customers,
        'headers': headers,
        'action_buttons': action_buttons,
        'active_customers': active_customers,
        'total_debt': total_debt,
        'page_title': 'قائمة العملاء',
        'page_icon': 'fas fa-users',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'العملاء', 'active': True}
        ],
    }
    
    return render(request, 'client/customer_list.html', context)


@login_required
def customer_add(request):
    """
    إضافة عميل جديد
    """
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            messages.success(request, _('تم إضافة العميل بنجاح'))
            return redirect('client:customer_list')
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة عميل جديد',
        'page_icon': 'fas fa-user-plus',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'العملاء', 'url': reverse('client:customer_list'), 'icon': 'fas fa-users'},
            {'title': 'إضافة عميل', 'active': True}
        ],
    }
    
    return render(request, 'client/customer_form.html', context)


@login_required
def customer_edit(request, pk):
    """
    تعديل بيانات عميل
    """
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تعديل بيانات العميل بنجاح'))
            return redirect('client:customer_list')
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
        'page_title': f'تعديل بيانات العميل: {customer.name}',
        'page_icon': 'fas fa-user-edit',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'العملاء', 'url': reverse('client:customer_list'), 'icon': 'fas fa-users'},
            {'title': customer.name, 'url': reverse('client:customer_detail', kwargs={'pk': customer.pk})},
            {'title': 'تعديل', 'active': True}
        ],
    }
    
    return render(request, 'client/customer_form.html', context)


@login_required
def customer_delete(request, pk):
    """
    حذف عميل (تعطيل)
    """
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        customer.is_active = False
        customer.save()
        messages.success(request, _('تم حذف العميل بنجاح'))
        return redirect('client:customer_list')
    
    context = {
        'customer': customer,
        'page_title': f'حذف العميل: {customer.name}',
        'page_icon': 'fas fa-user-times',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'العملاء', 'url': reverse('client:customer_list'), 'icon': 'fas fa-users'},
            {'title': customer.name, 'url': reverse('client:customer_detail', kwargs={'pk': customer.pk})},
            {'title': 'حذف', 'active': True}
        ],
    }
    
    return render(request, 'client/customer_delete.html', context)


@login_required
def customer_detail(request, pk):
    """
    عرض تفاصيل العميل والمدفوعات
    """
    customer = get_object_or_404(Customer, pk=pk)
    payments = customer.payments.all().order_by('-payment_date')
    
    # جلب فواتير البيع المرتبطة بالعميل
    invoices = Sale.objects.filter(customer=customer).order_by('-date')
    invoices_count = invoices.count()
    
    # حساب إجمالي المبيعات
    total_sales = invoices.aggregate(total=Sum('total'))['total'] or 0
    
    # حساب عدد المنتجات الفريدة في فواتير البيع
    from sale.models import SaleItem
    from django.db.models import Count
    
    sale_items = SaleItem.objects.filter(sale__customer=customer)
    total_products = sale_items.values('product').distinct().count()
    
    # تاريخ آخر معاملة
    last_transaction_date = None
    if payments.exists() or invoices.exists():
        last_payment_date = payments.first().payment_date if payments.exists() else None
        last_invoice_date = invoices.first().date if invoices.exists() else None
        
        if last_payment_date and last_invoice_date:
            last_transaction_date = max(last_payment_date, last_invoice_date)
        elif last_payment_date:
            last_transaction_date = last_payment_date
        else:
            last_transaction_date = last_invoice_date
    
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or 0
    
    # تجهيز بيانات المعاملات لكشف الحساب
    transactions = []
    
    # إضافة الفواتير
    for invoice in invoices:
        transactions.append({
            'date': invoice.date,
            'reference': invoice.number,
            'type': 'invoice',
            'description': f'فاتورة بيع رقم {invoice.number}',
            'debit': invoice.total,
            'credit': 0,
            'balance': 0  # سيتم حسابه لاحقاً
        })
    
    # إضافة المدفوعات
    for payment in payments:
        transactions.append({
            'date': payment.payment_date,
            'reference': payment.reference_number,
            'type': 'payment',
            'description': f'دفعة {payment.get_payment_method_display()}',
            'debit': 0,
            'credit': payment.amount,
            'balance': 0  # سيتم حسابه لاحقاً
        })
    
    # ترتيب المعاملات حسب التاريخ (من الأقدم للأحدث)
    transactions.sort(key=lambda x: x['date'])
    
    # حساب الرصيد التراكمي
    running_balance = 0
    for transaction in transactions:
        running_balance = running_balance + transaction['debit'] - transaction['credit']
        transaction['balance'] = running_balance
    
    # عكس ترتيب المعاملات (من الأحدث للأقدم) للعرض
    transactions.reverse()
    
    context = {
        'customer': customer,
        'payments': payments,
        'invoices': invoices,
        'invoices_count': invoices_count,
        'total_payments': total_payments,
        'total_sales': total_sales,
        'total_products': total_products,
        'last_transaction_date': last_transaction_date,
        'transactions': transactions,
        'page_title': f'بيانات العميل: {customer.name}',
        'page_icon': 'fas fa-user',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'العملاء', 'url': reverse('client:customer_list'), 'icon': 'fas fa-users'},
            {'title': customer.name, 'active': True}
        ],
    }
    
    return render(request, 'client/customer_detail.html', context)


@login_required
def customer_payment_add(request, customer_id=None):
    """
    إضافة دفعة من العميل
    """
    customer = None
    if customer_id:
        customer = get_object_or_404(Customer, pk=customer_id)
    
    if request.method == 'POST':
        form = CustomerPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            
            with transaction.atomic():
                payment.save()
                # تحديث رصيد العميل
                payment.customer.balance -= payment.amount
                payment.customer.save()
                
            messages.success(request, _('تم إضافة الدفعة بنجاح'))
            
            if customer_id:
                return redirect('client:customer_detail', pk=customer_id)
            return redirect('client:customer_list')
    else:
        initial = {}
        if customer:
            initial['customer'] = customer
        form = CustomerPaymentForm(initial=initial)
    
    context = {
        'form': form,
        'customer': customer,
        'page_title': 'إضافة دفعة من العميل',
        'page_icon': 'fas fa-money-bill-wave',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'العملاء', 'url': reverse('client:customer_list'), 'icon': 'fas fa-users'},
        ],
    }

    # إضافة العنصر الأخير للمسار التفصيلي حسب وجود العميل
    if customer:
        context['breadcrumb_items'].append({'title': customer.name, 'url': reverse('client:customer_detail', kwargs={'pk': customer.pk})})
        context['breadcrumb_items'].append({'title': 'إضافة دفعة', 'active': True})
    else:
        context['breadcrumb_items'].append({'title': 'إضافة دفعة', 'active': True})
    
    return render(request, 'client/customer_payment_form.html', context)
