from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from sale.models import Sale, SaleItem, SalePayment, SaleReturn, SaleReturnItem
from .forms import SaleForm, SaleItemForm, SalePaymentForm, SaleReturnForm
from product.models import Product, Stock, StockMovement, Warehouse, SerialNumber
from django.db.models import Sum, F, Value, IntegerField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.template.loader import get_template
import logging
import random
from client.models import Customer
import datetime
from decimal import Decimal
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)


@login_required
def sale_list(request):
    """
    عرض قائمة فواتير المبيعات
    """
    # الاستعلام الأساسي مع ترتيب تنازلي حسب التاريخ ثم الرقم
    sales_query = Sale.objects.all().order_by('-date', '-id')
    
    # تصفية حسب العميل
    customer = request.GET.get('customer')
    if customer:
        sales_query = sales_query.filter(customer_id=customer)
    
    # تصفية حسب حالة الدفع
    payment_status = request.GET.get('payment_status')
    if payment_status:
        sales_query = sales_query.filter(payment_status=payment_status)
    
    # تصفية حسب التاريخ
    date_from = request.GET.get('date_from')
    if date_from:
        sales_query = sales_query.filter(date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        sales_query = sales_query.filter(date__lte=date_to)
    
    # التصفح والترقيم
    paginator = Paginator(sales_query, 25)  # 25 فاتورة في كل صفحة
    page = request.GET.get('page')
    sales = paginator.get_page(page)
    
    # إحصائيات للعرض في الصفحة
    paid_sales_count = Sale.objects.filter(payment_status='paid').count()
    partially_paid_sales_count = Sale.objects.filter(payment_status='partially_paid').count()
    unpaid_sales_count = Sale.objects.filter(payment_status='unpaid').count()
    
    # عدد الفواتير المرتجعة
    returned_sales_count = Sale.objects.filter(returns__status='confirmed').distinct().count()
    
    # إجمالي المبيعات
    total_amount = Sale.objects.aggregate(Sum('total'))['total__sum'] or 0
    
    # الحصول على قائمة العملاء للفلترة
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    # تعريف عناوين أعمدة الجدول
    sale_headers = [
        {'key': 'number', 'label': _('رقم الفاتورة'), 'sortable': True, 'class': 'text-center', 'format': 'reference', 'variant': 'highlight-code', 'app': 'sale'},
        {'key': 'date', 'label': _('التاريخ'), 'sortable': True, 'class': 'text-center', 'format': 'date'},
        {'key': 'customer.name', 'label': _('العميل'), 'sortable': True},
        {'key': 'warehouse.name', 'label': _('المستودع'), 'sortable': True},
        {'key': 'total', 'label': _('الإجمالي'), 'sortable': True, 'class': 'text-center', 'format': 'currency', 'decimals': 2},
        {'key': 'payment_method', 'label': _('طريقة الدفع'), 'sortable': True, 'class': 'text-center', 'format': 'status'},
        {'key': 'payment_status', 'label': _('حالة الدفع'), 'sortable': True, 'class': 'text-center', 'format': 'status'},
        {'key': 'return_status', 'label': _('حالة الإرجاع'), 'sortable': True, 'class': 'text-center', 'format': 'status'}
    ]

    # تعريف أزرار الإجراءات للجدول
    sale_actions = [
        {'url': 'sale:sale_detail', 'icon': 'fa-eye', 'label': _('عرض'), 'class': 'action-view'},
        {'url': 'sale:sale_edit', 'icon': 'fa-edit', 'label': _('تعديل'), 'class': 'action-edit'},
        {'url': 'sale:sale_delete', 'icon': 'fa-trash', 'label': _('حذف'), 'class': 'action-delete'},
        {'url': 'sale:sale_print', 'icon': 'fa-print', 'label': _('طباعة'), 'class': 'action-print'},
        {'url': 'sale:sale_return', 'icon': 'fa-undo', 'label': _('مرتجع'), 'class': 'action-return'}
    ]
    
    context = {
        'sales': sales,
        'paid_sales_count': paid_sales_count,
        'partially_paid_sales_count': partially_paid_sales_count,
        'unpaid_sales_count': unpaid_sales_count,
        'returned_sales_count': returned_sales_count,
        'total_amount': total_amount,
        'customers': customers,
        'sale_headers': sale_headers,
        'sale_actions': sale_actions,
        'page_title': 'فواتير المبيعات',
        'page_icon': 'fas fa-shopping-cart',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المبيعات', 'url': '#', 'icon': 'fas fa-truck'},
            {'title': 'فواتير المبيعات', 'active': True}
        ],
    }
    
    return render(request, 'sale/sale_list.html', context)


