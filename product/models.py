from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    """
    نموذج فئات المنتجات
    """
    name = models.CharField(_('اسم الفئة'), max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True,
                              related_name='children', verbose_name=_('الفئة الأم'))
    description = models.TextField(_('الوصف'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('فئة')
        verbose_name_plural = _('الفئات')
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name


class Brand(models.Model):
    """
    نموذج العلامات التجارية
    """
    name = models.CharField(_('اسم العلامة التجارية'), max_length=255)
    description = models.TextField(_('الوصف'), blank=True, null=True)
    logo = models.ImageField(_('الشعار'), upload_to='brands', blank=True, null=True)
    website = models.URLField(_('الموقع الإلكتروني'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('علامة تجارية')
        verbose_name_plural = _('العلامات التجارية')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Unit(models.Model):
    """
    نموذج وحدات القياس
    """
    name = models.CharField(_('اسم الوحدة'), max_length=50)
    symbol = models.CharField(_('الرمز'), max_length=10)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('وحدة قياس')
        verbose_name_plural = _('وحدات القياس')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"


class Product(models.Model):
    """
    نموذج المنتجات
    """
    name = models.CharField(_('اسم المنتج'), max_length=255)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products',
                                verbose_name=_('الفئة'))
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products',
                             verbose_name=_('العلامة التجارية'), blank=True, null=True)
    description = models.TextField(_('الوصف'), blank=True, null=True)
    sku = models.CharField(_('رمز المنتج'), max_length=50, unique=True)
    barcode = models.CharField(_('الباركود'), max_length=50, blank=True, null=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='products',
                            verbose_name=_('وحدة القياس'))
    cost_price = models.DecimalField(_('سعر التكلفة'), max_digits=12, decimal_places=2,
                                    validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(_('سعر البيع'), max_digits=12, decimal_places=2,
                                       validators=[MinValueValidator(0)])
    min_stock = models.PositiveIntegerField(_('الحد الأدنى للمخزون'), default=0)
    max_stock = models.PositiveIntegerField(_('الحد الأقصى للمخزون'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    is_featured = models.BooleanField(_('مميز'), default=False)
    tax_rate = models.DecimalField(_('نسبة الضريبة'), max_digits=5, decimal_places=2,
                                  default=0, validators=[MinValueValidator(0)])
    discount_rate = models.DecimalField(_('نسبة الخصم'), max_digits=5, decimal_places=2,
                                       default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  verbose_name=_('أنشئ بواسطة'), related_name='products_created')
    
    class Meta:
        verbose_name = _('منتج')
        verbose_name_plural = _('المنتجات')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def current_stock(self):
        """
        حساب المخزون الحالي في جميع المستودعات
        """
        from django.db.models import Sum
        # معالجة حالة عدم وجود مخزون
        stock = self.stocks.aggregate(Sum('quantity'))
        return stock['quantity__sum'] or 0
    
    @property
    def profit_margin(self):
        """
        حساب هامش الربح
        """
        if self.cost_price > 0:
            return (self.selling_price - self.cost_price) / self.cost_price * 100
        return 0


class ProductImage(models.Model):
    """
    نموذج صور المنتجات
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images',
                               verbose_name=_('المنتج'))
    image = models.ImageField(_('الصورة'), upload_to='products')
    is_primary = models.BooleanField(_('صورة رئيسية'), default=False)
    alt_text = models.CharField(_('نص بديل'), max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('صورة منتج')
        verbose_name_plural = _('صور المنتجات')
        ordering = ['-is_primary', 'created_at']
    
    def __str__(self):
        return f"{self.product} - {self.alt_text or 'صورة'}"


class ProductVariant(models.Model):
    """
    نموذج متغيرات المنتج
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants',
                               verbose_name=_('المنتج'))
    name = models.CharField(_('اسم المتغير'), max_length=255)
    sku = models.CharField(_('رمز المتغير'), max_length=50, unique=True)
    barcode = models.CharField(_('الباركود'), max_length=50, blank=True, null=True)
    cost_price = models.DecimalField(_('سعر التكلفة'), max_digits=12, decimal_places=2,
                                    validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(_('سعر البيع'), max_digits=12, decimal_places=2,
                                       validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(_('المخزون'), default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('متغير منتج')
        verbose_name_plural = _('متغيرات المنتجات')
        ordering = ['product', 'name']
    
    def __str__(self):
        return f"{self.product} - {self.name} ({self.sku})"


class Warehouse(models.Model):
    """
    نموذج المخازن
    """
    name = models.CharField(_('اسم المخزن'), max_length=255)
    code = models.CharField(_('كود المخزن'), max_length=20, unique=True)
    location = models.CharField(_('الموقع'), max_length=255, blank=True, null=True)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                               verbose_name=_('المدير'), null=True, blank=True, 
                               related_name='managed_warehouses')
    description = models.TextField(_('الوصف'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مخزن')
        verbose_name_plural = _('المخازن')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Stock(models.Model):
    """
    نموذج المخزون
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks',
                               verbose_name=_('المنتج'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks',
                                 verbose_name=_('المخزن'))
    quantity = models.PositiveIntegerField(_('الكمية'), default=0)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('مخزون')
        verbose_name_plural = _('المخزون')
        unique_together = ('product', 'warehouse')
    
    def __str__(self):
        return f"{self.product} - {self.warehouse} ({self.quantity})"


class StockMovement(models.Model):
    """
    نموذج حركة المخزون
    """
    MOVEMENT_TYPES = (
        ('in', _('وارد')),
        ('out', _('صادر')),
        ('transfer', _('تحويل')),
        ('adjustment', _('تسوية')),
        ('return_in', _('مرتجع وارد')),
        ('return_out', _('مرتجع صادر')),
    )
    
    # أنواع مستندات الحركة
    DOCUMENT_TYPES = (
        ('purchase', _('شراء')),
        ('purchase_return', _('مرتجع مشتريات')),
        ('sale', _('بيع')),
        ('sale_return', _('مرتجع مبيعات')),
        ('transfer', _('تحويل')),
        ('adjustment', _('جرد')),
        ('opening', _('رصيد')),
        ('other', _('أخرى')),
    )
    
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements',
                               verbose_name=_('المنتج'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='movements',
                                 verbose_name=_('المخزن'))
    movement_type = models.CharField(_('نوع الحركة'), max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField(_('الكمية'))
    reference_number = models.CharField(_('رقم المرجع'), max_length=50, blank=True, null=True)
    document_type = models.CharField(_('نوع المستند'), max_length=20, choices=DOCUMENT_TYPES, default='other')
    document_number = models.CharField(_('رقم المستند'), max_length=50, blank=True, null=True)
    notes = models.TextField(_('ملاحظات'), blank=True, null=True)
    timestamp = models.DateTimeField(_('تاريخ الحركة'), auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                  verbose_name=_('أنشئ بواسطة'), related_name='stock_movements_created')
    # للتحويلات
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT,
                                             verbose_name=_('المخزن المستلم'),
                                             related_name='incoming_movements',
                                             blank=True, null=True)
    
    # حقول لتتبع كمية المخزون قبل وبعد الحركة
    quantity_before = models.PositiveIntegerField(_('الكمية قبل'), default=0)
    quantity_after = models.PositiveIntegerField(_('الكمية بعد'), default=0)
    
    # خاصية لتخطي تحديث المخزون (للاستخدام الداخلي)
    _skip_update = False
    
    number = models.CharField(_('رقم الحركة'), max_length=50, unique=True, blank=True, null=True)
    
    class Meta:
        verbose_name = _('حركة المخزون')
        verbose_name_plural = _('حركات المخزون')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.product} - {self.movement_type} - {self.quantity} - {self.timestamp}"
    
    def save(self, *args, **kwargs):
        """
        تحديث كمية المخزون عند إنشاء حركة جديدة
        """
        # تحقق من عدم تخطي التحديث (للاستخدام عند استعادة البيانات)
        if not self._skip_update:
            try:
                # الحصول على مخزون المنتج في المخزن المحدد أو إنشاء سجل جديد إذا لم يكن موجوداً
                stock, created = Stock.objects.get_or_create(
                    product=self.product,
                    warehouse=self.warehouse,
                    defaults={'quantity': 0}
                )
                
                # تخزين قيمة المخزون قبل التحديث
                self.quantity_before = stock.quantity
                
                # تحديث الكمية حسب نوع الحركة
                if self.movement_type == 'in' or self.movement_type == 'return_in':
                    # إضافة للمخزون (شراء أو مرتجع مبيعات)
                    stock.quantity += self.quantity
                elif self.movement_type == 'out' or self.movement_type == 'return_out':
                    # خصم من المخزون (بيع أو مرتجع مشتريات)
                    # تأكد من عدم طرح أكثر من المخزون الحالي
                    if stock.quantity >= self.quantity:
                        stock.quantity -= self.quantity
                    else:
                        stock.quantity = 0
                elif self.movement_type == 'transfer':
                    # خصم من المخزن الحالي
                    if stock.quantity >= self.quantity:
                        stock.quantity -= self.quantity
                    else:
                        stock.quantity = 0
                    
                    # إضافة للمخزن المستلم
                    if self.destination_warehouse:
                        dest_stock, created = Stock.objects.get_or_create(
                            product=self.product,
                            warehouse=self.destination_warehouse,
                            defaults={'quantity': 0}
                        )
                        dest_stock.quantity += self.quantity
                        dest_stock.save()
                elif self.movement_type == 'adjustment':
                    # تعديل المخزون للوصول إلى كمية محددة
                    stock.quantity = self.quantity
                
                # تخزين قيمة المخزون بعد التحديث
                self.quantity_after = stock.quantity
                
                # حفظ التغييرات على المخزون
                stock.save()
            except Exception as e:
                # تسجيل الأخطاء دون إيقاف العملية
                print(f"خطأ في تحديث المخزون: {e}")
        
        # استمرار في عملية الحفظ الطبيعية
        if not self.number:
            # الحصول على الرقم التسلسلي
            serial = SerialNumber.objects.get_or_create(
                document_type='stock_movement',
                year=timezone.now().year,
                defaults={'prefix': 'MOV'}
            )[0]
            next_number = serial.get_next_number()
            self.number = f"{serial.prefix}{next_number:04d}"
        
        super().save(*args, **kwargs)


class SerialNumber(models.Model):
    """
    نموذج لتتبع الأرقام التسلسلية للمستندات
    """
    DOCUMENT_TYPES = (
        ('sale', _('فاتورة مبيعات')),
        ('purchase', _('فاتورة مشتريات')),
        ('stock_movement', _('حركة مخزون')),
    )
    
    document_type = models.CharField(_('نوع المستند'), max_length=20, choices=DOCUMENT_TYPES)
    last_number = models.PositiveIntegerField(_('آخر رقم'), default=0)
    prefix = models.CharField(_('بادئة'), max_length=10, blank=True)
    year = models.PositiveIntegerField(_('السنة'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('رقم تسلسلي')
        verbose_name_plural = _('الأرقام التسلسلية')
        unique_together = ['document_type', 'year']
    
    def get_next_number(self):
        """
        الحصول على الرقم التالي في التسلسل
        """
        # البحث عن آخر رقم مستخدم في هذا النوع من المستندات
        from django.db.models import Max
        from django.apps import apps
        
        # تحديد النموذج المناسب حسب نوع المستند
        if self.document_type == 'sale':
            model = apps.get_model('sale', 'Sale')
        elif self.document_type == 'purchase':
            model = apps.get_model('purchase', 'Purchase')
        else:
            model = apps.get_model('product', 'StockMovement')
        
        # استخراج الرقم من آخر مستند
        last_doc = model.objects.filter(
            number__startswith=self.prefix
        ).order_by('-number').first()
        
        if last_doc:
            # استخراج الرقم من آخر مستند
            try:
                last_number = int(last_doc.number.replace(self.prefix, ''))
                self.last_number = max(self.last_number, last_number)
            except ValueError:
                pass
        
        # زيادة الرقم
        self.last_number += 1
        self.save()
        return self.last_number
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.year} - {self.last_number}"
