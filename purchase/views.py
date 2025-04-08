from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from purchase.models import Purchase, PurchasePayment, PurchaseItem, PurchaseReturn, PurchaseReturnItem, PurchaseOrder, PurchaseOrderItem
from .forms import PurchaseForm, PurchaseItemForm, PurchasePaymentForm, PurchaseReturnForm, PurchaseUpdateForm
from product.models import Product, Stock, StockMovement
from decimal import Decimal
import logging
from django.db import models
from django.core.paginator import Paginator
from django.db.models import Sum
from supplier.models import Supplier
from datetime import datetime

logger = logging.getLogger(__name__)


@login_required
def purchase_list(request):
    """
    عرض قائمة فواتير المشتريات
    """
    # الاستعلام الأساسي مع ترتيب تنازلي حسب التاريخ ثم الرقم
    purchases_query = Purchase.objects.all().order_by('-date', '-id')
    
    # تصفية حسب المورد
    supplier = request.GET.get('supplier')
    if supplier:
        purchases_query = purchases_query.filter(supplier_id=supplier)
    
    # تصفية حسب حالة الدفع
    payment_status = request.GET.get('payment_status')
    if payment_status:
        purchases_query = purchases_query.filter(payment_status=payment_status)
    
    # تصفية حسب التاريخ
    date_from = request.GET.get('date_from')
    if date_from:
        purchases_query = purchases_query.filter(date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        purchases_query = purchases_query.filter(date__lte=date_to)
    
    # التصفح والترقيم
    paginator = Paginator(purchases_query, 25)  # 25 فاتورة في كل صفحة
    page = request.GET.get('page')
    purchases = paginator.get_page(page)
    
    # إحصائيات للعرض في الصفحة
    paid_purchases_count = Purchase.objects.filter(payment_status='paid').count()
    partially_paid_purchases_count = Purchase.objects.filter(payment_status='partially_paid').count()
    unpaid_purchases_count = Purchase.objects.filter(payment_status='unpaid').count()
    
    # عدد الفواتير المرتجعة
    returned_purchases_count = Purchase.objects.filter(returns__status='confirmed').distinct().count()
    
    # إجمالي المشتريات
    total_amount = Purchase.objects.aggregate(Sum('total'))['total__sum'] or 0
    
    # الحصول على قائمة الموردين للفلترة
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    # تعريف عناوين أعمدة الجدول
    purchase_headers = [
        {'key': 'number', 'label': _('رقم الفاتورة'), 'sortable': True, 'class': 'text-center', 'format': 'reference', 'variant': 'highlight-code', 'app': 'purchase'},
        {'key': 'date', 'label': _('التاريخ'), 'sortable': True, 'class': 'text-center', 'format': 'date'},
        {'key': 'supplier.name', 'label': _('المورد'), 'sortable': True},
        {'key': 'warehouse.name', 'label': _('المستودع'), 'sortable': True},
        {'key': 'total', 'label': _('الإجمالي'), 'sortable': True, 'class': 'text-center', 'format': 'currency', 'decimals': 2},
        {'key': 'payment_method', 'label': _('طريقة الدفع'), 'sortable': True, 'class': 'text-center', 'format': 'status'},
        {'key': 'payment_status', 'label': _('حالة الدفع'), 'sortable': True, 'class': 'text-center', 'format': 'status'},
        {'key': 'return_status', 'label': _('حالة الإرجاع'), 'sortable': True, 'class': 'text-center', 'format': 'status'}
    ]

    # تعريف أزرار الإجراءات للجدول
    purchase_actions = [
        {'url': 'purchase:purchase_detail', 'icon': 'fa-eye', 'label': _('عرض'), 'class': 'action-view'},
        {'url': 'purchase:purchase_edit', 'icon': 'fa-edit', 'label': _('تعديل'), 'class': 'action-edit'},
        {'url': 'purchase:purchase_delete', 'icon': 'fa-trash', 'label': _('حذف'), 'class': 'action-delete'},
        {'url': 'purchase:purchase_print', 'icon': 'fa-print', 'label': _('طباعة'), 'class': 'action-print'},
        {'url': 'purchase:purchase_return', 'icon': 'fa-undo', 'label': _('مرتجع'), 'class': 'action-return'}
    ]
    
    context = {
        'purchases': purchases,
        'paid_purchases_count': paid_purchases_count,
        'partially_paid_purchases_count': partially_paid_purchases_count,
        'unpaid_purchases_count': unpaid_purchases_count,
        'returned_purchases_count': returned_purchases_count,
        'total_amount': total_amount,
        'suppliers': suppliers,
        'purchase_headers': purchase_headers,
        'purchase_actions': purchase_actions,
        'page_title': 'فواتير المشتريات',
        'page_icon': 'fas fa-shopping-cart',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المشتريات', 'url': '#', 'icon': 'fas fa-truck'},
            {'title': 'فواتير المشتريات', 'active': True}
        ],
    }
    
    return render(request, 'purchase/purchase_list.html', context)


