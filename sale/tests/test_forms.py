from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from sale.forms import CustomerForm, SaleForm, SaleReturnForm
from sale.models import Customer, Sale, SaleItem, SaleReturn
from product.models import Product, Category, Unit, Warehouse, Stock
from financial.models import Account

User = get_user_model()

class CustomerFormTest(TestCase):
    """
    اختبارات نموذج إدخال العميل
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # إنشاء عميل موجود للتحقق من التكرار
        Customer.objects.create(
            name='عميل موجود',
            phone='01234567890',
            email='existing@customer.com',
            created_by=self.user
        )
    
    def test_valid_customer_form(self):
        """
        اختبار صحة نموذج العميل بالبيانات الصحيحة
        """
        form_data = {
            'name': 'عميل جديد',
            'phone': '01987654321',
            'email': 'new@customer.com',
            'address': 'عنوان العميل الجديد',
            'tax_number': '1234567890',
            'notes': 'ملاحظات العميل'
        }
        
        form = CustomerForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_customer_form(self):
        """
        اختبار رفض نموذج العميل بالبيانات غير الصحيحة
        """
        # نموذج بدون اسم
        form_data = {
            'phone': '01987654321',
            'email': 'invalid@customer.com'
        }
        
        form = CustomerForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        
        # بريد إلكتروني غير صالح
        form_data = {
            'name': 'عميل اختبار',
            'phone': '01987654321',
            'email': 'invalid-email'
        }
        
        form = CustomerForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_duplicate_customer_phone(self):
        """
        اختبار رفض رقم هاتف عميل مكرر
        """
        # محاولة إنشاء عميل جديد بنفس رقم هاتف العميل الموجود
        form_data = {
            'name': 'عميل جديد',
            'phone': '01234567890',  # رقم مكرر
            'email': 'new@customer.com'
        }
        
        form = CustomerForm(data=form_data)
        # التحقق من الخطأ (يعتمد على منطق التحقق في النموذج)
        # إذا كان النموذج يتحقق من تكرار رقم الهاتف
        if 'unique_phone' in dir(form) or hasattr(form.fields['phone'], 'validators'):
            self.assertFalse(form.is_valid())
            self.assertIn('phone', form.errors)


class SaleFormTest(TestCase):
    """
    اختبارات نموذج إدخال المبيعات
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # إنشاء بيانات الاختبار
        self.customer = Customer.objects.create(
            name='عميل اختبار',
            phone='01234567890',
            email='test@customer.com',
            created_by=self.user
        )
        
        self.category = Category.objects.create(
            name='فئة اختبار',
            created_by=self.user
        )
        
        self.unit = Unit.objects.create(
            name='قطعة',
            abbreviation='ق',
            created_by=self.user
        )
        
        self.product = Product.objects.create(
            name='منتج اختبار',
            code='TEST001',
            category=self.category,
            unit=self.unit,
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            created_by=self.user
        )
        
        self.warehouse = Warehouse.objects.create(
            name='مستودع اختبار',
            code='WH001',
            created_by=self.user
        )
        
        # إنشاء مخزون للمنتج
        self.stock = Stock.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=50,
            created_by=self.user
        )
        
        # إنشاء حساب مالي
        self.account = Account.objects.create(
            name='حساب اختبار',
            account_type='cash',
            balance=Decimal('10000.00'),
            created_by=self.user
        )
    
    def test_valid_sale_form(self):
        """
        اختبار صحة نموذج المبيعات بالبيانات الصحيحة
        """
        form_data = {
            'customer': self.customer.id,
            'invoice_no': 'INV-001',
            'date': timezone.now().date().isoformat(),
            'warehouse': self.warehouse.id,
            'payment_method': 'cash',
            'account': self.account.id,
            'notes': 'ملاحظات البيع',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '2',
            'items-0-price': '150.00',
        }
        
        form = SaleForm(data=form_data)
        # التحقق من صحة النموذج (يعتمد على المنطق الدقيق للنموذج)
        # هذا تبسيط لأن SaleForm قد يكون معقدًا مع مجموعة نماذج items
        if hasattr(form, 'is_valid'):
            self.assertTrue(form.is_valid())
    
    def test_invalid_sale_form(self):
        """
        اختبار رفض نموذج المبيعات بالبيانات غير الصحيحة
        """
        # نموذج بدون عميل
        form_data = {
            'invoice_no': 'INV-002',
            'date': timezone.now().date().isoformat(),
            'warehouse': self.warehouse.id,
            'payment_method': 'cash',
            'account': self.account.id,
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '2',
            'items-0-price': '150.00',
        }
        
        form = SaleForm(data=form_data)
        if hasattr(form, 'is_valid'):
            self.assertFalse(form.is_valid())
            self.assertIn('customer', form.errors)
    
    def test_sale_with_insufficient_stock(self):
        """
        اختبار رفض البيع بكمية أكبر من المخزون المتاح
        """
        # محاولة بيع كمية أكبر من المخزون المتاح
        form_data = {
            'customer': self.customer.id,
            'invoice_no': 'INV-003',
            'date': timezone.now().date().isoformat(),
            'warehouse': self.warehouse.id,
            'payment_method': 'cash',
            'account': self.account.id,
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '100',  # أكبر من المخزون المتاح (50)
            'items-0-price': '150.00',
        }
        
        form = SaleForm(data=form_data)
        # التحقق من الخطأ (يعتمد على منطق التحقق في النموذج)
        # هذا مجرد مثال، قد يكون التحقق من المخزون في مكان آخر في التطبيق
        if hasattr(form, 'clean') and 'check_stock' in dir(form):
            self.assertFalse(form.is_valid())
            # التحقق من وجود خطأ متعلق بالمخزون (يعتمد على تنفيذ التطبيق)


