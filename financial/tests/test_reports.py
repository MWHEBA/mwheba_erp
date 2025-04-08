from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from financial.models import Account, Transaction
from sale.models import Customer, Sale, SaleItem
from purchase.models import Supplier, Purchase, PurchaseItem
from product.models import Product, Category, Unit
from decimal import Decimal
import json
from datetime import date, timedelta

User = get_user_model()

class ReportTestCase(TestCase):
    """
    اختبارات التقارير المالية والإحصائيات في النظام
    """
    def setUp(self):
        """
        إعداد البيانات المطلوبة للاختبارات
        """
        # إنشاء مستخدم للاختبارات
        self.user = User.objects.create_user(
            username='reportuser',
            email='report@example.com',
            password='reportpass123'
        )
        
        # إنشاء عميل HTTP وتسجيل الدخول
        self.client = Client()
        self.client.login(username='reportuser', password='reportpass123')
        
        # إنشاء بيانات المنتجات
        self.category = Category.objects.create(
            name='فئة التقارير',
            description='فئة لاختبارات التقارير',
            created_by=self.user
        )
        
        self.unit = Unit.objects.create(
            name='قطعة',
            abbreviation='ق',
            created_by=self.user
        )
        
        self.product1 = Product.objects.create(
            name='منتج تقرير 1',
            code='REP001',
            category=self.category,
            unit=self.unit,
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            created_by=self.user
        )
        
        self.product2 = Product.objects.create(
            name='منتج تقرير 2',
            code='REP002',
            category=self.category,
            unit=self.unit,
            purchase_price=Decimal('200.00'),
            sale_price=Decimal('300.00'),
            created_by=self.user
        )
        
        # إنشاء حساب مالي
        self.account = Account.objects.create(
            name='حساب التقارير',
            account_type='cash',
            balance=Decimal('10000.00'),
            created_by=self.user
        )
        
        # إنشاء عميل ومورد
        self.customer = Customer.objects.create(
            name='عميل التقارير',
            phone='01234567890',
            address='عنوان العميل',
            created_by=self.user
        )
        
        self.supplier = Supplier.objects.create(
            name='مورد التقارير',
            phone='09876543210',
            address='عنوان المورد',
            created_by=self.user
        )
        
        # تواريخ للاختبارات
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        self.last_week = self.today - timedelta(days=7)
        self.last_month = self.today - timedelta(days=30)
        
        # إنشاء معاملات مالية للتقارير
        # 1. معاملات الإيرادات
        Transaction.objects.create(
            account=self.account,
            transaction_type='income',
            amount=Decimal('1000.00'),
            date=self.today,
            description='إيراد اليوم',
            created_by=self.user
        )
        
        Transaction.objects.create(
            account=self.account,
            transaction_type='income',
            amount=Decimal('800.00'),
            date=self.yesterday,
            description='إيراد الأمس',
            created_by=self.user
        )
        
        Transaction.objects.create(
            account=self.account,
            transaction_type='income',
            amount=Decimal('3000.00'),
            date=self.last_week,
            description='إيراد الأسبوع الماضي',
            created_by=self.user
        )
        
        # 2. معاملات المصروفات
        Transaction.objects.create(
            account=self.account,
            transaction_type='expense',
            amount=Decimal('500.00'),
            date=self.today,
            description='مصروف اليوم',
            created_by=self.user
        )
        
        Transaction.objects.create(
            account=self.account,
            transaction_type='expense',
            amount=Decimal('300.00'),
            date=self.yesterday,
            description='مصروف الأمس',
            created_by=self.user
        )
        
        Transaction.objects.create(
            account=self.account,
            transaction_type='expense',
            amount=Decimal('1200.00'),
            date=self.last_week,
            description='مصروف الأسبوع الماضي',
            created_by=self.user
        )
        
        # 3. إنشاء عمليات بيع
        sale1 = Sale.objects.create(
            customer=self.customer,
            invoice_no='INV-REP-1',
            date=self.today,
            payment_method='cash',
            account=self.account,
            notes='بيع للتقارير اليوم',
            created_by=self.user
        )
        
        SaleItem.objects.create(
            sale=sale1,
            product=self.product1,
            quantity=5,
            price=Decimal('150.00'),
            created_by=self.user
        )
        
        sale2 = Sale.objects.create(
            customer=self.customer,
            invoice_no='INV-REP-2',
            date=self.yesterday,
            payment_method='cash',
            account=self.account,
            notes='بيع للتقارير الأمس',
            created_by=self.user
        )
        
        SaleItem.objects.create(
            sale=sale2,
            product=self.product2,
            quantity=2,
            price=Decimal('300.00'),
            created_by=self.user
        )
        
        # 4. إنشاء عمليات شراء
        purchase1 = Purchase.objects.create(
            supplier=self.supplier,
            invoice_no='PO-REP-1',
            date=self.today,
            payment_method='cash',
            account=self.account,
            notes='شراء للتقارير اليوم',
            created_by=self.user
        )
        
        PurchaseItem.objects.create(
            purchase=purchase1,
            product=self.product1,
            quantity=10,
            price=Decimal('100.00'),
            created_by=self.user
        )
        
        purchase2 = Purchase.objects.create(
            supplier=self.supplier,
            invoice_no='PO-REP-2',
            date=self.last_week,
            payment_method='cash',
            account=self.account,
            notes='شراء للتقارير الأسبوع الماضي',
            created_by=self.user
        )
        
        PurchaseItem.objects.create(
            purchase=purchase2,
            product=self.product2,
            quantity=5,
            price=Decimal('200.00'),
            created_by=self.user
        )
    
    def test_daily_income_report(self):
        """
        اختبار تقرير الإيرادات اليومي
        """
        # استدعاء صفحة تقرير الإيرادات اليومي
        response = self.client.get(
            reverse('financial:income_report'),
            {'date': self.today.strftime('%Y-%m-%d')}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير (يعتمد على الاستجابة الفعلية)
        # نفترض أن البيانات موجودة في سياق القالب
        report_data = response.context.get('report_data', {})
        
        # التحقق من إجمالي الإيرادات اليومي
        # يجب أن يكون 1000 (معاملة الإيراد) + 5*150 (مبيعات المنتج 1)
        expected_income = Decimal('1000.00') + Decimal('5') * Decimal('150.00')
        self.assertEqual(report_data.get('total_income', 0), expected_income)
    
    def test_expense_report(self):
        """
        اختبار تقرير المصروفات
        """
        # استدعاء صفحة تقرير المصروفات
        response = self.client.get(
            reverse('financial:expense_report'),
            {'date': self.today.strftime('%Y-%m-%d')}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        
        # التحقق من إجمالي المصروفات
        # يجب أن يكون 500 (معاملة المصروفات) + 10*100 (مشتريات المنتج 1)
        expected_expense = Decimal('500.00') + Decimal('10') * Decimal('100.00')
        self.assertEqual(report_data.get('total_expenses', 0), expected_expense)
    
    def test_profit_loss_report(self):
        """
        اختبار تقرير الأرباح والخسائر
        """
        # استدعاء صفحة تقرير الأرباح والخسائر للفترة من الأسبوع الماضي حتى اليوم
        response = self.client.get(
            reverse('financial:profit_loss_report'),
            {
                'start_date': self.last_week.strftime('%Y-%m-%d'),
                'end_date': self.today.strftime('%Y-%m-%d')
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        
        # إجمالي الإيرادات: 1000 + 800 + 3000 (معاملات الإيرادات) + 5*150 + 2*300 (المبيعات)
        total_income = (
            Decimal('1000.00') + Decimal('800.00') + Decimal('3000.00') +
            Decimal('5') * Decimal('150.00') + Decimal('2') * Decimal('300.00')
        )
        
        # إجمالي المصروفات: 500 + 300 + 1200 (معاملات المصروفات) + 10*100 + 5*200 (المشتريات)
        total_expenses = (
            Decimal('500.00') + Decimal('300.00') + Decimal('1200.00') +
            Decimal('10') * Decimal('100.00') + Decimal('5') * Decimal('200.00')
        )
        
        # صافي الربح/الخسارة
        net_profit = total_income - total_expenses
        
        # التحقق من النتائج
        self.assertEqual(report_data.get('total_income', 0), total_income)
        self.assertEqual(report_data.get('total_expenses', 0), total_expenses)
        self.assertEqual(report_data.get('net_profit', 0), net_profit)
    
    def test_sales_report(self):
        """
        اختبار تقرير المبيعات
        """
        # استدعاء صفحة تقرير المبيعات
        response = self.client.get(
            reverse('sale:sales_report'),
            {'period': 'monthly', 'month': self.today.month, 'year': self.today.year}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        
        # إجمالي المبيعات لهذا الشهر
        # يجب أن يكون 5*150 + 2*300
        expected_sales = Decimal('5') * Decimal('150.00') + Decimal('2') * Decimal('300.00')
        self.assertEqual(report_data.get('total_sales', 0), expected_sales)
        
        # عدد المبيعات
        self.assertEqual(report_data.get('sales_count', 0), 2)
    
    def test_purchase_report(self):
        """
        اختبار تقرير المشتريات
        """
        # استدعاء صفحة تقرير المشتريات
        response = self.client.get(
            reverse('purchase:purchase_report'),
            {'period': 'monthly', 'month': self.today.month, 'year': self.today.year}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        
        # إجمالي المشتريات لهذا الشهر
        # يجب أن يكون 10*100 + 5*200
        expected_purchases = Decimal('10') * Decimal('100.00') + Decimal('5') * Decimal('200.00')
        self.assertEqual(report_data.get('total_purchases', 0), expected_purchases)
        
        # عدد المشتريات
        self.assertEqual(report_data.get('purchase_count', 0), 2)
    
    def test_customer_report(self):
        """
        اختبار تقرير العملاء
        """
        # استدعاء صفحة تقرير العملاء
        response = self.client.get(
            reverse('sale:customer_report'),
            {'customer_id': self.customer.id}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        
        # إجمالي مبيعات العميل
        # يجب أن يكون 5*150 + 2*300
        expected_sales = Decimal('5') * Decimal('150.00') + Decimal('2') * Decimal('300.00')
        self.assertEqual(report_data.get('total_sales', 0), expected_sales)
        
        # عدد المبيعات للعميل
        self.assertEqual(report_data.get('sales_count', 0), 2)
    
    def test_supplier_report(self):
        """
        اختبار تقرير الموردين
        """
        # استدعاء صفحة تقرير الموردين
        response = self.client.get(
            reverse('purchase:supplier_report'),
            {'supplier_id': self.supplier.id}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        
        # إجمالي مشتريات المورد
        # يجب أن يكون 10*100 + 5*200
        expected_purchases = Decimal('10') * Decimal('100.00') + Decimal('5') * Decimal('200.00')
        self.assertEqual(report_data.get('total_purchases', 0), expected_purchases)
        
        # عدد المشتريات من المورد
        self.assertEqual(report_data.get('purchase_count', 0), 2)
    
    def test_product_performance_report(self):
        """
        اختبار تقرير أداء المنتجات
        """
        # استدعاء صفحة تقرير أداء المنتجات
        response = self.client.get(
            reverse('product:product_performance_report')
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        products_data = report_data.get('products', [])
        
        # البحث عن منتج 1 في البيانات
        product1_data = next((p for p in products_data if p['id'] == self.product1.id), None)
        
        # التحقق من بيانات المنتج
        self.assertIsNotNone(product1_data)
        self.assertEqual(product1_data.get('total_sold', 0), 5)  # تم بيع 5 وحدات
        self.assertEqual(product1_data.get('total_purchased', 0), 10)  # تم شراء 10 وحدات
        
        # يجب أن يكون الربح الإجمالي للمنتج 1 هو (سعر البيع - سعر الشراء) × الكمية المباعة
        expected_profit = (Decimal('150.00') - Decimal('100.00')) * Decimal('5')
        self.assertEqual(product1_data.get('total_profit', 0), expected_profit)
    
    def test_date_range_report(self):
        """
        اختبار تقرير بنطاق تاريخي
        """
        # استدعاء صفحة تقرير بنطاق تاريخي
        response = self.client.get(
            reverse('financial:date_range_report'),
            {
                'start_date': self.last_month.strftime('%Y-%m-%d'),
                'end_date': self.today.strftime('%Y-%m-%d'),
                'report_type': 'sales'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير
        report_data = response.context.get('report_data', {})
        
        # التأكد من أن جميع المبيعات في النطاق الزمني مضمنة
        # يجب أن يكون 2 (عدد عمليات البيع)
        self.assertEqual(report_data.get('sales_count', 0), 2)
    
    def test_dashboard_statistics(self):
        """
        اختبار إحصائيات لوحة المعلومات
        """
        # استدعاء صفحة لوحة المعلومات
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات الإحصائيات
        stats = response.context.get('statistics', {})
        
        # التحقق من الإحصائيات
        self.assertIn('total_sales', stats)
        self.assertIn('total_purchases', stats)
        self.assertIn('total_income', stats)
        self.assertIn('total_expenses', stats)
        self.assertIn('recent_sales', stats)
        self.assertIn('popular_products', stats)
    
    def test_export_report(self):
        """
        اختبار تصدير التقارير
        """
        # استدعاء صفحة تصدير تقرير المبيعات
        response = self.client.get(
            reverse('sale:export_sales_report'),
            {'format': 'csv', 'period': 'monthly', 'month': self.today.month, 'year': self.today.year}
        )
        
        # يجب أن يكون الرد 200 OK مع نوع محتوى مناسب
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename=', response['Content-Disposition'])
    
    def test_custom_report(self):
        """
        اختبار التقارير المخصصة
        """
        # استدعاء صفحة التقارير المخصصة
        response = self.client.get(
            reverse('financial:custom_report'),
            {
                'report_type': 'product_category',
                'start_date': self.last_month.strftime('%Y-%m-%d'),
                'end_date': self.today.strftime('%Y-%m-%d')
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # تحليل بيانات التقرير المخصص
        report_data = response.context.get('report_data', {})
        
        # يجب أن يحتوي على بيانات فئات المنتجات
        self.assertIn('categories', report_data)
        
        # يجب أن تحتوي البيانات على فئة واحدة على الأقل
        categories = report_data.get('categories', [])
        self.assertGreaterEqual(len(categories), 1)
        
        # يجب أن تحتوي الفئة الأولى (فئة التقارير) على بيانات
        category_data = next((c for c in categories if c['id'] == self.category.id), None)
        self.assertIsNotNone(category_data)
        self.assertIn('total_sales', category_data)
        self.assertIn('total_profit', category_data) 