@login_required
def purchase_create(request):
    """
    إنشاء فاتورة مشتريات جديدة
    """
    products = Product.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # إنشاء فاتورة المشتريات
                    purchase = form.save(commit=False)
                    purchase.subtotal = Decimal(request.POST.get('subtotal', 0))
                    purchase.total = Decimal(request.POST.get('total', 0))
                    purchase.created_by = request.user
                    purchase.save()
                    
                    # إضافة بنود الفاتورة
                    product_ids = request.POST.getlist('product[]')
                    quantities = request.POST.getlist('quantity[]')
                    unit_prices = request.POST.getlist('unit_price[]')
                    discounts = request.POST.getlist('discount[]')
                    
                    # حذف جميع حركات المخزون المرتبطة بهذه الفاتورة أولاً للتأكد من عدم التكرار
                    StockMovement.objects.filter(
                        reference_number__startswith=f"PURCHASE-{purchase.number}"
                    ).delete()
                    
                    # تعريف رقم المرجع الرئيسي
                    main_reference = f"PURCHASE-{purchase.number}"
                    
                    for i in range(len(product_ids)):
                        if product_ids[i]:  # تخطي الصفوف الفارغة
                            product = get_object_or_404(Product, id=product_ids[i])
                            quantity = int(float(quantities[i]))
                            unit_price = Decimal(unit_prices[i])
                            discount = Decimal(discounts[i]) if discounts[i] else Decimal('0')
                            
                            # إنشاء بند فاتورة
                            item = PurchaseItem(
                                purchase=purchase,
                                product=product,
                                quantity=quantity,
                                unit_price=unit_price,
                                discount=discount,
                                total=(Decimal(quantity) * unit_price) - discount
                            )
                            item.save()
                    
                    # بعد إنشاء جميع البنود، قم بإنشاء حركات المخزون
                    for item in purchase.items.all():
                        # استخدام معرف البند في الرقم المرجعي بدلاً من معرف المنتج لضمان عدم التكرار
                        reference_id = f"{main_reference}-ITEM{item.id}" 
                        
                        # تحقق من وجود حركة مخزون مسبقة بنفس الرقم المرجعي
                        if not StockMovement.objects.filter(
                            reference_number=reference_id
                        ).exists():
                            # الحصول على المخزون الحالي
                            stock, created = Stock.objects.get_or_create(
                                product=item.product,
                                warehouse=purchase.warehouse,
                                defaults={'quantity': Decimal('0')}
                            )
                            
                            # تخزين قيمة المخزون قبل التحديث
                            quantity_before = stock.quantity
                            
                            # تحديث المخزون يدوياً - تحويل قيمة العنصر إلى Decimal لتجنب خطأ عدم توافق الأنواع
                            stock.quantity += Decimal(item.quantity)
                            stock.save()
                            
                            # تخزين قيمة المخزون بعد التحديث
                            quantity_after = stock.quantity
                            
                            # إنشاء حركة المخزون مع تعطيل التحديث التلقائي
                            movement = StockMovement(
                                product=item.product,
                                warehouse=purchase.warehouse,
                                movement_type='in',
                                quantity=item.quantity,
                                reference_number=reference_id,
                                document_type='purchase',
                                document_number=purchase.number,
                                notes=f'استلام من فاتورة المشتريات رقم {purchase.number}',
                                created_by=request.user,
                                quantity_before=quantity_before,
                                quantity_after=quantity_after
                            )
                            movement._skip_update = True  # تعطيل تحديث المخزون التلقائي
                            movement.save()
                    
                    messages.success(request, 'تم إنشاء فاتورة المشتريات بنجاح')
                    return redirect('purchase:purchase_list')
            
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء إنشاء الفاتورة: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء الموجودة في النموذج')
    else:
        # إنشاء رقم فاتورة مشتريات جديد
        last_purchase = Purchase.objects.order_by('-id').first()
        next_number = f"PUR{(last_purchase.id + 1 if last_purchase else 1):04d}"
        
        initial_data = {
            'date': timezone.now().date(),
            'number': next_number,
        }
        form = PurchaseForm(initial=initial_data)
    
    # إضافة متغيرات عنوان الصفحة
    context = {
        'form': form,
        'products': products,
        'page_title': 'إضافة فاتورة مشتريات',
        'page_icon': 'fas fa-plus-circle',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المشتريات', 'url': reverse('purchase:purchase_list'), 'icon': 'fas fa-shopping-bag'},
            {'title': 'إضافة فاتورة', 'active': True}
        ]
    }
    
    return render(request, 'purchase/purchase_form.html', context)