@login_required
def sale_create(request):
    """
    إنشاء فاتورة مبيعات جديدة
    """
    products = Product.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        form = SaleForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # إنشاء فاتورة المبيعات
                    sale = form.save(commit=False)
                    sale.subtotal = Decimal(request.POST.get('subtotal', '0'))
                    sale.total = Decimal(request.POST.get('total', '0'))
                    sale.created_by = request.user
                    
                    # التأكد من وجود رقم للفاتورة
                    if not sale.number:
                        # الحصول على الرقم التسلسلي
                        try:
                            logger.info("جاري محاولة إنشاء رقم تسلسلي جديد للفاتورة")
                            serial, created = SerialNumber.objects.get_or_create(
                                document_type='sale',
                                year=timezone.now().year,
                                defaults={
                                    'prefix': 'SALE',
                                    'last_number': 0
                                }
                            )
                            next_number = serial.get_next_number()
                            sale.number = f"{serial.prefix}{next_number:04d}"
                            logger.info(f"تم إنشاء رقم فاتورة جديد: {sale.number}")
                        except Exception as e:
                            logger.error(f"خطأ في إنشاء رقم الفاتورة: {str(e)}")
                            # في حالة فشل إنشاء الرقم التسلسلي، قم بإنشاء رقم عشوائي
                            import random
                            random_num = random.randint(10000, 99999)
                            sale.number = f"SALE{random_num}"
                            logger.info(f"تم إنشاء رقم فاتورة عشوائي: {sale.number}")
                    
                    sale.save()
                    
                    # إضافة بنود الفاتورة
                    product_ids = request.POST.getlist('product[]')
                    quantities = request.POST.getlist('quantity[]')
                    unit_prices = request.POST.getlist('unit_price[]')
                    discounts = request.POST.getlist('discount[]')
                    
                    # حذف جميع حركات المخزون المرتبطة بهذه الفاتورة أولاً للتأكد من عدم التكرار
                    StockMovement.objects.filter(
                        reference_number__startswith=f"SALE-{sale.number}"
                    ).delete()
                    
                    # تعريف رقم المرجع الرئيسي
                    main_reference = f"SALE-{sale.number}"
                    
                    for i in range(len(product_ids)):
                        if product_ids[i]:  # تخطي الصفوف الفارغة
                            product = get_object_or_404(Product, id=product_ids[i])
                            try:
                                # التأكد من تحويل كل القيم إلى الأنواع المناسبة
                                quantity_val = float(quantities[i])
                                # التأكد من أن الكمية موجبة وأكبر من الصفر
                                if quantity_val <= 0:
                                    raise ValueError("يجب أن تكون الكمية أكبر من صفر")
                                
                                quantity = max(1, int(quantity_val))  # التأكد من أن الكمية على الأقل 1
                                
                                # التأكد من صحة سعر الوحدة
                                unit_price_val = unit_prices[i].strip() if isinstance(unit_prices[i], str) else unit_prices[i]
                                if not unit_price_val or float(unit_price_val) <= 0:
                                    raise ValueError("يجب أن يكون سعر الوحدة أكبر من صفر")
                                unit_price = Decimal(unit_price_val)
                                
                                # التأكد من صحة قيمة الخصم
                                discount_value = discounts[i].strip() if isinstance(discounts[i], str) else discounts[i]
                                discount_value = discount_value if discount_value else '0'
                                if float(discount_value) < 0:
                                    discount_value = '0'  # تجنب القيم السالبة في الخصم
                                discount = Decimal(discount_value)
                                
                                # إنشاء بند فاتورة
                                item = SaleItem(
                                    sale=sale,
                                    product=product,
                                    quantity=quantity,
                                    unit_price=unit_price,
                                    discount=discount,
                                    total=(Decimal(str(quantity)) * unit_price) - discount
                                )
                                item.save()
                            except (ValueError, TypeError) as e:
                                raise ValueError(f"خطأ في تحويل قيم البند {i+1}: {str(e)}")
                    
                    # بعد إنشاء جميع البنود، قم بإنشاء حركات المخزون
                    for item in sale.items.all():
                        # استخدام معرف البند في الرقم المرجعي بدلاً من معرف المنتج لضمان عدم التكرار
                        reference_id = f"{main_reference}-ITEM{item.id}" 
                        
                        # تحقق من وجود حركة مخزون مسبقة بنفس الرقم المرجعي
                        if not StockMovement.objects.filter(
                            reference_number=reference_id
                        ).exists():
                            # الحصول على المخزون الحالي
                            stock, created = Stock.objects.get_or_create(
                                product=item.product,
                                warehouse=sale.warehouse,
                                defaults={'quantity': 0}
                            )
                            
                            # تخزين قيمة المخزون قبل التحديث
                            quantity_before = stock.quantity
                            
                            # تحديث المخزون يدوياً
                            stock.quantity -= item.quantity
                            stock.save()
                            
                            # إنشاء حركة مخزون
                            StockMovement.objects.create(
                                product=item.product,
                                warehouse=sale.warehouse,
                                movement_type='out',
                                quantity=item.quantity,
                                reference_number=reference_id,
                                document_type='sale',
                                document_number=sale.number,
                                notes=f'فاتورة مبيعات رقم {sale.number}',
                                created_by=request.user
                            )
                    
                    messages.success(request, 'تم إنشاء فاتورة المبيعات بنجاح')
                    return redirect('sale:sale_detail', pk=sale.pk)
            
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء إنشاء الفاتورة: {str(e)}')
    else:
        # تهيئة بيانات افتراضية
        initial_data = {
            'date': timezone.now().date(),  # تعيين تاريخ اليوم كتاريخ افتراضي للفاتورة
        }
        form = SaleForm(initial=initial_data)
    
    # محاولة الحصول على الرقم التسلسلي التالي للفاتورة
    next_sale_number = None
    try:
        # إنشاء مستند SerialNumber ليتم الحصول على رقم جديد منه
        serial, created = SerialNumber.objects.get_or_create(
            document_type='sale',
            year=timezone.now().year,
            defaults={
                'prefix': 'SALE',
                'last_number': 0
            }
        )
        
        # الحصول على الرقم التالي للفاتورة بدون حفظ (لعرض فقط)
        last_sale = Sale.objects.order_by('-id').first()
        last_number = 0
        
        if last_sale and last_sale.number:
            try:
                last_number = int(last_sale.number.replace('SALE', ''))
            except (ValueError, AttributeError):
                pass
                
        next_number = max(serial.last_number, last_number) + 1
        next_sale_number = f"{serial.prefix}{next_number:04d}"
        logger.info(f"الرقم التالي للفاتورة الجديدة: {next_sale_number}")
    except Exception as e:
        logger.error(f"خطأ في الحصول على الرقم التالي للفاتورة: {str(e)}")
    
    # إضافة متغيرات عنوان الصفحة
    context = {
        'products': products,
        'form': form,
        'next_sale_number': next_sale_number,  # إضافة رقم الفاتورة التالي للسياق
        'page_title': 'إضافة فاتورة مبيعات',
        'page_icon': 'fas fa-plus-circle',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المبيعات', 'url': reverse('sale:sale_list'), 'icon': 'fas fa-shopping-cart'},
            {'title': 'إضافة فاتورة', 'active': True}
        ]
    }
    
    return render(request, 'sale/sale_form.html', context)


