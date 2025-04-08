from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db import models, transaction
from django.db.models import Sum, Q
from django.urls import reverse

from .models import Supplier, SupplierPayment
from .forms import SupplierForm, SupplierPaymentForm
from purchase.models import Purchase, PurchaseItem


@login_required
def supplier_list(request):
    """
    عرض قائمة الموردين
    """
    # فلترة بناءً على المعايير
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    order_by = request.GET.get('order_by', 'balance')
    order_dir = request.GET.get('order_dir', 'desc')  # تنازلي افتراضيًا
    
    suppliers = Supplier.objects.all()
    
    if status == 'active':
        suppliers = suppliers.filter(is_active=True)
    elif status == 'inactive':
        suppliers = suppliers.filter(is_active=False)
        
    if search:
        suppliers = suppliers.filter(
            models.Q(name__icontains=search) | 
            models.Q(code__icontains=search) |
            models.Q(phone__icontains=search)
        )
    
    # ترتيب النتائج
    if order_by:
        order_field = order_by
        if order_dir == 'desc':
            order_field = f'-{order_by}'
        suppliers = suppliers.order_by(order_field)
    else:
        # ترتيب حسب الأعلى استحقاق افتراضيًا
        suppliers = suppliers.order_by('-balance')
    
    active_suppliers = suppliers.filter(is_active=True).count()
    total_debt = suppliers.aggregate(Sum('balance'))['balance__sum'] or 0
    total_purchases = 0  # قد تحتاج لحساب إجمالي المشتريات من موديل آخر
    
    # تعريف أعمدة الجدول
    headers = [
        {'key': 'name', 'label': 'اسم المورد', 'sortable': True, 'class': 'text-start'},
        {'key': 'code', 'label': 'الكود', 'sortable': True},
        {'key': 'phone', 'label': 'رقم الهاتف', 'sortable': False},
        {'key': 'email', 'label': 'البريد الإلكتروني', 'sortable': False},
        {'key': 'balance', 'label': 'الاستحقاق', 'sortable': True, 'format': 'currency', 'decimals': 2, 'variant': 'text-danger'},
        {'key': 'is_active', 'label': 'الحالة', 'sortable': True, 'format': 'boolean'},
    ]
    
    # تعريف أزرار الإجراءات
    action_buttons = [
        {'url': 'supplier:supplier_detail', 'icon': 'fa-eye', 'class': 'action-view', 'label': 'عرض'},
        {'url': 'supplier:supplier_edit', 'icon': 'fa-edit', 'class': 'action-edit', 'label': 'تعديل'},
        {'url': 'supplier:supplier_delete', 'icon': 'fa-trash', 'class': 'action-delete', 'label': 'حذف'},
        {'url': 'supplier:supplier_payment_add_for_supplier', 'icon': 'fa-money-bill-wave', 'class': 'action-success', 'label': 'إضافة دفعة'}
    ]
    
    context = {
        'suppliers': suppliers,
        'headers': headers,
        'action_buttons': action_buttons,
        'active_suppliers': active_suppliers,
        'total_debt': total_debt,
        'total_purchases': total_purchases,
        'page_title': 'قائمة الموردين',
        'page_icon': 'fas fa-truck',
        'current_order_by': order_by,
        'current_order_dir': order_dir,
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الموردين', 'active': True}
        ],
    }
    
    return render(request, 'supplier/supplier_list.html', context)


@login_required
def supplier_add(request):
    """
    إضافة مورد جديد
    """
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()
            messages.success(request, _('تم إضافة المورد بنجاح'))
            return redirect('supplier:supplier_list')
    else:
        form = SupplierForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة مورد جديد',
        'page_icon': 'fas fa-user-plus',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الموردين', 'url': reverse('supplier:supplier_list'), 'icon': 'fas fa-truck'},
            {'title': 'إضافة مورد', 'active': True}
        ],
    }
    
    return render(request, 'supplier/supplier_form.html', context)


@login_required
def supplier_edit(request, pk):
    """
    تعديل بيانات مورد
    """
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تعديل بيانات المورد بنجاح'))
            return redirect('supplier:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    
    context = {
        'form': form,
        'supplier': supplier,
        'page_title': f'تعديل بيانات المورد: {supplier.name}',
        'page_icon': 'fas fa-user-edit',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الموردين', 'url': reverse('supplier:supplier_list'), 'icon': 'fas fa-truck'},
            {'title': supplier.name, 'url': reverse('supplier:supplier_detail', kwargs={'pk': supplier.pk})},
            {'title': 'تعديل', 'active': True}
        ],
    }
    
    return render(request, 'supplier/supplier_form.html', context)