@login_required
def purchase_order_list(request):
    """
    عرض قائمة طلبات الشراء
    """
    purchase_orders = PurchaseOrder.objects.all().order_by('-date', '-id')
    
    # إضافة متغيرات عنوان الصفحة
    context = {
        'purchase_orders': purchase_orders,
        'page_title': 'طلبات الشراء',
        'page_icon': 'fas fa-clipboard-list',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المشتريات', 'url': '#', 'icon': 'fas fa-shopping-bag'},
            {'title': 'طلبات الشراء', 'active': True}
        ]
    }
    
    return render(request, 'purchase/purchase_order_list.html', context)


@login_required
def purchase_order_detail(request, pk):
    """
    عرض تفاصيل طلب الشراء
    """
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    # إضافة متغيرات عنوان الصفحة
    context = {
        'purchase_order': purchase_order,
        'page_title': f'طلب شراء - {purchase_order.number}',
        'page_icon': 'fas fa-clipboard-list',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المشتريات', 'url': '#', 'icon': 'fas fa-shopping-bag'},
            {'title': 'طلبات الشراء', 'url': reverse('purchase:purchase_order_list'), 'icon': 'fas fa-clipboard-list'},
            {'title': f'طلب شراء {purchase_order.number}', 'active': True}
        ]
    }
    
    return render(request, 'purchase/purchase_order_detail.html', context)


@login_required
def purchase_payment_list(request):
    """
    عرض قائمة مدفوعات فواتير المشتريات
    """
    payments = PurchasePayment.objects.all()
    
    # فلترة حسب طريقة الدفع
    if 'payment_method' in request.GET and request.GET['payment_method']:
        payments = payments.filter(payment_method=request.GET['payment_method'])
    
    # فلترة حسب التاريخ
    if 'start_date' in request.GET and request.GET['start_date']:
        payments = payments.filter(payment_date__gte=request.GET['start_date'])
    
    if 'end_date' in request.GET and request.GET['end_date']:
        payments = payments.filter(payment_date__lte=request.GET['end_date'])
    
    # فرز النتائج
    payments = payments.order_by('-payment_date', '-id')
    
    context = {
        'payments': payments,
        'title': 'مدفوعات المشتريات',
    }
    
    return render(request, 'purchase/payment_list.html', context)


@login_required
def purchase_order_create(request):
    """
    إنشاء أمر شراء جديد
    """
    products = Product.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        # هنا سيتم إضافة منطق معالجة النموذج
        pass
    else:
        # إنشاء رقم أمر شراء جديد
        last_order = PurchaseOrder.objects.order_by('-id').first()
        next_number = f"PO{(last_order.id + 1 if last_order else 1):04d}"
        
        initial_data = {
            'date': timezone.now().date(),
            'number': next_number,
        }
        # هنا سيتم إضافة منطق عرض النموذج
        
    context = {
        'products': products,
        'title': 'إضافة أمر شراء جديد',
    }
    
    return render(request, 'purchase/purchase_order_form.html', context)


@login_required
def purchase_detail(request, pk):
    """
    عرض تفاصيل فاتورة المشتريات
    """
    purchase = get_object_or_404(Purchase, pk=pk)
    context = {
        'purchase': purchase,
        'title': 'تفاصيل فاتورة المشتريات',
        'page_title': f'فاتورة مشتريات - {purchase.number}',
        'page_icon': 'fas fa-file-invoice',
        'breadcrumb_items': [
            {'title': 'لوحة التحكم', 'url': reverse('core:dashboard'), 'icon': 'fas fa-tachometer-alt'},
            {'title': 'المشتريات', 'url': reverse('purchase:purchase_list'), 'icon': 'fas fa-shopping-basket'},
            {'title': f'فاتورة {purchase.number}', 'active': True},
        ],
    }
    return render(request, 'purchase/purchase_detail.html', context)


