from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product, Category, Unit, Warehouse, Stock
from sale.models import Customer, Sale, SaleItem, SaleReturn, SaleReturnItem
from purchase.models import Supplier, Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem
from financial.models import Account, Transaction
from decimal import Decimal
from datetime import date, timedelta, datetime
import json

User = get_user_model()

class ReportTestCase(TestCase):
    """
    اختبارات وظائف التقارير في النظام
    """
    def setUp(self):
        """
        إعداد البيانات المطلوبة للاختبارات
        """
        # إنشاء مستخدم للاختبارات
        self.user = User.objects.create_user(
            username='reportuser',
            email='report@example.com',
            password='report123'
        )
        
        # إنشاء عميل HTTP وتسجيل الدخول
        self.client = Client()
        self.client.login(username='reportuser', password='report123')
        
        # تاريخ اليوم للاختبارات
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        self.last_week = self.today - timedelta(days=7)
        self.last_month = self.today - timedelta(days=30)
        
        # إنشاء بيانات الاختبار
        self._create_categories_and_products()
        self._create_customers_and_suppliers()
        self._create_warehouses_and_stock()
        self._create_accounts()
        self._create_sales_and_purchases()
        self._create_returns()
        self._create_transactions()
    
    def _create_categories_and_products(self):
        """
        إنشاء فئات ومنتجات للاختبار
        """
        # إنشاء فئات
        self.category1 = Category.objects.create(
            name='فئة التقارير 1',
            description='وصف فئة التقارير 1',
            created_by=self.user
        )
        
        self.category2 = Category.objects.create(
            name='فئة التقارير 2',
            description='وصف فئة التقارير 2',
            created_by=self.user
        )
        
        # إنشاء وحدة قياس
        self.unit = Unit.objects.create(
            name='وحدة التقارير',
            abbreviation='و.ت',
            created_by=self.user
        )
        
        # إنشاء منتجات
        self.product1 = Product.objects.create(
            name='منتج التقارير 1',
            code='REP001',
            category=self.category1,
            unit=self.unit,
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            created_by=self.user
        )
        
        self.product2 = Product.objects.create(
            name='منتج التقارير 2',
            code='REP002',
            category=self.category1,
            unit=self.unit,
            purchase_price=Decimal('200.00'),
            sale_price=Decimal('300.00'),
            created_by=self.user
        )
        
        self.product3 = Product.objects.create(
            name='منتج التقارير 3',
            code='REP003',
            category=self.category2,
            unit=self.unit,
            purchase_price=Decimal('300.00'),
            sale_price=Decimal('450.00'),
            created_by=self.user
        )
    
    def _create_customers_and_suppliers(self):
        """
        إنشاء عملاء وموردين للاختبار
        """
        # إنشاء عملاء
        self.customer1 = Customer.objects.create(
            name='عميل التقارير 1',
            phone='01234567891',
            address='عنوان عميل التقارير 1',
            created_by=self.user
        )
        
        self.customer2 = Customer.objects.create(
            name='عميل التقارير 2',
            phone='01234567892',
            address='عنوان عميل التقارير 2',
            created_by=self.user
        )
        
        # إنشاء موردين
        self.supplier1 = Supplier.objects.create(
            name='مورد التقارير 1',
            phone='09876543211',
            address='عنوان مورد التقارير 1',
            created_by=self.user
        )
        
        self.supplier2 = Supplier.objects.create(
            name='مورد التقارير 2',
            phone='09876543212',
            address='عنوان مورد التقارير 2',
            created_by=self.user
        )
    
    def _create_warehouses_and_stock(self):
        """
        إنشاء مستودعات ومخزون للاختبار
        """
        # إنشاء مستودعات
        self.warehouse1 = Warehouse.objects.create(
            name='مستودع التقارير 1',
            location='موقع مستودع التقارير 1',
            created_by=self.user
        )
        
        self.warehouse2 = Warehouse.objects.create(
            name='مستودع التقارير 2',
            location='موقع مستودع التقارير 2',
            created_by=self.user
        )
        
        # إنشاء مخزون للمنتجات
        self.stock1 = Stock.objects.create(
            product=self.product1,
            warehouse=self.warehouse1,
            quantity=100,
            created_by=self.user
        )
        
        self.stock2 = Stock.objects.create(
            product=self.product2,
            warehouse=self.warehouse1,
            quantity=50,
            created_by=self.user
        )
        
        self.stock3 = Stock.objects.create(
            product=self.product3,
            warehouse=self.warehouse2,
            quantity=75,
            created_by=self.user
        )
    
    def _create_accounts(self):
        """
        إنشاء حسابات مالية للاختبار
        """
        # إنشاء حسابات
        self.cash_account = Account.objects.create(
            name='صندوق النقدية',
            account_type='cash',
            balance=Decimal('10000.00'),
            created_by=self.user
        )
        
        self.bank_account = Account.objects.create(
            name='حساب البنك',
            account_type='bank',
            balance=Decimal('20000.00'),
            created_by=self.user
        )
    
    def _create_sales_and_purchases(self):
        """
        إنشاء مبيعات ومشتريات للاختبار
        """
        # إنشاء مبيعات
        self.sale1 = Sale.objects.create(
            customer=self.customer1,
            invoice_no='S-REP-001',
            date=self.today,
            payment_method='cash',
            account=self.cash_account,
            notes='ملاحظات البيع 1',
            created_by=self.user
        )
        
        self.sale_item1 = SaleItem.objects.create(
            sale=self.sale1,
            product=self.product1,
            quantity=5,
            price=self.product1.sale_price,
            created_by=self.user
        )
        
        self.sale_item2 = SaleItem.objects.create(
            sale=self.sale1,
            product=self.product2,
            quantity=3,
            price=self.product2.sale_price,
            created_by=self.user
        )
        
        self.sale2 = Sale.objects.create(
            customer=self.customer2,
            invoice_no='S-REP-002',
            date=self.yesterday,
            payment_method='bank',
            account=self.bank_account,
            notes='ملاحظات البيع 2',
            created_by=self.user
        )
        
        self.sale_item3 = SaleItem.objects.create(
            sale=self.sale2,
            product=self.product3,
            quantity=2,
            price=self.product3.sale_price,
            created_by=self.user
        )
        
        self.sale3 = Sale.objects.create(
            customer=self.customer1,
            invoice_no='S-REP-003',
            date=self.last_week,
            payment_method='cash',
            account=self.cash_account,
            notes='ملاحظات البيع 3',
            created_by=self.user
        )
        
        self.sale_item4 = SaleItem.objects.create(
            sale=self.sale3,
            product=self.product2,
            quantity=4,
            price=self.product2.sale_price,
            created_by=self.user
        )
        
        # إنشاء مشتريات
        self.purchase1 = Purchase.objects.create(
            supplier=self.supplier1,
            invoice_no='P-REP-001',
            date=self.today,
            payment_method='cash',
            account=self.cash_account,
            notes='ملاحظات الشراء 1',
            created_by=self.user
        )
        
        self.purchase_item1 = PurchaseItem.objects.create(
            purchase=self.purchase1,
            product=self.product1,
            quantity=10,
            price=self.product1.purchase_price,
            created_by=self.user
        )
        
        self.purchase2 = Purchase.objects.create(
            supplier=self.supplier2,
            invoice_no='P-REP-002',
            date=self.last_week,
            payment_method='bank',
            account=self.bank_account,
            notes='ملاحظات الشراء 2',
            created_by=self.user
        )
        
        self.purchase_item2 = PurchaseItem.objects.create(
            purchase=self.purchase2,
            product=self.product2,
            quantity=8,
            price=self.product2.purchase_price,
            created_by=self.user
        )
        
        self.purchase_item3 = PurchaseItem.objects.create(
            purchase=self.purchase2,
            product=self.product3,
            quantity=5,
            price=self.product3.purchase_price,
            created_by=self.user
        )
    
    def _create_returns(self):
        """
        إنشاء مرتجعات مبيعات ومشتريات للاختبار
        """
        # إنشاء مرتجع مبيعات
        self.sale_return = SaleReturn.objects.create(
            sale=self.sale1,
            return_date=self.today,
            created_by=self.user
        )
        
        self.sale_return_item = SaleReturnItem.objects.create(
            sale_return=self.sale_return,
            product=self.product1,
            quantity=2,
            price=self.product1.sale_price,
            created_by=self.user
        )
        
        # إنشاء مرتجع مشتريات
        self.purchase_return = PurchaseReturn.objects.create(
            purchase=self.purchase1,
            return_date=self.today,
            created_by=self.user
        )
        
        self.purchase_return_item = PurchaseReturnItem.objects.create(
            purchase_return=self.purchase_return,
            product=self.product1,
            quantity=3,
            price=self.product1.purchase_price,
            created_by=self.user
        )
    
    def _create_transactions(self):
        """
        إنشاء معاملات مالية للاختبار
        """
        # إنشاء معاملات مالية
        self.income_transaction = Transaction.objects.create(
            account=self.cash_account,
            transaction_type='income',
            amount=Decimal('500.00'),
            date=self.today,
            description='إيراد إضافي',
            created_by=self.user
        )
        
        self.expense_transaction = Transaction.objects.create(
            account=self.cash_account,
            transaction_type='expense',
            amount=Decimal('300.00'),
            date=self.yesterday,
            description='مصروف إضافي',
            created_by=self.user
        )
        
        self.transfer_transaction = Transaction.objects.create(
            account=self.cash_account,
            transaction_type='transfer',
            amount=Decimal('1000.00'),
            date=self.last_week,
            description='تحويل إلى حساب البنك',
            to_account=self.bank_account,
            created_by=self.user
        )
    
    def test_daily_sales_report(self):
        """
        اختبار تقرير المبيعات اليومي
        """
        # استدعاء صفحة تقرير المبيعات اليومي
        response = self.client.get(
            reverse('sale:sales_report'),
            {'period': 'daily', 'date': self.today.strftime('%Y-%m-%d')}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('sales', response.context)
        self.assertIn('total_amount', response.context)
        
        # التحقق من عدد المبيعات في التقرير (يجب أن يكون مبيعة واحدة لليوم الحالي)
        sales = response.context['sales']
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].id, self.sale1.id)
        
        # التحقق من إجمالي المبيعات
        total_amount = response.context['total_amount']
        expected_total = self.sale_item1.quantity * self.sale_item1.price + \
                         self.sale_item2.quantity * self.sale_item2.price
        self.assertEqual(total_amount, expected_total)
    
    def test_monthly_sales_report(self):
        """
        اختبار تقرير المبيعات الشهري
        """
        # استدعاء صفحة تقرير المبيعات الشهري
        current_month = self.today.month
        current_year = self.today.year
        
        response = self.client.get(
            reverse('sale:sales_report'),
            {'period': 'monthly', 'month': current_month, 'year': current_year}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('sales', response.context)
        self.assertIn('total_amount', response.context)
        
        # التحقق من عدد المبيعات في التقرير (يجب أن تكون جميع المبيعات في الشهر الحالي)
        sales = response.context['sales']
        
        # عدد المبيعات في الشهر الحالي
        current_month_sales_count = Sale.objects.filter(
            date__month=current_month,
            date__year=current_year
        ).count()
        
        self.assertEqual(len(sales), current_month_sales_count)
    
    def test_purchase_report(self):
        """
        اختبار تقرير المشتريات
        """
        # استدعاء صفحة تقرير المشتريات مع فلترة حسب المورد
        response = self.client.get(
            reverse('purchase:purchase_report'),
            {'supplier': self.supplier1.id}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('purchases', response.context)
        
        # التحقق من عدد المشتريات في التقرير (يجب أن تكون مشتريات المورد الأول فقط)
        purchases = response.context['purchases']
        self.assertEqual(len(purchases), 1)
        self.assertEqual(purchases[0].id, self.purchase1.id)
    
    def test_inventory_report(self):
        """
        اختبار تقرير المخزون
        """
        # استدعاء صفحة تقرير المخزون
        response = self.client.get(
            reverse('product:inventory_report')
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('stock_items', response.context)
        
        # التحقق من عدد عناصر المخزون في التقرير
        stock_items = response.context['stock_items']
        self.assertEqual(len(stock_items), 3)  # ثلاثة منتجات
    
    def test_inventory_value_report(self):
        """
        اختبار تقرير قيمة المخزون
        """
        # استدعاء صفحة تقرير قيمة المخزون
        response = self.client.get(
            reverse('product:inventory_value_report')
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('total_value', response.context)
        
        # حساب القيمة الإجمالية المتوقعة للمخزون
        expected_value = (
            self.stock1.quantity * self.product1.purchase_price +
            self.stock2.quantity * self.product2.purchase_price +
            self.stock3.quantity * self.product3.purchase_price
        )
        
        # التحقق من القيمة الإجمالية للمخزون
        total_value = response.context['total_value']
        self.assertEqual(total_value, expected_value)
    
    def test_product_movement_report(self):
        """
        اختبار تقرير حركة المنتج
        """
        # استدعاء صفحة تقرير حركة المنتج
        response = self.client.get(
            reverse('product:product_movement_report'),
            {'product': self.product1.id}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('movements', response.context)
        self.assertIn('product', response.context)
        
        # التحقق من المنتج المحدد
        product = response.context['product']
        self.assertEqual(product.id, self.product1.id)
    
    def test_customer_statement_report(self):
        """
        اختبار تقرير كشف حساب العميل
        """
        # استدعاء صفحة تقرير كشف حساب العميل
        response = self.client.get(
            reverse('sale:customer_statement'),
            {'customer': self.customer1.id}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('sales', response.context)
        self.assertIn('customer', response.context)
        
        # التحقق من العميل المحدد
        customer = response.context['customer']
        self.assertEqual(customer.id, self.customer1.id)
        
        # التحقق من عدد المبيعات للعميل
        sales = response.context['sales']
        customer1_sales_count = Sale.objects.filter(customer=self.customer1).count()
        self.assertEqual(len(sales), customer1_sales_count)
    
    def test_supplier_statement_report(self):
        """
        اختبار تقرير كشف حساب المورد
        """
        # استدعاء صفحة تقرير كشف حساب المورد
        response = self.client.get(
            reverse('purchase:supplier_statement'),
            {'supplier': self.supplier1.id}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('purchases', response.context)
        self.assertIn('supplier', response.context)
        
        # التحقق من المورد المحدد
        supplier = response.context['supplier']
        self.assertEqual(supplier.id, self.supplier1.id)
        
        # التحقق من عدد المشتريات للمورد
        purchases = response.context['purchases']
        supplier1_purchases_count = Purchase.objects.filter(supplier=self.supplier1).count()
        self.assertEqual(len(purchases), supplier1_purchases_count)
    
    def test_profit_loss_report(self):
        """
        اختبار تقرير الأرباح والخسائر
        """
        # تواريخ التقرير
        start_date = self.last_month.strftime('%Y-%m-%d')
        end_date = self.today.strftime('%Y-%m-%d')
        
        # استدعاء صفحة تقرير الأرباح والخسائر
        response = self.client.get(
            reverse('financial:profit_loss_report'),
            {'start_date': start_date, 'end_date': end_date}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('total_income', response.context)
        self.assertIn('total_expense', response.context)
        self.assertIn('net_profit', response.context)
        
        # التحقق من صحة الأرقام
        total_income = response.context['total_income']
        total_expense = response.context['total_expense']
        net_profit = response.context['net_profit']
        
        self.assertEqual(net_profit, total_income - total_expense)
    
    def test_account_statement_report(self):
        """
        اختبار تقرير كشف الحساب المالي
        """
        # استدعاء صفحة تقرير كشف الحساب المالي
        response = self.client.get(
            reverse('financial:account_statement'),
            {'account': self.cash_account.id}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('transactions', response.context)
        self.assertIn('account', response.context)
        
        # التحقق من الحساب المحدد
        account = response.context['account']
        self.assertEqual(account.id, self.cash_account.id)
        
        # التحقق من عدد المعاملات للحساب
        transactions = response.context['transactions']
        cash_account_transactions_count = Transaction.objects.filter(
            account=self.cash_account
        ).count()
        self.assertEqual(len(transactions), cash_account_transactions_count)
    
    def test_top_selling_products_report(self):
        """
        اختبار تقرير المنتجات الأكثر مبيعًا
        """
        # استدعاء صفحة تقرير المنتجات الأكثر مبيعًا
        response = self.client.get(
            reverse('product:top_selling_products')
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('top_products', response.context)
        
        # التحقق من ترتيب المنتجات الأكثر مبيعًا
        top_products = response.context['top_products']
        
        # يجب أن تكون هناك منتجات في القائمة
        self.assertGreater(len(top_products), 0)
    
    def test_sales_by_category_report(self):
        """
        اختبار تقرير المبيعات حسب الفئة
        """
        # استدعاء صفحة تقرير المبيعات حسب الفئة
        response = self.client.get(
            reverse('product:sales_by_category')
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('categories_data', response.context)
        
        # التحقق من البيانات المعروضة
        categories_data = response.context['categories_data']
        
        # يجب أن تكون هناك فئات في البيانات
        self.assertGreater(len(categories_data), 0)
    
    def test_report_api_endpoint(self):
        """
        اختبار نقطة نهاية API للتقارير (للرسوم البيانية)
        """
        # استدعاء نقطة نهاية API للمبيعات الشهرية
        response = self.client.get(
            reverse('api:monthly_sales_data')
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # تحليل البيانات المستجابة
        data = json.loads(response.content)
        
        # التحقق من وجود البيانات المطلوبة للرسم البياني
        self.assertIn('labels', data)
        self.assertIn('datasets', data)
        
        # التحقق من وجود بيانات في المجموعات
        datasets = data['datasets']
        self.assertGreater(len(datasets), 0)
    
    def test_dashboard_report_widgets(self):
        """
        اختبار أدوات التقارير في لوحة التحكم
        """
        # استدعاء صفحة لوحة التحكم
        response = self.client.get(
            reverse('dashboard:index')
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود بيانات التقارير في السياق
        self.assertIn('total_sales', response.context)
        self.assertIn('total_purchases', response.context)
        self.assertIn('total_customers', response.context)
        self.assertIn('total_suppliers', response.context)
        self.assertIn('recent_sales', response.context)
        self.assertIn('recent_purchases', response.context)
        
        # التحقق من قيم التقارير
        total_sales = response.context['total_sales']
        self.assertEqual(total_sales, Sale.objects.count())
        
        total_customers = response.context['total_customers']
        self.assertEqual(total_customers, Customer.objects.count())
    
    def test_custom_date_range_report(self):
        """
        اختبار تقرير بنطاق تاريخ مخصص
        """
        # تواريخ مخصصة للتقرير
        start_date = self.last_week.strftime('%Y-%m-%d')
        end_date = self.today.strftime('%Y-%m-%d')
        
        # استدعاء صفحة تقرير المبيعات بفترة مخصصة
        response = self.client.get(
            reverse('sale:sales_report'),
            {'period': 'custom', 'start_date': start_date, 'end_date': end_date}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من وجود معلومات التقرير في السياق
        self.assertIn('sales', response.context)
        
        # التحقق من المبيعات في النطاق المحدد
        sales = response.context['sales']
        
        # عدد المبيعات في النطاق المحدد
        expected_sales_count = Sale.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).count()
        
        self.assertEqual(len(sales), expected_sales_count)
    
    def test_report_export_functionality(self):
        """
        اختبار وظيفة تصدير التقارير
        """
        # استدعاء صفحة تصدير تقرير المبيعات
        response = self.client.get(
            reverse('sale:export_sales_report'),
            {'format': 'csv', 'period': 'all'}
        )
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # التحقق من نوع المحتوى
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # التحقق من وجود ترويسة التنزيل
        self.assertIn('attachment; filename=', response['Content-Disposition']) 