@login_required
def sale_payment_list(request):
    """
    عرض قائمة مدفوعات فواتير المبيعات
    """
    payments = SalePayment.objects.all()
    
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
        'title': 'مدفوعات المبيعات',
    }
    
    return render(request, 'sale/payment_list.html', context)


@login_required
def sale_detail(request, pk):
    """
    عرض تفاصيل فاتورة المبيعات
    """
    sale = get_object_or_404(Sale, pk=pk)
    
    context = {
        'sale': sale,
        'title': 'تفاصيل فاتورة المبيعات',
        'page_title': f'فاتورة مبيعات - {sale.number}',
        'page_icon': 'fas fa-file-invoice-dollar',
        'breadcrumb_items': [
            {'title': 'لوحة التحكم', 'url': reverse('core:dashboard'), 'icon': 'fas fa-tachometer-alt'},
            {'title': 'المبيعات', 'url': reverse('sale:sale_list'), 'icon': 'fas fa-shopping-cart'},
            {'title': f'فاتورة {sale.number}', 'active': True},
        ],
    }
    
    return render(request, 'sale/sale_detail.html', context)


@login_required
def sale_edit(request, pk):
    """
    تعديل فاتورة المبيعات
    """
    sale = get_object_or_404(Sale, pk=pk)
    products = Product.objects.filter(is_active=True)
    
    # التحقق مما إذا كانت الفاتورة لها مرتجعات مؤكدة
    has_confirmed_returns = sale.returns.filter(status='confirmed').exists()
    
    if has_confirmed_returns:
        messages.error(request, 'لا يمكن تعديل الفاتورة لأنها تحتوي على مرتجعات مؤكدة')
        return redirect('sale:sale_detail', pk=sale.pk)
    
    # حفظ البنود الحالية للفاتورة قبل التعديل للاستفادة منها لاحقاً
    original_items = {}
    for item in sale.items.all():
        original_items[item.product_id] = item.quantity
    
    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # تحديث بيانات الفاتورة (باستثناء البنود)
                    updated_sale = form.save(commit=False)
                    updated_sale.subtotal = Decimal(request.POST.get('subtotal', '0'))
                    updated_sale.total = Decimal(request.POST.get('total', '0'))
                    updated_sale.save()
                    
                    # حذف عناصر الفاتورة (سيتم إعادة إنشائها)
                    sale.items.all().delete()
                    
                    # إضافة بنود الفاتورة الجديدة
                    product_ids = request.POST.getlist('product[]')
                    quantities = request.POST.getlist('quantity[]')
                    unit_prices = request.POST.getlist('unit_price[]')
                    discounts = request.POST.getlist('discount[]')
                    
                    # تعريف رقم المرجع الرئيسي
                    main_reference = f"SALE-{updated_sale.number}"
                    
                    for i in range(len(product_ids)):
                        if product_ids[i]:  # تخطي الصفوف الفارغة
                            product = get_object_or_404(Product, id=product_ids[i])
                            try:
                                # التأكد من تحويل كل القيم إلى الأنواع المناسبة
                                quantity_val = float(quantities[i])
                                # التأكد من أن الكمية موجبة وأكبر من الصفر
                                if quantity_val <= 0:
                                    raise ValueError("يجب أن تكون الكمية أكبر من صفر")
                                
                                quantity = max(1, int(quantity_val))  # التأكد من أن الكمية على الأقل 1
                                
                                # التأكد من صحة سعر الوحدة
                                unit_price_val = unit_prices[i].strip() if isinstance(unit_prices[i], str) else unit_prices[i]
                                if not unit_price_val or float(unit_price_val) <= 0:
                                    raise ValueError("يجب أن يكون سعر الوحدة أكبر من صفر")
                                unit_price = Decimal(unit_price_val)
                                
                                # التأكد من صحة قيمة الخصم
                                discount_value = discounts[i].strip() if isinstance(discounts[i], str) else discounts[i]
                                discount_value = discount_value if discount_value else '0'
                                if float(discount_value) < 0:
                                    discount_value = '0'  # تجنب القيم السالبة في الخصم
                                discount = Decimal(discount_value)
                                
                                # إنشاء بند فاتورة
                                item = SaleItem(
                                    sale=updated_sale,
                                    product=product,
                                    quantity=quantity,
                                    unit_price=unit_price,
                                    discount=discount,
                                    total=(Decimal(str(quantity)) * unit_price) - discount
                                )
                                item.save()
                            except (ValueError, TypeError) as e:
                                raise ValueError(f"خطأ في تحويل قيم البند {i+1}: {str(e)}")
                    
                    # بعد إنشاء جميع البنود، قم بإنشاء حركات المخزون للاختلافات فقط
                    # إنشاء قاموس للكميات الجديدة
                    new_items = {}
                    for item in updated_sale.items.all():
                        new_items[item.product_id] = item.quantity
                    
                    # معالجة المنتجات المضافة أو التي تغيرت كميتها
                    for product_id, new_quantity in new_items.items():
                        original_quantity = original_items.get(product_id, 0)
                        quantity_diff = new_quantity - original_quantity
                        
                        if quantity_diff != 0:  # فقط إذا كان هناك تغيير في الكمية
                            product = Product.objects.get(id=product_id)
                            
                            # الحصول على المخزون الحالي
                            stock, created = Stock.objects.get_or_create(
                                product=product,
                                warehouse=updated_sale.warehouse,
                                defaults={'quantity': 0}
                            )
                            
                            # تحديث المخزون يدوياً حسب اتجاه التغيير
                            if quantity_diff > 0:  # إذا زادت الكمية، نخصم الزيادة
                                stock.quantity -= quantity_diff
                                if stock.quantity < 0:
                                    stock.quantity = 0
                                
                                # إنشاء حركة مخزون للخصم
                                StockMovement.objects.create(
                                    product=product,
                                    warehouse=updated_sale.warehouse,
                                    movement_type='out',
                                    quantity=quantity_diff,
                                    reference_number=f"{main_reference}-EDIT-OUT-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                                    document_type='sale',
                                    document_number=updated_sale.number,
                                    notes=f'زيادة كمية منتج في تعديل فاتورة مبيعات رقم {updated_sale.number}',
                                    created_by=request.user
                                )
                            else:  # إذا قلت الكمية، نعيد الفرق للمخزون
                                stock.quantity += abs(quantity_diff)
                                
                                # إنشاء حركة مخزون للإضافة
                                StockMovement.objects.create(
                                    product=product,
                                    warehouse=updated_sale.warehouse,
                                    movement_type='in',
                                    quantity=abs(quantity_diff),
                                    reference_number=f"{main_reference}-EDIT-IN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                                    document_type='sale',
                                    document_number=updated_sale.number,
                                    notes=f'نقص كمية منتج في تعديل فاتورة مبيعات رقم {updated_sale.number}',
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
                                warehouse=updated_sale.warehouse,
                                defaults={'quantity': 0}
                            )
                            
                            # إعادة الكمية المحذوفة للمخزون
                            stock.quantity += original_quantity
                            stock.save()
                            
                            # إنشاء حركة مخزون للإضافة
                            StockMovement.objects.create(
                                product=product,
                                warehouse=updated_sale.warehouse,
                                movement_type='in',
                                quantity=original_quantity,
                                reference_number=f"{main_reference}-EDIT-DELETE-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                                document_type='sale',
                                document_number=updated_sale.number,
                                notes=f'حذف منتج من فاتورة مبيعات رقم {updated_sale.number}',
                                created_by=request.user
                            )
                    
                    messages.success(request, 'تم تعديل فاتورة المبيعات بنجاح')
                    return redirect('sale:sale_detail', pk=updated_sale.pk)
            
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء تعديل الفاتورة: {str(e)}')
    else:
        # تهيئة الفورم مع بيانات البيع الحالية
        form = SaleForm(instance=sale)
    
    sale_number = sale.number
    
    # إضافة متغيرات عنوان الصفحة
    context = {
        'sale': sale,
        'form': form,  # إضافة النموذج للسياق
        'products': products,
        'page_title': f'تعديل فاتورة مبيعات',
        'page_icon': 'fas fa-edit',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المبيعات', 'url': reverse('sale:sale_list'), 'icon': 'fas fa-shopping-cart'},
            {'title': f'تعديل الفاتورة {sale_number}', 'active': True}
        ],
        'sale_items': sale.items.all(),
        'has_confirmed_returns': has_confirmed_returns,
    }
    
    return render(request, 'sale/sale_form.html', context)


