from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum, Q, F
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from .models import (
    Product, Category, Warehouse, Stock, StockMovement,
    Brand, Unit, ProductImage, ProductVariant
)
from .forms import (
    ProductForm, CategoryForm, WarehouseForm, StockMovementForm,
    BrandForm, UnitForm, ProductImageForm, ProductVariantForm,
    ProductSearchForm
)
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
import csv
from io import BytesIO
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
import logging
from decimal import Decimal

# استيراد نماذج المبيعات والمشتريات للتحقق من الارتباطات
try:
    from sale.models import SaleItem
    from purchase.models import PurchaseItem
except ImportError:
    # تعامل مع حالة عدم وجود التطبيقات
    SaleItem = None
    PurchaseItem = None

logger = logging.getLogger(__name__)


@login_required
def product_list(request):
    """
    عرض قائمة المنتجات
    """
    # استرجاع كل المنتجات بطريقة بسيطة
    try:
        products = Product.objects.select_related('category', 'brand', 'unit').prefetch_related('stocks').all()
        
        # البحث البسيط
        search_query = request.GET.get('search', '')
        if search_query:
            products = products.filter(name__icontains=search_query)
        
        # تطبيق التصفية
        filter_form = ProductSearchForm(request.GET)
        
        context = {
            'products': products,
            'filter_form': filter_form,
            'page_title': 'قائمة المنتجات',
            'page_icon': 'fas fa-boxes',
            'breadcrumb_items': [
                {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
                {'title': 'المنتجات', 'active': True}
            ],
        }
        
        return render(request, 'product/product_list.html', context)
    except Exception as e:
        # في حالة حدوث أي خطأ، نعرض صفحة بسيطة مع رسالة الخطأ
        messages.error(request, f"حدث خطأ أثناء تحميل المنتجات: {str(e)}")
        return render(request, 'product/product_list.html', {
            'products': Product.objects.none(),
            'filter_form': ProductSearchForm(),
            'page_title': 'قائمة المنتجات - خطأ',
            'page_icon': 'fas fa-exclamation-triangle',
            'breadcrumb_items': [
                {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
                {'title': 'المنتجات', 'active': True}
            ],
            'error_message': str(e)
        })


@login_required
def product_create(request):
    """
    إضافة منتج جديد
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            
            # معالجة الصور
            images = request.FILES.getlist('images')
            for image in images:
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=not ProductImage.objects.filter(product=product).exists()
                )
            
            messages.success(request, f'تم إضافة المنتج "{product.name}" بنجاح')
            
            if 'save_and_continue' in request.POST:
                return redirect('product:product_create')
            else:
                return redirect('product:product_list')
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة منتج جديد',
        'page_icon': 'fas fa-plus-circle',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': 'إضافة منتج', 'active': True}
        ],
    }
    
    return render(request, 'product/product_form.html', context)


@login_required
def product_edit(request, pk):
    """
    تعديل منتج
    """
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.updated_by = request.user
            product.save()
            
            # معالجة الصور
            images = request.FILES.getlist('images')
            for image in images:
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=not ProductImage.objects.filter(product=product).exists()
                )
            
            messages.success(request, f'تم تحديث المنتج "{product.name}" بنجاح')
            return redirect('product:product_list')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'title': f'تعديل المنتج: {product.name}',
        'page_title': f'تعديل المنتج: {product.name}',
        'page_icon': 'fas fa-edit',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': f'تعديل: {product.name}', 'active': True}
        ],
    }
    
    return render(request, 'product/product_form.html', context)


@login_required
def product_detail(request, pk):
    """
    عرض تفاصيل المنتج
    """
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand', 'unit'), 
        pk=pk
    )
    
    # الحصول على المخزون الحالي للمنتج في كل مستودع
    stock_items = Stock.objects.filter(product=product).select_related('warehouse')
    
    # آخر حركات المخزون
    stock_movements = StockMovement.objects.filter(product=product).select_related(
        'warehouse', 'destination_warehouse', 'created_by'
    ).order_by('-timestamp')[:10]
    
    # إجمالي المخزون
    total_stock = stock_items.aggregate(total=Sum('quantity'))['total'] or 0
    
    context = {
        'product': product,
        'stock_items': stock_items,
        'stock_movements': stock_movements,
        'total_stock': total_stock,
        'title': product.name,
    }
    
    return render(request, 'product/product_detail.html', context)


@login_required
def product_delete(request, pk):
    """
    حذف منتج
    """
    product = get_object_or_404(Product, pk=pk)
    
    # التحقق من وجود ارتباطات للمنتج
    has_movements = StockMovement.objects.filter(product=product).exists()
    has_sale_items = SaleItem is not None and SaleItem.objects.filter(product=product).exists()
    has_purchase_items = PurchaseItem is not None and PurchaseItem.objects.filter(product=product).exists()
    
    has_dependencies = has_movements or has_sale_items or has_purchase_items
    
    if request.method == 'POST':
        try:
            name = product.name
            
            if has_dependencies:
                # إذا كان المنتج مرتبطًا بسجلات أخرى، قم بإلغاء تنشيطه فقط
                product.is_active = False
                product.save()
                messages.success(request, f'تم إلغاء تنشيط المنتج "{name}" بنجاح. لم يتم حذفه لارتباطه بعمليات سابقة')
            else:
                # إذا لم يكن مرتبطًا بأي سجلات، يمكن حذفه
                product.delete()
                messages.success(request, f'تم حذف المنتج "{name}" بنجاح')
                
            return redirect('product:product_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء معالجة طلب الحذف: {str(e)}')
    
    context = {
        'product': product,
        'title': f'حذف المنتج: {product.name}',
        'has_dependencies': has_dependencies,
        'object': product,  # لاستخدامه في القالب
        'object_name': 'المنتج',  # لاستخدامه في القالب
    }
    
    return render(request, 'product/product_confirm_delete.html', context)


@login_required
def category_list(request):
    """
    عرض قائمة فئات المنتجات
    """
    categories = Category.objects.all()
    
    # بحث
    search_query = request.GET.get('search', '')
    if search_query:
        categories = categories.filter(name__icontains=search_query)
    
    # الفئات حسب الحالة
    status = request.GET.get('status', '')
    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'inactive':
        categories = categories.filter(is_active=False)
    
    # إجمالي الفئات والفئات النشطة
    total_categories = Category.objects.count()
    active_categories = Category.objects.filter(is_active=True).count()
    
    # الفئات الرئيسية (التي ليس لها أب)
    root_categories = categories.filter(parent__isnull=True)
    
    # ترقيم الصفحات
    paginator = Paginator(categories, 30)
    page = request.GET.get('page')
    
    try:
        categories = paginator.page(page)
    except PageNotAnInteger:
        categories = paginator.page(1)
    except EmptyPage:
        categories = paginator.page(paginator.num_pages)
    
    context = {
        'categories': categories,
        'root_categories': root_categories,
        'total_categories': total_categories,
        'active_categories': active_categories,
        'search_query': search_query,
        'status': status,
        'page_title': 'فئات المنتجات',
        'page_icon': 'fas fa-tags',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': 'الفئات', 'active': True}
        ],
    }
    
    return render(request, 'product/category_list.html', context)


@login_required
def category_create(request):
    """
    إضافة فئة منتجات جديدة
    """
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'تم إضافة الفئة "{category.name}" بنجاح')
            return redirect('product:category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة فئة جديدة',
        'page_icon': 'fas fa-folder-plus',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': 'الفئات', 'url': reverse('product:category_list'), 'icon': 'fas fa-tags'},
            {'title': 'إضافة فئة', 'active': True}
        ],
    }
    
    return render(request, 'product/category_form.html', context)


@login_required
def category_edit(request, pk):
    """
    تعديل فئة منتجات
    """
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'تم تحديث الفئة "{category.name}" بنجاح')
            return redirect('product:category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'تعديل الفئة: {category.name}',
        'object_type': 'فئة',
        'object_list_name': 'الفئات',
        'list_url': reverse('product:category_list'),
        'page_icon': 'fas fa-tags',
    }
    
    return render(request, 'product/category_form.html', context)


@login_required
def category_delete(request, pk):
    """
    حذف فئة منتجات
    """
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'تم حذف الفئة "{name}" بنجاح')
        return redirect('product:category_list')
    
    context = {
        'category': category,
        'title': f'حذف الفئة: {category.name}',
    }
    
    return render(request, 'product/category_confirm_delete.html', context)


@login_required
def category_detail(request, pk):
    """
    عرض تفاصيل فئة منتجات
    """
    category = get_object_or_404(Category, pk=pk)
    
    # الحصول على المنتجات في هذه الفئة
    products = Product.objects.filter(category=category).select_related('brand', 'unit')
    
    # الفئات الفرعية
    subcategories = Category.objects.filter(parent=category)
    
    context = {
        'category': category,
        'products': products,
        'subcategories': subcategories,
        'title': category.name,
    }
    
    return render(request, 'product/category_detail.html', context)


@login_required
def brand_list(request):
    """
    عرض قائمة العلامات التجارية
    """
    brands = Brand.objects.all()
    
    context = {
        'brands': brands,
        'page_title': 'العلامات التجارية',
        'page_icon': 'fas fa-copyright',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': 'العلامات التجارية', 'active': True}
        ],
    }
    
    return render(request, 'product/brand_list.html', context)


@login_required
def brand_create(request):
    """
    إضافة علامة تجارية جديدة
    """
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            brand = form.save()
            messages.success(request, f'تم إضافة العلامة التجارية "{brand.name}" بنجاح')
            return redirect('product:brand_list')
    else:
        form = BrandForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة علامة تجارية جديدة',
        'page_icon': 'fas fa-copyright',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': 'العلامات التجارية', 'url': reverse('product:brand_list'), 'icon': 'fas fa-copyright'},
            {'title': 'إضافة علامة تجارية', 'active': True}
        ],
    }
    
    return render(request, 'product/brand_form.html', context)


@login_required
def brand_edit(request, pk):
    """
    تعديل علامة تجارية
    """
    brand = get_object_or_404(Brand, pk=pk)
    
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES, instance=brand)
        if form.is_valid():
            brand = form.save()
            messages.success(request, f'تم تحديث العلامة التجارية "{brand.name}" بنجاح')
            return redirect('product:brand_list')
    else:
        form = BrandForm(instance=brand)
    
    context = {
        'form': form,
        'brand': brand,
        'title': f'تعديل العلامة التجارية: {brand.name}',
    }
    
    return render(request, 'product/brand_form.html', context)


@login_required
def brand_delete(request, pk):
    """
    حذف علامة تجارية
    """
    brand = get_object_or_404(Brand, pk=pk)
    
    if request.method == 'POST':
        name = brand.name
        brand.delete()
        messages.success(request, f'تم حذف العلامة التجارية "{name}" بنجاح')
        return redirect('product:brand_list')
    
    context = {
        'brand': brand,
        'title': f'حذف العلامة التجارية: {brand.name}',
    }
    
    return render(request, 'product/brand_confirm_delete.html', context)


@login_required
def brand_detail(request, pk):
    """
    عرض تفاصيل علامة تجارية
    """
    brand = get_object_or_404(Brand, pk=pk)
    
    # الحصول على المنتجات لهذه العلامة التجارية
    products = Product.objects.filter(brand=brand).select_related('category', 'unit')
    
    context = {
        'brand': brand,
        'products': products,
        'title': brand.name,
        'page_title': f'العلامة التجارية: {brand.name}',
        'page_icon': 'fas fa-copyright',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': 'العلامات التجارية', 'url': reverse('product:brand_list'), 'icon': 'fas fa-copyright'},
            {'title': brand.name, 'active': True}
        ],
    }
    
    return render(request, 'product/brand_detail.html', context)


@login_required
def unit_list(request):
    """
    عرض قائمة وحدات القياس
    """
    units = Unit.objects.all()
    
    context = {
        'units': units,
        'title': 'وحدات القياس',
    }
    
    return render(request, 'product/unit_list.html', context)


@login_required
def unit_create(request):
    """
    إضافة وحدة قياس جديدة
    """
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save()
            messages.success(request, f'تم إضافة وحدة القياس "{unit.name}" بنجاح')
            return redirect('product:unit_list')
    else:
        form = UnitForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة وحدة قياس جديدة',
        'page_icon': 'fas fa-ruler',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-boxes'},
            {'title': 'وحدات القياس', 'url': reverse('product:unit_list'), 'icon': 'fas fa-ruler'},
            {'title': 'إضافة وحدة', 'active': True}
        ],
    }
    
    return render(request, 'product/unit_form.html', context)


@login_required
def unit_edit(request, pk):
    """
    تعديل وحدة قياس
    """
    unit = get_object_or_404(Unit, pk=pk)
    
    if request.method == 'POST':
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            unit = form.save()
            messages.success(request, f'تم تحديث وحدة القياس "{unit.name}" بنجاح')
            return redirect('product:unit_list')
    else:
        form = UnitForm(instance=unit)
    
    context = {
        'form': form,
        'unit': unit,
        'title': f'تعديل وحدة القياس: {unit.name}',
    }
    
    return render(request, 'product/unit_form.html', context)


@login_required
def unit_delete(request, pk):
    """
    حذف وحدة قياس
    """
    unit = get_object_or_404(Unit, pk=pk)
    
    if request.method == 'POST':
        name = unit.name
        unit.delete()
        messages.success(request, f'تم حذف وحدة القياس "{name}" بنجاح')
        return redirect('product:unit_list')
    
    context = {
        'unit': unit,
        'title': f'حذف وحدة القياس: {unit.name}',
    }
    
    return render(request, 'product/unit_confirm_delete.html', context)


@login_required
def unit_detail(request, pk):
    """
    عرض تفاصيل وحدة قياس
    """
    unit = get_object_or_404(Unit, pk=pk)
    
    # الحصول على المنتجات التي تستخدم هذه الوحدة
    products = Product.objects.filter(unit=unit).select_related('category', 'brand')
    
    context = {
        'unit': unit,
        'products': products,
        'title': unit.name,
    }
    
    return render(request, 'product/unit_detail.html', context)


@login_required
def warehouse_list(request):
    """
    عرض قائمة المخازن
    """
    warehouses = Warehouse.objects.all().prefetch_related('stocks')
    
    # بحث
    search_query = request.GET.get('search', '')
    if search_query:
        warehouses = warehouses.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # الحالة
    status = request.GET.get('status', '')
    if status == 'active':
        warehouses = warehouses.filter(is_active=True)
    elif status == 'inactive':
        warehouses = warehouses.filter(is_active=False)
    
    # إحصائيات
    total_warehouses = Warehouse.objects.count()
    active_warehouses = Warehouse.objects.filter(is_active=True).count()
    
    context = {
        'warehouses': warehouses,
        'total_warehouses': total_warehouses,
        'active_warehouses': active_warehouses,
        'page_title': 'المخازن',
        'page_icon': 'fas fa-warehouse',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المخزون', 'url': '#', 'icon': 'fas fa-boxes'},
            {'title': 'المخازن', 'active': True}
        ],
    }
    
    return render(request, 'product/warehouse_list.html', context)


@login_required
def warehouse_create(request):
    """
    إضافة مخزن جديد
    """
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save()
            messages.success(request, f'تم إضافة المخزن "{warehouse.name}" بنجاح')
            return redirect('product:warehouse_list')
    else:
        form = WarehouseForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة مخزن جديد',
        'page_icon': 'fas fa-warehouse',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المخزون', 'url': '#', 'icon': 'fas fa-boxes'},
            {'title': 'المخازن', 'url': reverse('product:warehouse_list'), 'icon': 'fas fa-warehouse'},
            {'title': 'إضافة مخزن', 'active': True}
        ],
    }
    
    return render(request, 'product/warehouse_form.html', context)


@login_required
def warehouse_edit(request, pk):
    """
    تعديل مخزن
    """
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            warehouse = form.save()
            messages.success(request, f'تم تحديث المخزن "{warehouse.name}" بنجاح')
            return redirect('product:warehouse_list')
    else:
        form = WarehouseForm(instance=warehouse)
    
    context = {
        'form': form,
        'warehouse': warehouse,
        'page_title': f'تعديل المخزن: {warehouse.name}',
        'page_icon': 'fas fa-edit',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المخزون', 'url': '#', 'icon': 'fas fa-boxes'},
            {'title': 'المخازن', 'url': reverse('product:warehouse_list'), 'icon': 'fas fa-warehouse'},
            {'title': f'تعديل: {warehouse.name}', 'active': True}
        ],
    }
    
    return render(request, 'product/warehouse_form.html', context)


@login_required
def warehouse_delete(request, pk):
    """
    حذف مخزن
    """
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        name = warehouse.name
        warehouse.delete()
        messages.success(request, f'تم حذف المخزن "{name}" بنجاح')
        return redirect('product:warehouse_list')
    
    context = {
        'warehouse': warehouse,
        'page_title': f'حذف المخزن: {warehouse.name}',
        'page_icon': 'fas fa-trash-alt',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المخزون', 'url': '#', 'icon': 'fas fa-boxes'},
            {'title': 'المخازن', 'url': reverse('product:warehouse_list'), 'icon': 'fas fa-warehouse'},
            {'title': f'حذف: {warehouse.name}', 'active': True}
        ],
    }
    
    return render(request, 'product/warehouse_confirm_delete.html', context)


@login_required
def warehouse_detail(request, pk):
    """
    عرض تفاصيل المخزن
    """
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    # الأرصدة المتاحة في المخزن
    stocks = Stock.objects.filter(warehouse=warehouse).select_related(
        'product', 'product__category', 'product__brand', 'product__unit'
    )
    
    # المنتجات المتاحة للإضافة إلى المخزن
    all_products = Product.objects.filter(is_active=True).select_related('category', 'brand', 'unit')
    
    # المخازن الأخرى للتحويل
    other_warehouses = Warehouse.objects.filter(is_active=True).exclude(pk=warehouse.pk)
    
    # آخر حركات المخزون في هذا المخزن
    recent_movements = StockMovement.objects.filter(
        warehouse=warehouse
    ).select_related(
        'product', 'warehouse', 'destination_warehouse', 'created_by'
    ).order_by('-timestamp')[:10]
    
    # إحصائيات المخزون
    total_products = stocks.count()
    in_stock_products = stocks.filter(quantity__gt=0).count()
    low_stock_products = stocks.filter(
        quantity__gt=0,
        quantity__lt=F('product__min_stock')
    ).count()
    out_of_stock_products = stocks.filter(quantity__lte=0).count()
    
    context = {
        'warehouse': warehouse,
        'stocks': stocks,
        'all_products': all_products,
        'other_warehouses': other_warehouses,
        'recent_movements': recent_movements,
        'total_products': total_products,
        'in_stock_products': in_stock_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'page_title': f'تفاصيل المخزن: {warehouse.name}',
        'page_icon': 'fas fa-warehouse',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المخزون', 'url': '#', 'icon': 'fas fa-boxes'},
            {'title': 'المخازن', 'url': reverse('product:warehouse_list'), 'icon': 'fas fa-warehouse'},
            {'title': warehouse.name, 'active': True}
        ],
    }
    
    return render(request, 'product/warehouse_detail.html', context)


@login_required
def stock_list(request):
    """
    عرض قائمة المخزون
    """
    stocks = Stock.objects.all().select_related(
        'product', 'product__category', 'product__brand', 'product__unit',
        'warehouse'
    )
    
    # فلترة حسب المخزن
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        stocks = stocks.filter(warehouse_id=warehouse_id)
    
    # فلترة حسب المنتج
    product_id = request.GET.get('product')
    if product_id:
        stocks = stocks.filter(product_id=product_id)
    
    # فلترة حسب الكمية
    stock_status = request.GET.get('stock_status')
    if stock_status == 'in_stock':
        stocks = stocks.filter(quantity__gt=0)
    elif stock_status == 'out_of_stock':
        stocks = stocks.filter(quantity__lte=0)
    elif stock_status == 'low_stock':
        stocks = stocks.filter(
            quantity__gt=0,
            quantity__lt=F('product__min_stock')
        )
    
    # المخازن والمنتجات لعناصر التصفية
    warehouses = Warehouse.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).select_related('category')
    
    # ترقيم الصفحات
    paginator = Paginator(stocks, 20)
    page = request.GET.get('page')
    try:
        stocks = paginator.page(page)
    except PageNotAnInteger:
        stocks = paginator.page(1)
    except EmptyPage:
        stocks = paginator.page(paginator.num_pages)
    
    context = {
        'stocks': stocks,
        'warehouses': warehouses,
        'products': products,
        'warehouse_id': warehouse_id,
        'product_id': product_id,
        'stock_status': stock_status,
        'page_title': 'جرد المخزون',
        'page_icon': 'fas fa-clipboard-list',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المخزون', 'url': '#', 'icon': 'fas fa-boxes'},
            {'title': 'جرد المخزون', 'active': True}
        ],
    }
    
    return render(request, 'product/stock_list.html', context)


@login_required
def stock_detail(request, pk):
    """
    عرض تفاصيل المخزون
    """
    stock = get_object_or_404(Stock, pk=pk)
    
    # حركات المخزون
    movements = StockMovement.objects.filter(
        product=stock.product,
        warehouse=stock.warehouse
    ).order_by('-timestamp')
    
    context = {
        'stock': stock,
        'movements': movements,
        'title': f'تفاصيل المخزون: {stock.product.name}',
    }
    
    return render(request, 'product/stock_detail.html', context)


@login_required
def stock_adjust(request, pk):
    """
    تسوية المخزون
    """
    stock = get_object_or_404(Stock, pk=pk)
    
    if request.method == 'POST':
        quantity = request.POST.get('quantity', 0)
        notes = request.POST.get('notes', '')
        
        # إنشاء حركة تسوية
        StockMovement.objects.create(
            product=stock.product,
            warehouse=stock.warehouse,
            movement_type='adjustment',
            quantity=abs(Decimal(quantity)),
            notes=notes,
            created_by=request.user
        )
        
        # تحديث المخزون
        stock.quantity = Decimal(quantity)
        stock.save()
        
        messages.success(request, f'تم تسوية المخزون بنجاح')
        return redirect('product:stock_detail', pk=stock.pk)
    
    context = {
        'stock': stock,
        'title': f'تسوية المخزون: {stock.product.name}',
    }
    
    return render(request, 'product/stock_adjust.html', context)


@login_required
def stock_movement_list(request):
    """
    عرض قائمة حركات المخزون
    """
    movements = StockMovement.objects.all().select_related(
        'product', 'warehouse', 'destination_warehouse', 'created_by'
    ).order_by('-timestamp')
    
    # تصفية حسب البحث
    search_query = request.GET.get('search', '')
    if search_query:
        movements = movements.filter(
            Q(reference__icontains=search_query) |
            Q(product__name__icontains=search_query)
        )
    
    # تصفية حسب المخزن
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        movements = movements.filter(
            Q(warehouse_id=warehouse_id) | Q(destination_warehouse_id=warehouse_id)
        )
    
    # تصفية حسب المنتج
    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)
    
    # تصفية حسب نوع الحركة
    movement_type = request.GET.get('movement_type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    
    # تصفية حسب التاريخ
    date_from = request.GET.get('date_from')
    if date_from:
        movements = movements.filter(timestamp__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        movements = movements.filter(timestamp__date__lte=date_to)
    
    # إحصائيات
    total_movements = movements.count()
    total_quantity = movements.aggregate(total=Sum('quantity'))['total'] or 0
    
    # عدد الحركات حسب نوعها
    in_movements = movements.filter(movement_type='in').count()
    out_movements = movements.filter(movement_type='out').count()
    transfer_movements = movements.filter(movement_type='transfer').count()
    adjustment_movements = movements.filter(movement_type='adjustment').count()
    
    # كل المخازن والمنتجات لقائمة الاختيار
    warehouses = Warehouse.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')
    
    # ترقيم الصفحات
    paginator = Paginator(movements, 30)
    page = request.GET.get('page')
    try:
        movements = paginator.page(page)
    except PageNotAnInteger:
        movements = paginator.page(1)
    except EmptyPage:
        movements = paginator.page(paginator.num_pages)
    
    context = {
        'movements': movements,
        'warehouses': warehouses,
        'products': products,
        'total_movements': total_movements,
        'total_quantity': total_quantity,
        'in_movements': in_movements,
        'out_movements': out_movements,
        'transfer_movements': transfer_movements,
        'adjustment_movements': adjustment_movements,
        'page_title': 'حركات المخزون',
        'page_icon': 'fas fa-exchange-alt',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المخزون', 'url': '#', 'icon': 'fas fa-boxes'},
            {'title': 'حركات المخزون', 'active': True}
        ],
    }
    
    return render(request, 'product/stock_movement_list.html', context)


@login_required
def stock_movement_create(request):
    """
    إضافة حركة مخزون جديدة
    """
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            # تعيين نوع المستند للحركات اليدوية
            movement.document_type = 'other'
            movement.save()
            
            messages.success(request, f'تم إضافة حركة المخزون بنجاح')
            return redirect('product:stock_movement_list')
    else:
        form = StockMovementForm()
    
    context = {
        'form': form,
        'title': 'إضافة حركة مخزون جديدة',
    }
    
    return render(request, 'product/stock_movement_form.html', context)


@login_required
def stock_movement_detail(request, pk):
    """
    عرض تفاصيل حركة المخزون
    """
    movement = get_object_or_404(StockMovement.objects.select_related(
        'product', 'product__category', 'product__brand', 'product__unit',
        'warehouse', 'destination_warehouse', 'created_by'
    ), pk=pk)
    
    # حساب المخزون قبل وبعد الحركة
    if movement.movement_type in ['in', 'transfer_in']:
        previous_stock = movement.quantity_before
        current_stock = movement.quantity_after
    elif movement.movement_type in ['out', 'transfer_out']:
        previous_stock = movement.quantity_before
        current_stock = movement.quantity_after
    else:  # adjustment
        previous_stock = movement.quantity_before
        current_stock = movement.quantity_after
    
    # حركات متعلقة بنفس المنتج في نفس المخزن
    related_movements = StockMovement.objects.filter(
        product=movement.product,
        warehouse=movement.warehouse
    ).select_related(
        'product', 'warehouse', 'destination_warehouse', 'created_by'
    ).order_by('-timestamp')[:10]
    
    context = {
        'movement': movement,
        'previous_stock': previous_stock,
        'current_stock': current_stock,
        'related_movements': related_movements,
        'title': _('تفاصيل حركة المخزون'),
    }
    
    return render(request, 'product/stock_movement_detail.html', context)


@login_required
def stock_movement_delete(request, pk):
    """
    حذف حركة مخزون
    """
    movement = get_object_or_404(StockMovement, pk=pk)
    
    # جمع معلومات العناصر المرتبطة بهذه الحركة
    related_objects = {}
    
    if request.method == 'POST':
        # استرجاع معلومات المخزن والمنتج قبل الحذف
        warehouse = movement.warehouse
        product = movement.product
        
        # الغاء تأثير حركة المخزون
        if movement.movement_type == 'in':
            # إذا كانت حركة إضافة، نقوم بخصم الكمية
            stock = Stock.objects.get(warehouse=warehouse, product=product)
            stock.quantity -= Decimal(movement.quantity)
            stock.save()
        elif movement.movement_type == 'out':
            # إذا كانت حركة سحب، نقوم بإضافة الكمية
            stock = Stock.objects.get(warehouse=warehouse, product=product)
            stock.quantity += Decimal(movement.quantity)
            stock.save()
        elif movement.movement_type == 'transfer' and movement.destination_warehouse:
            # إذا كانت حركة تحويل، نقوم بعكس التحويل
            source_stock = Stock.objects.get(warehouse=warehouse, product=product)
            dest_stock = Stock.objects.get(warehouse=movement.destination_warehouse, product=product)
            
            source_stock.quantity += Decimal(movement.quantity)
            dest_stock.quantity -= Decimal(movement.quantity)
            
            source_stock.save()
            dest_stock.save()
        
        # حذف حركة المخزون
        movement.delete()
        
        messages.success(request, _('تم حذف حركة المخزون بنجاح'))
        return redirect('product:stock_movement_list')
    
    context = {
        'object': movement,
        'related_objects': related_objects,
        'back_url': reverse('product:stock_movement_list'),
        'title': _('حذف حركة المخزون'),
    }
    
    return render(request, 'product/stock_movement_confirm_delete.html', context)


@login_required
@require_POST
def add_stock_movement(request):
    """
    واجهة برمجة لإضافة حركة مخزون (إضافة/سحب/تعديل/تحويل)
    
    معلمات الطلب:
    - product_id: معرف المنتج
    - warehouse_id: معرف المخزن
    - movement_type: نوع الحركة (in, out, adjustment, transfer)
    - quantity: الكمية
    - destination_warehouse: معرف المخزن المستلم (للتحويل فقط)
    - reference_number: رقم المرجع (اختياري)
    - notes: ملاحظات (اختياري)
    
    الاستجابة:
    - success: حالة النجاح (true/false)
    - message: رسالة نجاح أو خطأ
    - movement_id: معرف حركة المخزون الجديدة (في حالة النجاح)
    - current_stock: المخزون الحالي بعد التحديث (في حالة النجاح)
    """
    try:
        # التحقق من وجود المعلمات الأساسية
        product_id = request.POST.get('product_id') or request.POST.get('product')
        warehouse_id = request.POST.get('warehouse_id')
        movement_type = request.POST.get('movement_type')
        quantity = request.POST.get('quantity')
        
        # التحقق من وجود جميع المعلمات المطلوبة
        if not all([product_id, warehouse_id, movement_type, quantity]):
            return JsonResponse({
                'success': False, 
                'error': _('جميع الحقول مطلوبة: product_id, warehouse_id, movement_type, quantity')
            })
        
        # التحقق من صحة البيانات
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': _('المنتج غير موجود')
            })
            
        try:
            warehouse = Warehouse.objects.get(pk=warehouse_id)
        except Warehouse.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': _('المخزن غير موجود')
            })
        
        # التحقق من صحة الكمية
        try:
            quantity = Decimal(quantity)
            if quantity <= 0:
                return JsonResponse({
                    'success': False, 
                    'error': _('يجب أن تكون الكمية أكبر من صفر')
                })
        except ValueError:
            return JsonResponse({
                'success': False, 
                'error': _('الكمية يجب أن تكون رقمًا صحيحًا')
            })
        
        # التحقق من نوع الحركة
        if movement_type not in ['in', 'out', 'adjustment', 'transfer']:
            return JsonResponse({
                'success': False, 
                'error': _('نوع الحركة غير صحيح. القيم المقبولة: in, out, adjustment, transfer')
            })
        
        # الحصول على المخزون الحالي أو إنشاء سجل جديد
        stock, created = Stock.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={'quantity': 0}
        )
        
        # حفظ المخزون الحالي قبل التعديل
        current_stock = stock.quantity
        
        # تنفيذ عملية المخزون
        if movement_type == 'in':
            # إضافة مخزون
            stock.quantity += Decimal(quantity)
            message = _('تمت إضافة {} وحدة من {} إلى المخزون').format(quantity, product.name)
            
        elif movement_type == 'out':
            # سحب مخزون
            if stock.quantity < Decimal(quantity):
                return JsonResponse({
                    'success': False, 
                    'error': _('الكمية غير كافية في المخزون. المتاح حالياً: {}').format(stock.quantity)
                })
            
            stock.quantity -= Decimal(quantity)
            message = _('تم سحب {} وحدة من {} من المخزون').format(quantity, product.name)
            
        elif movement_type == 'adjustment':
            # تعديل المخزون (تعيين قيمة محددة)
            old_quantity = stock.quantity
            stock.quantity = Decimal(quantity)
            message = _('تم تعديل مخزون {} من {} إلى {}').format(
                product.name, old_quantity, quantity
            )
            
        elif movement_type == 'transfer':
            # تحويل مخزون بين المخازن
            destination_warehouse_id = request.POST.get('destination_warehouse')
            
            if not destination_warehouse_id:
                return JsonResponse({
                    'success': False, 
                    'error': _('يجب تحديد المخزن المستلم للتحويل')
                })
            
            if destination_warehouse_id == warehouse_id:
                return JsonResponse({
                    'success': False, 
                    'error': _('لا يمكن التحويل إلى نفس المخزن')
                })
            
            try:
                destination_warehouse = Warehouse.objects.get(pk=destination_warehouse_id)
            except Warehouse.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'error': _('المخزن المستلم غير موجود')
                })
            
            # التحقق من كفاية المخزون
            if stock.quantity < Decimal(quantity):
                return JsonResponse({
                    'success': False, 
                    'error': _('الكمية غير كافية للتحويل. المتاح حالياً: {}').format(stock.quantity)
                })
                
            # خصم من المخزن المصدر
            stock.quantity -= Decimal(quantity)
            
            # إضافة إلى المخزن المستلم
            dest_stock, created = Stock.objects.get_or_create(
                product=product,
                warehouse=destination_warehouse,
                defaults={'quantity': Decimal('0')}
            )
            
            dest_before = dest_stock.quantity
            dest_stock.quantity += Decimal(quantity)
            dest_stock.save()
            
            message = _('تم تحويل {} وحدة من {} من {} إلى {}').format(
                quantity, product.name, warehouse.name, destination_warehouse.name
            )
        
        # حفظ التغييرات
        stock.save()
        
        # إنشاء سجل حركة المخزون
        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=current_stock,
            quantity_after=stock.quantity,
            reference_number=request.POST.get('reference_number', ''),
            notes=request.POST.get('notes', ''),
            created_by=request.user
        )
        
        # إذا كانت حركة تحويل، حفظ المخزن المستلم
        if movement_type == 'transfer' and 'destination_warehouse' in locals():
            movement.destination_warehouse = destination_warehouse
            movement.save()
            
            # إنشاء سجل حركة للمخزن المستلم
            StockMovement.objects.create(
                product=product,
                warehouse=destination_warehouse,
                movement_type='transfer_in',
                quantity=quantity,
                quantity_before=dest_before,
                quantity_after=dest_stock.quantity,
                reference_number=request.POST.get('reference_number', ''),
                notes=_('تحويل من مخزن {}').format(warehouse.name),
                created_by=request.user
            )
        
        # تسجيل الحركة في سجل النظام
        logger.info(
            'Stock movement created: %s %s %s units of %s in %s by %s',
            movement_type, 
            quantity, 
            product.name,
            warehouse.name,
            request.user.username
        )
        
        return JsonResponse({
            'success': True, 
            'message': message,
            'movement_id': movement.id,
            'current_stock': stock.quantity
        })
        
    except ValidationError as e:
        logger.warning('Validation error in add_stock_movement: %s', str(e))
        return JsonResponse({
            'success': False, 
            'error': str(e)
        })
    except Exception as e:
        # سجل الخطأ ولكن لا ترسل تفاصيل للمستخدم
        logger.error('Error in add_stock_movement: %s', str(e), exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': _('حدث خطأ أثناء تنفيذ العملية. يرجى المحاولة مرة أخرى لاحقًا.')
        })


@login_required
def export_stock_movements(request):
    """
    تصدير حركات المخزون كملف CSV أو PDF
    """
    # الحصول على الحركات مع تطبيق الفلاتر
    movements = StockMovement.objects.all().select_related(
        'product', 'product__category', 'product__brand',
        'warehouse', 'destination_warehouse', 'created_by'
    ).order_by('-timestamp')
    
    # تطبيق الفلاتر
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        movements = movements.filter(
            Q(warehouse_id=warehouse_id) | 
            Q(destination_warehouse_id=warehouse_id)
        )
    
    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)
    
    movement_type = request.GET.get('movement_type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    
    date_from = request.GET.get('date_from')
    if date_from:
        movements = movements.filter(timestamp__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        movements = movements.filter(timestamp__date__lte=date_to)
    
    # تحديد نوع التصدير
    export_format = request.GET.get('format', 'csv')
    
    if export_format == 'csv':
        # تصدير CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_movements.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'المنتج', 'المخزن', 'النوع', 'الكمية', 
            'المخزون قبل', 'المخزون بعد', 'المخزن المستلم',
            'رقم المرجع', 'ملاحظات', 'التاريخ'
        ])
        
        for movement in movements:
            writer.writerow([
                movement.id,
                movement.product.name,
                movement.warehouse.name,
                movement.get_movement_type_display(),
                movement.quantity,
                movement.quantity_before,
                movement.quantity_after,
                movement.destination_warehouse.name if movement.destination_warehouse else '',
                movement.reference_number,
                movement.notes,
                movement.timestamp.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    
    elif export_format == 'pdf':
        # تصدير PDF
        # هنا سنستخدم HTML كوسيط لإنشاء PDF
        template = get_template('product/exports/stock_movements_pdf.html')
        context = {
            'movements': movements,
            'today': timezone.now(),
            'request': request,
        }
        html = template.render(context)
        
        # إنشاء PDF
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="stock_movements.pdf"'
            return response
        
        return HttpResponse('Error generating PDF', status=400)
    
    else:
        # نوع تصدير غير معروف
        return HttpResponse('Invalid export format', status=400)


@login_required
def export_warehouse_inventory_all(request):
    """
    تصدير المخزون من جميع المخازن أو حسب التصفية
    """
    # جلب المخزون
    stocks = Stock.objects.all().select_related('product', 'product__category', 'warehouse')
    
    # التصفية حسب المخزن إذا تم تحديده
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id and warehouse_id.isdigit():
        stocks = stocks.filter(warehouse_id=warehouse_id)
    
    # التصفية حسب المنتج إذا تم تحديده
    product_id = request.GET.get('product')
    if product_id and product_id.isdigit():
        stocks = stocks.filter(product_id=product_id)
    
    # التصفية حسب الكمية
    min_quantity = request.GET.get('min_quantity')
    if min_quantity and min_quantity.isdigit():
        stocks = stocks.filter(quantity__gte=min_quantity)
    
    max_quantity = request.GET.get('max_quantity')
    if max_quantity and max_quantity.isdigit():
        stocks = stocks.filter(quantity__lte=max_quantity)
    
    # تحديد نوع التصدير
    export_format = request.GET.get('format', 'csv')
    
    if export_format == 'csv':
        # تصدير CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'رقم المنتج', 'اسم المنتج', 'SKU', 'المخزن', 'الفئة', 'الكمية', 
            'الحد الأدنى', 'الحد الأقصى', 'حالة المخزون'
        ])
        
        for stock in stocks:
            # تحديد حالة المخزون
            if stock.quantity <= 0:
                status = 'نفذ من المخزون'
            elif stock.quantity < stock.product.min_stock:
                status = 'مخزون منخفض'
            elif stock.quantity > stock.product.max_stock:
                status = 'مخزون زائد'
            else:
                status = 'مخزون جيد'
            
            writer.writerow([
                stock.product.id,
                stock.product.name,
                stock.product.sku,
                stock.warehouse.name,
                stock.product.category.name if stock.product.category else '',
                stock.quantity,
                stock.product.min_stock,
                stock.product.max_stock,
                status
            ])
        
        return response
    
    # يمكن إضافة تصدير PDF هنا لاحقاً
    return redirect('product:stock_list')


@login_required
def export_warehouse_inventory(request, warehouse_id=None):
    """
    تصدير مخزون مخزن معين
    """
    # إذا لم يتم تحديد رقم المخزن، نحاول جلبه من الاستعلام
    if warehouse_id is None:
        warehouse_id = request.GET.get('warehouse')
        if not warehouse_id or not warehouse_id.isdigit():
            # إذا لم يتم تحديد مخزن، نستخدم دالة تصدير كل المخزون
            return export_warehouse_inventory_all(request)
    
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    stocks = Stock.objects.filter(warehouse=warehouse).select_related('product')
    
    # التصفية حسب المنتج إذا تم تحديده
    product_id = request.GET.get('product')
    if product_id and product_id.isdigit():
        stocks = stocks.filter(product_id=product_id)
    
    # تصدير CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{warehouse.name}_inventory.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'رقم المنتج', 'اسم المنتج', 'SKU', 'الفئة', 'الكمية', 
        'الحد الأدنى', 'الحد الأقصى', 'حالة المخزون'
    ])
    
    for stock in stocks:
        # تحديد حالة المخزون
        if stock.quantity <= 0:
            status = 'نفذ من المخزون'
        elif stock.quantity < stock.product.min_stock:
            status = 'مخزون منخفض'
        elif stock.quantity > stock.product.max_stock:
            status = 'مخزون زائد'
        else:
            status = 'مخزون جيد'
        
        writer.writerow([
            stock.product.id,
            stock.product.name,
            stock.product.sku,
            stock.product.category.name if stock.product.category else '',
            stock.quantity,
            stock.product.min_stock,
            stock.product.max_stock,
            status
        ])
    
    return response


@login_required
def low_stock_products(request):
    """
    عرض المنتجات ذات المخزون المنخفض
    """
    # الحصول على المنتجات ذات المخزون المنخفض
    low_stock_items = Stock.objects.filter(
        quantity__gt=0,
        quantity__lt=F('product__min_stock')
    ).select_related(
        'product', 'product__category', 'product__brand', 'product__unit',
        'warehouse'
    )
    
    context = {
        'low_stock_items': low_stock_items,
        'title': _('المنتجات ذات المخزون المنخفض'),
    }
    
    return render(request, 'product/low_stock.html', context)


@login_required
def add_product_image(request):
    """
    إضافة صورة منتج من خلال AJAX
    """
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product_id')
            image = request.FILES.get('image')
            alt_text = request.POST.get('alt_text', '')
            is_primary = request.POST.get('is_primary') == 'on'
            
            if not product_id or not image:
                return JsonResponse({'success': False, 'error': _('بيانات غير كاملة')})
            
            # التأكد من وجود المنتج
            product = get_object_or_404(Product, pk=product_id)
            
            # إذا كانت الصورة الأساسية، نقوم بإلغاء تحديد الصور الأساسية الأخرى
            if is_primary:
                ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
            
            # إنشاء صورة جديدة
            product_image = ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=alt_text,
                is_primary=is_primary
            )
            
            return JsonResponse({
                'success': True,
                'id': product_image.id,
                'url': product_image.image.url
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': _('طلب غير صالح')})


@login_required
def delete_product_image(request, pk):
    """
    حذف صورة منتج
    """
    if request.method == 'POST':
        try:
            image = get_object_or_404(ProductImage, pk=pk)
            image.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': _('طلب غير صالح')})


@login_required
def get_stock_by_warehouse(request):
    """
    API للحصول على المخزون المتاح في مستودع معين
    """
    warehouse_id = request.GET.get('warehouse')
    
    # تسجيل معلومات الطلب للتشخيص
    logger.info(f"طلب API للمخزون - المستودع: {warehouse_id}, الطريقة: {request.method}")
    
    if not warehouse_id:
        logger.warning("API المخزون: لم يتم توفير معرف المستودع")
        return JsonResponse({}, status=400)
    
    try:
        # التحقق من وجود المستودع
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        
        # الحصول على المخزون المتاح في المستودع المحدد
        stocks = Stock.objects.filter(warehouse=warehouse).values('product_id', 'quantity')
        
        # بناء قاموس به المنتجات والمخزون المتاح
        stock_data = {}
        for stock in stocks:
            stock_data[str(stock['product_id'])] = stock['quantity']
        
        logger.info(f"API المخزون: تم استرجاع {len(stock_data)} من المنتجات للمستودع {warehouse.name}")
        return JsonResponse(stock_data)
    
    except Exception as e:
        logger.error(f"خطأ في API المخزون: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def product_stock_view(request, pk):
    """
    عرض مخزون المنتج في جميع المخازن
    """
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand', 'unit'), 
        pk=pk
    )
    
    # الحصول على المخزون الحالي للمنتج في كل مستودع
    stock_items = Stock.objects.filter(product=product).select_related('warehouse')
    
    # آخر حركات المخزون
    stock_movements = StockMovement.objects.filter(product=product).select_related(
        'warehouse', 'destination_warehouse', 'created_by'
    ).order_by('-timestamp')[:20]
    
    # إجمالي المخزون
    total_stock = stock_items.aggregate(total=Sum('quantity'))['total'] or 0
    
    # المخازن المتاحة لإضافة المخزون
    warehouses = Warehouse.objects.filter(is_active=True)
    
    context = {
        'product': product,
        'stock_items': stock_items,
        'stock_movements': stock_movements,
        'total_stock': total_stock,
        'warehouses': warehouses,
        'page_title': f'مخزون المنتج: {product.name}',
        'page_icon': 'fas fa-boxes',
        'breadcrumb_items': [
            {'title': 'الرئيسية', 'url': reverse('core:dashboard'), 'icon': 'fas fa-home'},
            {'title': 'المنتجات', 'url': reverse('product:product_list'), 'icon': 'fas fa-box'},
            {'title': product.name, 'url': reverse('product:product_detail', args=[product.pk]), 'icon': 'fas fa-info-circle'},
            {'title': 'المخزون', 'active': True}
        ],
    }
    
    return render(request, 'product/product_stock.html', context)