@login_required
def supplier_delete(request, pk):
    """
    حذف مورد (تعطيل)
    """
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.is_active = False
        supplier.save()
        messages.success(request, _('تم حذف المورد بنجاح'))
        return redirect('supplier:supplier_list')
    
    context = {
        'supplier': supplier,
        'page_title': f'حذف المورد: {supplier.name}',
        'page_icon': 'fas fa-user-times',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الموردين', 'url': reverse('supplier:supplier_list'), 'icon': 'fas fa-truck'},
            {'title': supplier.name, 'url': reverse('supplier:supplier_detail', kwargs={'pk': supplier.pk})},
            {'title': 'حذف', 'active': True}
        ],
    }
    
    return render(request, 'supplier/supplier_delete.html', context)


@login_required
def supplier_detail(request, pk):
    """
    عرض تفاصيل المورد والمدفوعات
    """
    supplier = get_object_or_404(Supplier, pk=pk)
    payments = supplier.payments.all().order_by('-payment_date')
    
    # جلب فواتير الشراء المرتبطة بالمورد
    purchases = Purchase.objects.filter(supplier=supplier).order_by('-date')
    purchases_count = purchases.count()
    
    # حساب إجمالي المشتريات
    total_purchases = purchases.aggregate(total=Sum('total'))['total'] or 0
    
    # حساب عدد المنتجات الفريدة في فواتير الشراء
    purchase_items = PurchaseItem.objects.filter(purchase__supplier=supplier)
    products_count = purchase_items.values('product').distinct().count()
    
    # تاريخ آخر معاملة
    last_transaction_date = None
    if payments.exists() or purchases.exists():
        last_payment_date = payments.first().payment_date if payments.exists() else None
        last_purchase_date = purchases.first().date if purchases.exists() else None
        
        if last_payment_date and last_purchase_date:
            last_transaction_date = max(last_payment_date, last_purchase_date)
        elif last_payment_date:
            last_transaction_date = last_payment_date
        else:
            last_transaction_date = last_purchase_date
    
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or 0
    
    # تجهيز بيانات المعاملات لكشف الحساب
    transactions = []
    
    # إضافة فواتير الشراء
    for purchase in purchases:
        transactions.append({
            'date': purchase.date,
            'reference': purchase.number,
            'type': 'purchase',
            'description': f'فاتورة شراء رقم {purchase.number}',
            'debit': purchase.total,
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
        'supplier': supplier,
        'payments': payments,
        'purchases': purchases,
        'purchases_count': purchases_count,
        'total_purchases': total_purchases,
        'products_count': products_count,
        'total_payments': total_payments,
        'last_transaction_date': last_transaction_date,
        'transactions': transactions,
        'page_title': f'بيانات المورد: {supplier.name}',
        'page_icon': 'fas fa-truck',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الموردين', 'url': reverse('supplier:supplier_list'), 'icon': 'fas fa-truck'},
            {'title': supplier.name, 'active': True}
        ],
    }
    
    return render(request, 'supplier/supplier_detail.html', context)


@login_required
def supplier_payment_add(request, supplier_id=None):
    """
    إضافة دفعة للمورد
    """
    supplier = None
    if supplier_id:
        supplier = get_object_or_404(Supplier, pk=supplier_id)
    
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            
            with transaction.atomic():
                payment.save()
                # تحديث رصيد المورد
                payment.supplier.balance -= payment.amount
                payment.supplier.save()
                
            messages.success(request, _('تم إضافة الدفعة بنجاح'))
            
            if supplier_id:
                return redirect('supplier:supplier_detail', pk=supplier_id)
            return redirect('supplier:supplier_list')
    else:
        initial = {}
        if supplier:
            initial['supplier'] = supplier
        form = SupplierPaymentForm(initial=initial)
    
    context = {
        'form': form,
        'supplier': supplier,
        'page_title': 'إضافة دفعة للمورد',
        'page_icon': 'fas fa-money-bill-wave',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'الموردين', 'url': reverse('supplier:supplier_list'), 'icon': 'fas fa-truck'},
        ],
    }

    # إضافة العنصر الأخير للمسار التفصيلي حسب وجود المورد
    if supplier:
        context['breadcrumb_items'].append({'title': supplier.name, 'url': reverse('supplier:supplier_detail', kwargs={'pk': supplier.pk})})
        context['breadcrumb_items'].append({'title': 'إضافة دفعة', 'active': True})
    else:
        context['breadcrumb_items'].append({'title': 'إضافة دفعة', 'active': True})
    
    return render(request, 'supplier/supplier_payment_form.html', context)