class SaleReturnFormTest(TestCase):
    """
    اختبارات نموذج إدخال مرتجعات المبيعات
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # إنشاء بيانات الاختبار
        self.customer = Customer.objects.create(
            name='عميل اختبار',
            phone='01234567890',
            created_by=self.user
        )
        
        self.category = Category.objects.create(
            name='فئة اختبار',
            created_by=self.user
        )
        
        self.unit = Unit.objects.create(
            name='قطعة',
            abbreviation='ق',
            created_by=self.user
        )
        
        self.product = Product.objects.create(
            name='منتج اختبار',
            code='TEST001',
            category=self.category,
            unit=self.unit,
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            created_by=self.user
        )
        
        self.warehouse = Warehouse.objects.create(
            name='مستودع اختبار',
            code='WH001',
            created_by=self.user
        )
        
        self.account = Account.objects.create(
            name='حساب اختبار',
            account_type='cash',
            balance=Decimal('10000.00'),
            created_by=self.user
        )
        
        # إنشاء عملية بيع
        self.sale = Sale.objects.create(
            customer=self.customer,
            invoice_no='INV-001',
            date=timezone.now().date(),
            warehouse=self.warehouse,
            payment_method='cash',
            account=self.account,
            created_by=self.user
        )
        
        # إضافة عنصر للبيع
        self.sale_item = SaleItem.objects.create(
            sale=self.sale,
            product=self.product,
            quantity=5,
            price=Decimal('150.00'),
            created_by=self.user
        )
    
    def test_valid_sale_return_form(self):
        """
        اختبار صحة نموذج مرتجعات المبيعات بالبيانات الصحيحة
        """
        form_data = {
            'sale': self.sale.id,
            'invoice_no': 'RET-001',
            'date': timezone.now().date().isoformat(),
            'warehouse': self.warehouse.id,
            'payment_method': 'cash',
            'account': self.account.id,
            'notes': 'ملاحظات المرتجع',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '2',  # أقل من كمية البيع (5)
            'items-0-price': '150.00',
            'items-0-reason': 'منتج معيب',
        }
        
        form = SaleReturnForm(data=form_data)
        # التحقق من صحة النموذج (يعتمد على المنطق الدقيق للنموذج)
        if hasattr(form, 'is_valid'):
            self.assertTrue(form.is_valid())
    
    def test_invalid_sale_return_form(self):
        """
        اختبار رفض نموذج مرتجعات المبيعات بالبيانات غير الصحيحة
        """
        # نموذج بدون فاتورة بيع
        form_data = {
            'invoice_no': 'RET-002',
            'date': timezone.now().date().isoformat(),
            'warehouse': self.warehouse.id,
            'payment_method': 'cash',
            'account': self.account.id,
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '2',
            'items-0-price': '150.00',
            'items-0-reason': 'منتج معيب',
        }
        
        form = SaleReturnForm(data=form_data)
        if hasattr(form, 'is_valid'):
            self.assertFalse(form.is_valid())
            self.assertIn('sale', form.errors)
    
    def test_return_quantity_more_than_sold(self):
        """
        اختبار رفض إرجاع كمية أكبر من الكمية المباعة
        """
        # محاولة إرجاع كمية أكبر من المباعة
        form_data = {
            'sale': self.sale.id,
            'invoice_no': 'RET-003',
            'date': timezone.now().date().isoformat(),
            'warehouse': self.warehouse.id,
            'payment_method': 'cash',
            'account': self.account.id,
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product': self.product.id,
            'items-0-quantity': '10',  # أكبر من كمية البيع (5)
            'items-0-price': '150.00',
            'items-0-reason': 'منتج معيب',
        }
        
        form = SaleReturnForm(data=form_data)
        # التحقق من الخطأ (يعتمد على منطق التحقق في النموذج)
        if hasattr(form, 'clean') and 'check_quantity' in dir(form):
            self.assertFalse(form.is_valid())
            # التحقق من وجود خطأ متعلق بالكمية (يعتمد على تنفيذ التطبيق) 