@login_required
def purchase_update(request, pk):
    """
    تعديل فاتورة مشتريات
    """
    purchase = get_object_or_404(Purchase, pk=pk)
    products = Product.objects.filter(is_active=True)
    
    # منع تعديل الفواتير المدفوعة أو المرتجعة بالكامل
    if purchase.is_fully_paid or purchase.return_status == 'full':
        messages.error(request, _('لا يمكن تعديل فاتورة مدفوعة أو مرتجعة بالكامل'))
        return redirect('purchase:purchase_detail', pk=pk)
    
    # حفظ البنود الحالية للفاتورة قبل التعديل للاستفادة منها لاحقاً
    original_items = {}
    for item in purchase.items.all():
        original_items[item.product_id] = item.quantity
    
    if request.method == 'POST':
        form = PurchaseUpdateForm(request.POST, instance=purchase)
        
        # تسجيل البيانات للتحقق
        logger.info(f"Form data: {request.POST}")
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    updated_purchase = form.save(commit=False)
                    
                    # الحصول على قيمة الضريبة من النموذج (إذا كانت مقدمة) وتحويلها إلى Decimal
                    tax_value = Decimal(form.cleaned_data.get('tax', 0) or 0)
                    
                    # معالجة بنود الفاتورة
                    product_ids = request.POST.getlist('product[]')
                    quantities = request.POST.getlist('quantity[]')
                    unit_prices = request.POST.getlist('unit_price[]')
                    discounts = request.POST.getlist('discount[]')
                    
                    # تتبع البنود المحفوظة لحذف أي بنود محذوفة
                    saved_item_ids = []
                    
                    # حساب المجموع الفرعي
                    subtotal = Decimal('0')
                    
                    # إنشاء قاموس للكميات الجديدة
                    new_items = {}
                    
                    # حفظ البنود
                    for i in range(len(product_ids)):
                        if not product_ids[i]:  # تخطي البنود الفارغة
                            continue
                            
                        product = get_object_or_404(Product, id=product_ids[i])
                        quantity = int(quantities[i])
                        unit_price = Decimal(unit_prices[i])
                        discount = Decimal(discounts[i] if discounts[i] else '0')
                        
                        # حساب إجمالي البند
                        item_total = (quantity * unit_price) - discount
                        subtotal += item_total
                        
                        # البحث عن البند الموجود أو إنشاء بند جديد
                        item, created = PurchaseItem.objects.update_or_create(
                            purchase=purchase,
                            product=product,
                            defaults={
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'discount': discount,
                                'total': item_total
                            }
                        )
                        
                        saved_item_ids.append(item.id)
                        # حفظ الكمية الجديدة في القاموس
                        new_items[product.id] = quantity
                    
                    # حذف البنود الغير موجودة في النموذج
                    PurchaseItem.objects.filter(purchase=purchase).exclude(id__in=saved_item_ids).delete()
                    
                    # تحديث المجموع الفرعي والإجمالي
                    updated_purchase.subtotal = subtotal
                    updated_purchase.tax = tax_value
                    updated_purchase.total = subtotal - Decimal(updated_purchase.discount) + tax_value
                    
                    # حفظ التعديلات
                    updated_purchase.save()
                    
                    # تعريف رقم المرجع الرئيسي
                    main_reference = f"PURCHASE-{updated_purchase.number}"
                    
                    # معالجة المنتجات المضافة أو التي تغيرت كميتها
                    for product_id, new_quantity in new_items.items():
                        original_quantity = original_items.get(product_id, 0)
                        quantity_diff = new_quantity - original_quantity
                        
                        if quantity_diff != 0:  # فقط إذا كان هناك تغيير في الكمية
                            product = Product.objects.get(id=product_id)
                            
                            # الحصول على المخزون الحالي
                            stock, created = Stock.objects.get_or_create(
                                product=product,
                                warehouse=updated_purchase.warehouse,
                                defaults={'quantity': 0}
                            )
                            
                            # تحديث المخزون يدوياً حسب اتجاه التغيير
                            if quantity_diff > 0:  # إذا زادت الكمية، نضيف الزيادة للمخزون
                                stock.quantity += quantity_diff
                                
                                # إنشاء حركة مخزون للإضافة
                                StockMovement.objects.create(
                                    product=product,
                                    warehouse=updated_purchase.warehouse,
                                    movement_type='in',
                                    quantity=quantity_diff,
                                    reference_number=f"{main_reference}-EDIT-IN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                                    document_type='purchase',
                                    document_number=updated_purchase.number,
                                    notes=f'زيادة كمية منتج في تعديل فاتورة مشتريات رقم {updated_purchase.number}',
                                    created_by=request.user
                                )
                            else:  # إذا قلت الكمية، نخصم الفرق من المخزون
                                stock.quantity -= abs(quantity_diff)
                                if stock.quantity < 0:
                                    stock.quantity = 0
                                
                                # إنشاء حركة مخزون للخصم
                                StockMovement.objects.create(
                                    product=product,
                                    warehouse=updated_purchase.warehouse,
                                    movement_type='out',
                                    quantity=abs(quantity_diff),
                                    reference_number=f"{main_reference}-EDIT-OUT-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                                    document_type='purchase',
                                    document_number=updated_purchase.number,
                                    notes=f'نقص كمية منتج في تعديل فاتورة مشتريات رقم {updated_purchase.number}',
                                    created_by=request.user
                                )
                            
                            stock.save()
                    
                    # معالجة المنتجات المحذوفة (المنتجات الموجودة في البنود القديمة وليست في البنود الجديدة)
                    for product_id, original_quantity in original_items.items():
                        if product_id not in new_items:  # إذا كان المنتج موجود سابقًا وتم حذفه
                            product = Product.objects.get(id=product_id)
                            
                            # الحصول على المخزون الحالي
                            stock, created = Stock.objects.get_or_create(
                                product=product,
                                warehouse=updated_purchase.warehouse,
                                defaults={'quantity': 0}
                            )
                            
                            # خصم الكمية المحذوفة من المخزون
                            stock.quantity -= original_quantity
                            if stock.quantity < 0:
                                stock.quantity = 0
                            stock.save()
                            
                            # إنشاء حركة مخزون للخصم
                            StockMovement.objects.create(
                                product=product,
                                warehouse=updated_purchase.warehouse,
                                movement_type='out',
                                quantity=original_quantity,
                                reference_number=f"{main_reference}-EDIT-DELETE-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                                document_type='purchase',
                                document_number=updated_purchase.number,
                                notes=f'حذف منتج من فاتورة مشتريات رقم {updated_purchase.number}',
                                created_by=request.user
                            )
                    
                    # تحديث مديونية المورد (يتم تنفيذه من خلال الإشارة في signals.py)
                    
                messages.success(request, _('تم تعديل فاتورة المشتريات بنجاح'))
                return redirect('purchase:purchase_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء تعديل الفاتورة: {str(e)}')
                logger.error(f"Error updating purchase: {str(e)}")
        else:
            # طباعة أخطاء النموذج بشكل مفصل
            logger.error(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"خطأ في الحقل {field}: {error}")
    else:
        form = PurchaseUpdateForm(instance=purchase)
    
    context = {
        'form': form,
        'purchase': purchase,
        'products': products,
        'title': 'تعديل فاتورة مشتريات',
        'page_title': f'تعديل فاتورة مشتريات - {purchase.number}',
        'page_icon': 'fas fa-edit',
    }
    
    return render(request, 'purchase/purchase_form.html', context)