@login_required
def sale_delete(request, pk):
    """
    حذف فاتورة المبيعات
    """
    sale = get_object_or_404(Sale, pk=pk)
    
    # التحقق مما إذا كانت الفاتورة لها مرتجعات مؤكدة
    has_confirmed_returns = sale.returns.filter(status='confirmed').exists()
    
    if has_confirmed_returns:
        messages.error(request, 'لا يمكن حذف الفاتورة لأنها تحتوي على مرتجعات مؤكدة')
        return redirect('sale:sale_detail', pk=sale.pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # حذف جميع حركات المخزون المرتبطة بهذه الفاتورة
                StockMovement.objects.filter(
                    reference_number__startswith=f"SALE-{sale.number}"
                ).delete()
                
                # حذف الفاتورة
                sale.delete()
                
                messages.success(request, 'تم حذف فاتورة المبيعات بنجاح')
                return redirect('sale:sale_list')
        
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف الفاتورة: {str(e)}')
    
    context = {
        'sale': sale,
        'title': f'حذف فاتورة مبيعات - {sale.number}',
    }
    
    return render(request, 'sale/sale_confirm_delete.html', context)


@login_required
def sale_print(request, pk):
    """
    طباعة فاتورة المبيعات
    """
    sale = get_object_or_404(Sale, pk=pk)
    
    context = {
        'sale': sale,
        'title': f'طباعة فاتورة مبيعات - {sale.number}',
        'year': datetime.datetime.now().year,
    }
    
    return render(request, 'sale/sale_print.html', context)


@login_required
def add_payment(request, pk):
    """
    إضافة دفعة لفاتورة المبيعات
    """
    sale = get_object_or_404(Sale, pk=pk)
    
    if request.method == 'POST':
        form = SalePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.sale = sale
            payment.created_by = request.user
            
            # تأكد من أن المبلغ لا يتجاوز المبلغ المستحق
            if payment.amount > sale.amount_due:
                messages.warning(request, _('تم تقليل المبلغ إلى القيمة المستحقة المتبقية'))
                payment.amount = sale.amount_due
            
            with transaction.atomic():
                # حفظ الدفعة
                payment.save()
                
                # تحديث حالة فاتورة المبيعات
                sale.refresh_from_db()
                if sale.amount_due <= 0:
                    sale.payment_status = 'paid'
                elif sale.amount_paid > 0:
                    sale.payment_status = 'partially_paid'
                sale.save()
                
                # تحديث رصيد العميل
                sale.customer.balance -= payment.amount
                sale.customer.save()
            
            messages.success(request, _('تم تسجيل الدفعة بنجاح'))
            return redirect('sale:sale_detail', pk=sale.pk)
    else:
        # تعبئة قيمة افتراضية للمبلغ (المبلغ المستحق)
        initial_data = {
            'amount': sale.amount_due,
            'payment_date': datetime.datetime.now().date()
        }
        form = SalePaymentForm(initial=initial_data)
    
    context = {
        'invoice': sale,  # استخدام invoice بدلاً من sale للنموذج المشترك
        'form': form,
        'is_purchase': False,  # تحديد أن هذا نموذج دفع للمبيعات
        'page_title': f'إضافة دفعة لفاتورة المبيعات {sale.number}',
        'title': f'إضافة دفعة لفاتورة المبيعات {sale.number}',
        'page_icon': 'fas fa-money-bill-wave',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'فواتير المبيعات', 'url': reverse('sale:sale_list'), 'icon': 'fas fa-file-invoice-dollar'},
            {'title': sale.number, 'url': reverse('sale:sale_detail', kwargs={'pk': sale.pk})},
            {'title': 'إضافة دفعة', 'active': True}
        ],
    }
    
    return render(request, 'sale/sale_payment_form.html', context)