@login_required
def purchase_delete(request, pk):
    """
    حذف فاتورة المشتريات
    """
    purchase = get_object_or_404(Purchase, pk=pk)
    
    # التحقق مما إذا كانت الفاتورة لها مرتجعات مؤكدة
    has_confirmed_returns = purchase.returns.filter(status='confirmed').exists()
    
    if has_confirmed_returns:
        messages.error(request, 'لا يمكن حذف الفاتورة لأنها تحتوي على مرتجعات مؤكدة')
        return redirect('purchase:purchase_detail', pk=purchase.pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # حساب عدد حركات المخزون المرتبطة بالفاتورة (للعرض فقط)
                movement_count = StockMovement.objects.filter(
                    reference_number__startswith=f"PURCHASE-{purchase.number}"
                ).count()
                
                # إنشاء حركات إرجاع للمخزون للإشارة إلى أن الفاتورة تم حذفها
                for item in purchase.items.all():
                    # إنشاء حركة مخزون جديدة للإرجاع (خصم كمية)
                    movement = StockMovement(
                        product=item.product,
                        warehouse=purchase.warehouse,
                        movement_type='return_out',
                        quantity=item.quantity,
                        reference_number=f"RETURN-DELETE-PURCHASE-{purchase.number}-ITEM{item.id}",
                        document_type='purchase_return',
                        document_number=purchase.number,
                        notes=f'إرجاع بسبب حذف فاتورة المشتريات رقم {purchase.number}',
                        created_by=request.user
                    )
                    movement.save()
                
                # لم نعد نحذف حركات المخزون
                # StockMovement.objects.filter(
                #     reference_number__startswith=f"PURCHASE-{purchase.number}"
                # ).delete()
                
                # حذف الفاتورة فقط
                purchase_number = purchase.number
                purchase.delete()
                
                messages.success(request, f'تم حذف فاتورة المشتريات {purchase_number} بنجاح مع إضافة حركات مخزون للإرجاع. تم الاحتفاظ بعدد {movement_count} من حركات المخزون للحفاظ على سجل المخزون')
                return redirect('purchase:purchase_list')
        
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف الفاتورة: {str(e)}')
            return redirect('purchase:purchase_detail', pk=purchase.pk)
    
    context = {
        'purchase': purchase,
        'title': f'حذف فاتورة المشتريات - {purchase.number}',
    }
    
    return render(request, 'purchase/purchase_confirm_delete.html', context)


@login_required
def purchase_print(request, pk):
    """
    طباعة فاتورة المشتريات
    """
    purchase = get_object_or_404(Purchase, pk=pk)
    today = timezone.now().date()
    year = timezone.now().year
    
    context = {
        'purchase': purchase,
        'title': f'طباعة فاتورة المشتريات - {purchase.number}',
        'today': today,
        'year': year,
    }
    
    return render(request, 'purchase/purchase_print.html', context)


@login_required
def add_payment(request, pk):
    """
    إضافة دفعة لفاتورة الشراء
    """
    purchase = get_object_or_404(Purchase, pk=pk)
    
    if request.method == 'POST':
        form = PurchasePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.purchase = purchase
            payment.created_by = request.user
            
            # تأكد من أن المبلغ لا يتجاوز المبلغ المستحق
            if payment.amount > purchase.amount_due:
                messages.warning(request, _('تم تقليل المبلغ إلى القيمة المستحقة المتبقية'))
                payment.amount = purchase.amount_due
            
            with transaction.atomic():
                # حفظ الدفعة
                payment.save()
                
                # تحديث حالة فاتورة الشراء
                purchase.refresh_from_db()
                if purchase.amount_due <= 0:
                    purchase.payment_status = 'paid'
                elif purchase.amount_paid > 0:
                    purchase.payment_status = 'partially_paid'
                purchase.save()
                
                # تحديث رصيد المورد
                purchase.supplier.balance -= payment.amount
                purchase.supplier.save()
            
            messages.success(request, _('تم تسجيل الدفعة بنجاح'))
            return redirect('purchase:purchase_detail', pk=purchase.pk)
    else:
        # تعبئة قيمة افتراضية للمبلغ (المبلغ المستحق)
        initial_data = {
            'amount': purchase.amount_due,
            'payment_date': datetime.now().date()
        }
        form = PurchasePaymentForm(initial=initial_data)
    
    context = {
        'invoice': purchase,  # استخدام invoice بدلاً من purchase للنموذج المشترك
        'form': form,
        'is_purchase': True,  # تحديد أن هذا نموذج دفع للمشتريات
        'page_title': f'إضافة دفعة لفاتورة المشتريات {purchase.number}',
        'title': f'إضافة دفعة لفاتورة المشتريات {purchase.number}',
        'page_icon': 'fas fa-money-bill-wave',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'فواتير المشتريات', 'url': reverse('purchase:purchase_list'), 'icon': 'fas fa-shopping-cart'},
            {'title': purchase.number, 'url': reverse('purchase:purchase_detail', kwargs={'pk': purchase.pk})},
            {'title': 'إضافة دفعة', 'active': True}
        ],
    }
    
    return render(request, 'purchase/purchase_payment_form.html', context)