@login_required
def sale_return(request, pk):
    """
    إرجاع فاتورة المبيعات
    """
    sale = get_object_or_404(Sale, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # إنشاء مرتجع المبيعات
                return_form = SaleReturnForm(request.POST)
                if return_form.is_valid():
                    sale_return = return_form.save(commit=False)
                    sale_return.sale = sale
                    sale_return.created_by = request.user
                    sale_return.save()
                    
                    # إضافة بنود المرتجع
                    item_ids = request.POST.getlist('item_id')
                    return_quantities = request.POST.getlist('return_quantity')
                    return_reasons = request.POST.getlist('return_reason')
                    
                    subtotal = 0
                    for i in range(len(item_ids)):
                        if item_ids[i] and int(return_quantities[i]) > 0:
                            sale_item = get_object_or_404(SaleItem, id=item_ids[i])
                            return_quantity = int(return_quantities[i])
                            return_reason = return_reasons[i] if i < len(return_reasons) else "إرجاع بضاعة"
                            
                            # التأكد من أن الكمية المرتجعة لا تتجاوز الكمية المباعة
                            if return_quantity > sale_item.quantity:
                                return_quantity = sale_item.quantity
                            
                            # إنشاء بند المرتجع
                            return_item = SaleReturnItem(
                                sale_return=sale_return,
                                sale_item=sale_item,
                                product=sale_item.product,
                                quantity=return_quantity,
                                unit_price=sale_item.unit_price,
                                reason=return_reason
                            )
                            return_item.save()
                            
                            # تحديث المجموع
                            subtotal += return_item.total
                            
                            # إنشاء حركة مخزون وارد (مرتجع مبيعات)
                            StockMovement.objects.create(
                                product=sale_item.product,
                                warehouse=sale_return.warehouse,
                                movement_type='return_in',
                                quantity=return_quantity,
                                reference_number=f"RETURN-SALE-{sale_return.number}-ITEM{return_item.id}",
                                document_type='sale_return',
                                document_number=sale_return.number,
                                notes=f'مرتجع مبيعات فاتورة رقم {sale.number}: {return_reason}',
                                created_by=request.user
                            )
                    
                    # تحديث إجماليات المرتجع
                    sale_return.subtotal = subtotal
                    sale_return.tax = subtotal * 0.14  # 14% ضريبة
                    sale_return.total = subtotal + sale_return.tax
                    sale_return.save()
                    
                    messages.success(request, 'تم تسجيل مرتجع المبيعات بنجاح')
                    return redirect('sale:sale_detail', pk=sale.pk)
        
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء معالجة المرتجع: {str(e)}')
            return_form = SaleReturnForm()  # إعادة تهيئة النموذج في حالة وجود خطأ
    else:
        # إنشاء نموذج فارغ عند طلب GET
        return_form = SaleReturnForm(initial={
            'date': timezone.now().date(),  # تاريخ اليوم كقيمة افتراضية
            'warehouse': sale.warehouse  # استخدام نفس مستودع الفاتورة
        })
    
    context = {
        'sale': sale,
        'items': sale.items.all(),
        'title': f'مرتجع مبيعات - {sale.number}',
        'form': return_form  # إضافة النموذج للسياق
    }
    
    return render(request, 'sale/sale_return.html', context)


@login_required
def sale_return_list(request):
    """
    عرض قائمة مرتجعات المبيعات
    """
    returns = SaleReturn.objects.all().order_by('-date', '-id')
    
    context = {
        'returns': returns,
        'page_title': 'مرتجعات المبيعات',
        'page_icon': 'fas fa-undo-alt',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المبيعات', 'url': reverse('sale:sale_list'), 'icon': 'fas fa-shopping-cart'},
            {'title': 'مرتجعات المبيعات', 'active': True}
        ],
    }
    
    return render(request, 'sale/sale_return_list.html', context)


@login_required
def sale_return_detail(request, pk):
    """
    عرض تفاصيل مرتجع المبيعات
    """
    sale_return = get_object_or_404(SaleReturn, pk=pk)
    
    context = {
        'sale_return': sale_return,
        'title': f'تفاصيل مرتجع المبيعات - {sale_return.number}',
    }
    
    return render(request, 'sale/sale_return_detail.html', context)


@login_required
def sale_return_confirm(request, pk):
    """
    تأكيد مرتجع المبيعات وتغيير حالته من مسودة إلى مؤكد
    """
    sale_return = get_object_or_404(SaleReturn, pk=pk)
    
    # التأكد من أن المرتجع في حالة مسودة
    if sale_return.status != 'draft':
        messages.error(request, 'لا يمكن تأكيد مرتجع تم تأكيده أو إلغاؤه من قبل')
        return redirect('sale:sale_return_detail', pk=sale_return.pk)
    
    try:
        with transaction.atomic():
            # تحديث حالة المرتجع إلى مؤكد
            sale_return.status = 'confirmed'
            sale_return.save()
            
            # يمكن هنا إضافة أي إجراءات إضافية مثل تحديث حسابات العميل
            # أو إنشاء قيود محاسبية أو إرسال إشعارات للعملاء المعنيين
            
            messages.success(request, 'تم تأكيد مرتجع المبيعات بنجاح')
    except Exception as e:
        logger.error(f"Error confirming sale return: {str(e)}")
        messages.error(request, f'حدث خطأ أثناء تأكيد المرتجع: {str(e)}')
    
    return redirect('sale:sale_return_detail', pk=sale_return.pk)


@login_required
def sale_return_cancel(request, pk):
    """
    إلغاء مرتجع المبيعات وتغيير حالته إلى ملغي
    """
    sale_return = get_object_or_404(SaleReturn, pk=pk)
    
    # التأكد من أن المرتجع في حالة مسودة
    if sale_return.status != 'draft':
        messages.error(request, 'لا يمكن إلغاء مرتجع تم تأكيده أو إلغاؤه من قبل')
        return redirect('sale:sale_return_detail', pk=sale_return.pk)
    
    try:
        with transaction.atomic():
            # تحديث حالة المرتجع إلى ملغي
            sale_return.status = 'cancelled'
            sale_return.save()
            
            # عكس حركات المخزون المرتبطة بالمرتجع
            # (إذا كانت قد تمت بالفعل عند إنشاء المرتجع)
            
            messages.success(request, 'تم إلغاء مرتجع المبيعات بنجاح')
    except Exception as e:
        logger.error(f"Error cancelling sale return: {str(e)}")
        messages.error(request, f'حدث خطأ أثناء إلغاء المرتجع: {str(e)}')
    
    return redirect('sale:sale_return_detail', pk=sale_return.pk)