@login_required
def purchase_return(request, pk):
    """
    إرجاع فاتورة المشتريات
    """
    purchase = get_object_or_404(Purchase, pk=pk)
    items = purchase.items.all()
    
    # الحصول على الكميات المرتجعة سابقاً لكل عنصر
    previously_returned_quantities = {}
    for item in items:
        returned_items = PurchaseReturnItem.objects.filter(
            purchase_item=item,
            purchase_return__status__in=['draft', 'confirmed']
        )
        previously_returned_quantities[item.id] = sum(returned_item.quantity for returned_item in returned_items)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # إنشاء مرتجع المشتريات
                return_data = {
                    'date': request.POST.get('date') or timezone.now().date(),
                    'warehouse': purchase.warehouse.id,  # استخدام نفس مخزن الفاتورة
                    'notes': request.POST.get('notes', '')
                }
                
                return_form = PurchaseReturnForm(return_data)
                if return_form.is_valid():
                    purchase_return = return_form.save(commit=False)
                    purchase_return.purchase = purchase
                    purchase_return.created_by = request.user
                    purchase_return.warehouse = purchase.warehouse  # استخدام نفس مخزن الفاتورة
                    
                    # تعيين قيم افتراضية للحقول المطلوبة
                    purchase_return.subtotal = 0
                    purchase_return.discount = 0
                    purchase_return.tax = 0
                    purchase_return.total = 0
                    
                    # تحديد رقم المرتجع
                    if not purchase_return.number:
                        from django.utils.crypto import get_random_string
                        purchase_return.number = f"RET-{get_random_string(6).upper()}"
                    
                    purchase_return.save()
                    
                    # إضافة بنود المرتجع
                    item_ids = request.POST.getlist('item_id')
                    return_quantities = request.POST.getlist('return_quantity')
                    return_reasons = request.POST.getlist('return_reason')
                    
                    valid_items = False  # التحقق من وجود منتجات مرتجعة
                    subtotal = 0
                    for i in range(len(item_ids)):
                        if not item_ids[i] or not return_quantities[i] or int(return_quantities[i]) <= 0:
                            continue  # تجاهل البنود الفارغة أو الصفرية
                        
                        try:
                            purchase_item = get_object_or_404(PurchaseItem, id=item_ids[i])
                            return_quantity = int(float(return_quantities[i]))
                            previously_returned = previously_returned_quantities.get(purchase_item.id, 0)
                            available_quantity = purchase_item.quantity - previously_returned
                            
                            return_reason = return_reasons[i] if i < len(return_reasons) and return_reasons[i] else "إرجاع بضاعة"
                            
                            # التأكد من أن الكمية المرتجعة لا تتجاوز الكمية المتبقية
                            if return_quantity > available_quantity:
                                messages.warning(request, f'تم تعديل الكمية المرتجعة للمنتج {purchase_item.product.name} إلى {available_quantity} (الكمية المتبقية المتاحة للإرجاع)')
                                return_quantity = available_quantity
                            
                            # تجاهل العناصر التي ليس لديها كمية متاحة للإرجاع
                            if return_quantity <= 0:
                                continue
                            
                            # إنشاء بند المرتجع
                            return_item = PurchaseReturnItem(
                                purchase_return=purchase_return,
                                purchase_item=purchase_item,
                                product=purchase_item.product,
                                quantity=return_quantity,
                                unit_price=purchase_item.unit_price,
                                discount=0,  # تعيين قيمة افتراضية
                                total=(return_quantity * purchase_item.unit_price),  # حساب الإجمالي
                                reason=return_reason
                            )
                            return_item.save()
                            
                            valid_items = True  # تم إنشاء بند واحد على الأقل بنجاح
                            
                            # تحديث المجموع
                            subtotal += return_item.total
                            
                            # إنشاء حركة مخزون صادر (مرتجع مشتريات)
                            StockMovement.objects.create(
                                product=purchase_item.product,
                                warehouse=purchase_return.warehouse,
                                movement_type='return_out',
                                quantity=return_quantity,
                                reference_number=f"RETURN-{purchase_return.number}-ITEM{return_item.id}",
                                document_type='purchase_return',
                                document_number=purchase_return.number,
                                notes=f'مرتجع مشتريات - {return_reason}',
                                created_by=request.user
                            )
                        except Exception as e:
                            logger.error(f"Error processing return item: {str(e)}")
                            continue
                    
                    if not valid_items:
                        # إذا لم يتم إضافة أي بنود صالحة، قم بإلغاء العملية
                        messages.error(request, 'يرجى تحديد كمية مرتجعة واحدة على الأقل')
                        raise Exception('لم يتم تحديد أي منتجات للإرجاع')
                    
                    # تحديث المرتجع
                    purchase_return.subtotal = subtotal
                    purchase_return.tax = 0  # إزالة الضريبة
                    purchase_return.total = subtotal  # الإجمالي يساوي المجموع الفرعي بدون ضريبة
                    purchase_return.save()
                    
                    messages.success(request, 'تم إنشاء مرتجع المشتريات بنجاح')
                    return redirect('purchase:purchase_detail', pk=purchase.pk)
                else:
                    for field, errors in return_form.errors.items():
                        for error in errors:
                            messages.error(request, f"خطأ في حقل {field}: {error}")
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء مرتجع المشتريات: {str(e)}')
            logger.error(f"Error creating purchase return: {str(e)}")
    
    # حساب الكميات المتبقية للعرض
    available_quantities = {}
    for item in items:
        available_quantities[item.id] = item.quantity - previously_returned_quantities.get(item.id, 0)
    
    context = {
        'title': 'مرتجع مشتريات',
        'purchase': purchase,
        'items': items,
        'available_quantities': available_quantities,
        'previously_returned_quantities': previously_returned_quantities,
        'has_returns': any(previously_returned_quantities.values()),
    }
    return render(request, 'purchase/purchase_return.html', context)


@login_required
def purchase_return_list(request):
    """
    عرض قائمة مرتجعات المشتريات
    """
    returns = PurchaseReturn.objects.all().order_by('-date', '-id')
    
    context = {
        'returns': returns,
        'page_title': 'مرتجعات المشتريات',
        'page_icon': 'fas fa-undo-alt',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المشتريات', 'url': reverse('purchase:purchase_list'), 'icon': 'fas fa-truck'},
            {'title': 'مرتجعات المشتريات', 'active': True}
        ],
    }
    
    return render(request, 'purchase/purchase_return_list.html', context)


@login_required
def purchase_return_detail(request, pk):
    """
    عرض تفاصيل مرتجع المشتريات
    """
    purchase_return = get_object_or_404(PurchaseReturn, pk=pk)
    
    context = {
        'purchase_return': purchase_return,
        'title': f'تفاصيل مرتجع المشتريات - {purchase_return.number}',
    }
    
    return render(request, 'purchase/purchase_return_detail.html', context)


@login_required
def purchase_return_confirm(request, pk):
    """
    تأكيد مرتجع المشتريات وتغيير حالته من مسودة إلى مؤكد
    """
    purchase_return = get_object_or_404(PurchaseReturn, pk=pk)
    
    # التأكد من أن المرتجع في حالة مسودة
    if purchase_return.status != 'draft':
        messages.error(request, 'لا يمكن تأكيد مرتجع تم تأكيده أو إلغاؤه من قبل')
        return redirect('purchase:purchase_return_detail', pk=purchase_return.pk)
    
    try:
        with transaction.atomic():
            # تحديث حالة المرتجع إلى مؤكد
            purchase_return.status = 'confirmed'
            purchase_return.save()
            
            # يمكن هنا إضافة أي إجراءات إضافية مثل تحديث حسابات المورد
            # أو إنشاء قيود محاسبية أو إرسال إشعارات للموردين المعنيين
            
            messages.success(request, 'تم تأكيد مرتجع المشتريات بنجاح')
    except Exception as e:
        logger.error(f"Error confirming purchase return: {str(e)}")
        messages.error(request, f'حدث خطأ أثناء تأكيد المرتجع: {str(e)}')
    
    return redirect('purchase:purchase_return_detail', pk=purchase_return.pk)


@login_required
def purchase_return_cancel(request, pk):
    """
    إلغاء مرتجع المشتريات وتغيير حالته إلى ملغي
    """
    purchase_return = get_object_or_404(PurchaseReturn, pk=pk)
    
    # التأكد من أن المرتجع في حالة مسودة
    if purchase_return.status != 'draft':
        messages.error(request, 'لا يمكن إلغاء مرتجع تم تأكيده أو إلغاؤه من قبل')
        return redirect('purchase:purchase_return_detail', pk=purchase_return.pk)
    
    try:
        with transaction.atomic():
            # تحديث حالة المرتجع إلى ملغي
            purchase_return.status = 'cancelled'
            purchase_return.save()
            
            # يمكن هنا إضافة أي إجراءات إضافية مثل عكس حركات المخزون المرتبطة بالمرتجع
            
            messages.success(request, 'تم إلغاء مرتجع المشتريات بنجاح')
    except Exception as e:
        logger.error(f"Error cancelling purchase return: {str(e)}")
        messages.error(request, f'حدث خطأ أثناء إلغاء المرتجع: {str(e)}')
    
    return redirect('purchase:purchase_return_detail', pk=purchase_return.pk)
