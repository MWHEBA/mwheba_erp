from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from product.models import Product, Category, Brand, Unit, Warehouse, Stock, StockMovement
from sale.models import Customer, Sale, SaleItem, SaleReturn, SaleReturnItem
from purchase.models import Supplier, Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem
from financial.models import Account, Transaction
from decimal import Decimal

User = get_user_model()

class IntegrationTestCase(TestCase):
    """
    اختبارات التكامل بين وحدات النظام المختلفة
    """
    def setUp(self):
        """
        إعداد البيانات المطلوبة للاختبارات
        """
        # إنشاء مستخدم
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # إنشاء عميل HTTP وتسجيل الدخول
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # إنشاء بيانات المنتجات
        self.category = Category.objects.create(
            name='فئة اختبار',
            description='وصف فئة الاختبار',
            created_by=self.user
        )
        
        self.brand = Brand.objects.create(
            name='علامة تجارية',
            description='وصف العلامة التجارية',
            created_by=self.user
        )
        
        self.unit = Unit.objects.create(
            name='قطعة',
            abbreviation='ق',
            created_by=self.user
        )
        
        self.warehouse = Warehouse.objects.create(
            name='مستودع رئيسي',
            code='WH001',
            location='موقع المستودع',
            created_by=self.user
        )
        
        self.product1 = Product.objects.create(
            name='منتج اختبار 1',
            code='P001',
            description='وصف المنتج الأول',
            category=self.category,
            brand=self.brand,
            unit=self.unit,
            purchase_price=Decimal('100.00'),
            sale_price=Decimal('150.00'),
            created_by=self.user
        )
        
        self.product2 = Product.objects.create(
            name='منتج اختبار 2',
            code='P002',
            description='وصف المنتج الثاني',
            category=self.category,
            brand=self.brand,
            unit=self.unit,
            purchase_price=Decimal('200.00'),
            sale_price=Decimal('300.00'),
            created_by=self.user
        )
        
        # إنشاء سجلات المخزون
        self.stock1 = Stock.objects.create(
            product=self.product1,
            warehouse=self.warehouse,
            quantity=50,
            created_by=self.user
        )
        
        self.stock2 = Stock.objects.create(
            product=self.product2,
            warehouse=self.warehouse,
            quantity=30,
            created_by=self.user
        )
        
        # إنشاء بيانات العملاء والموردين
        self.customer = Customer.objects.create(
            name='عميل للاختبار',
            phone='01234567890',
            address='عنوان العميل',
            created_by=self.user
        )
        
        self.supplier = Supplier.objects.create(
            name='مورد للاختبار',
            phone='09876543210',
            address='عنوان المورد',
            created_by=self.user
        )
        
        # إنشاء الحسابات المالية
        self.cash_account = Account.objects.create(
            name='حساب الصندوق',
            account_type='cash',
            balance=Decimal('5000.00'),
            created_by=self.user
        )
        
        self.bank_account = Account.objects.create(
            name='حساب البنك',
            account_type='bank',
            balance=Decimal('10000.00'),
            created_by=self.user
        )
    
    def test_purchase_to_stock_integration(self):
        """
        اختبار تكامل عملية الشراء مع المخزون
        عند إنشاء عملية شراء، يجب زيادة كمية المخزون تلقائيًا
        """
        # حفظ كمية المخزون الأصلية
        initial_quantity_p1 = self.stock1.quantity
        
        # إنشاء عملية شراء
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_no='PO-001',
            date='2023-05-10',
            payment_method='cash',
            account=self.cash_account,
            notes='ملاحظات عملية الشراء',
            created_by=self.user
        )
        
        # إضافة عناصر الشراء
        purchase_item = PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product1,
            quantity=20,
            price=Decimal('90.00'),  # سعر الشراء
            created_by=self.user
        )
        
        # إعادة تحميل سجل المخزون
        self.stock1.refresh_from_db()
        
        # التحقق من زيادة المخزون
        expected_new_quantity = initial_quantity_p1 + 20
        self.assertEqual(self.stock1.quantity, expected_new_quantity)
        
        # التحقق من وجود حركة مخزون
        stock_movement = StockMovement.objects.filter(
            product=self.product1,
            warehouse=self.warehouse,
            movement_type='in',
            quantity=20
        ).first()
        
        self.assertIsNotNone(stock_movement)
        self.assertEqual(stock_movement.reference_id, str(purchase.id))
        self.assertEqual(stock_movement.reference_type, 'purchase')
    
    def test_sale_to_stock_integration(self):
        """
        اختبار تكامل عملية البيع مع المخزون
        عند إنشاء عملية بيع، يجب خفض كمية المخزون تلقائيًا
        """
        # حفظ كمية المخزون الأصلية
        initial_quantity_p1 = self.stock1.quantity
        
        # إنشاء عملية بيع
        sale = Sale.objects.create(
            customer=self.customer,
            invoice_no='INV-001',
            date='2023-05-15',
            payment_method='cash',
            account=self.cash_account,
            notes='ملاحظات عملية البيع',
            created_by=self.user
        )
        
        # إضافة عناصر البيع
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product1,
            quantity=10,
            price=Decimal('150.00'),  # سعر البيع
            created_by=self.user
        )
        
        # إعادة تحميل سجل المخزون
        self.stock1.refresh_from_db()
        
        # التحقق من نقص المخزون
        expected_new_quantity = initial_quantity_p1 - 10
        self.assertEqual(self.stock1.quantity, expected_new_quantity)
        
        # التحقق من وجود حركة مخزون
        stock_movement = StockMovement.objects.filter(
            product=self.product1,
            warehouse=self.warehouse,
            movement_type='out',
            quantity=10
        ).first()
        
        self.assertIsNotNone(stock_movement)
        self.assertEqual(stock_movement.reference_id, str(sale.id))
        self.assertEqual(stock_movement.reference_type, 'sale')
    
    def test_purchase_to_financial_integration(self):
        """
        اختبار تكامل عملية الشراء مع النظام المالي
        عند إنشاء عملية شراء، يجب إنشاء معاملة مالية وخصم المبلغ من الحساب
        """
        # حفظ رصيد الحساب الأصلي
        initial_balance = self.cash_account.balance
        
        # إنشاء عملية شراء
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_no='PO-002',
            date='2023-05-11',
            payment_method='cash',
            account=self.cash_account,
            notes='ملاحظات عملية الشراء',
            created_by=self.user
        )
        
        # إضافة عناصر الشراء
        purchase_item = PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product1,
            quantity=5,
            price=Decimal('100.00'),
            created_by=self.user
        )
        
        # إعادة تحميل الحساب
        self.cash_account.refresh_from_db()
        
        # التحقق من خصم المبلغ من الحساب
        purchase_total = Decimal('500.00')  # 5 قطع × 100
        expected_new_balance = initial_balance - purchase_total
        self.assertEqual(self.cash_account.balance, expected_new_balance)
        
        # التحقق من وجود معاملة مالية
        transaction = Transaction.objects.filter(
            transaction_type='expense',
            amount=purchase_total,
            reference_id=str(purchase.id),
            reference_type='purchase'
        ).first()
        
        self.assertIsNotNone(transaction)
    
    def test_sale_to_financial_integration(self):
        """
        اختبار تكامل عملية البيع مع النظام المالي
        عند إنشاء عملية بيع، يجب إنشاء معاملة مالية وإضافة المبلغ للحساب
        """
        # حفظ رصيد الحساب الأصلي
        initial_balance = self.cash_account.balance
        
        # إنشاء عملية بيع
        sale = Sale.objects.create(
            customer=self.customer,
            invoice_no='INV-002',
            date='2023-05-16',
            payment_method='cash',
            account=self.cash_account,
            notes='ملاحظات عملية البيع',
            created_by=self.user
        )
        
        # إضافة عناصر البيع
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product2,
            quantity=3,
            price=Decimal('300.00'),
            created_by=self.user
        )
        
        # إعادة تحميل الحساب
        self.cash_account.refresh_from_db()
        
        # التحقق من إضافة المبلغ للحساب
        sale_total = Decimal('900.00')  # 3 قطع × 300
        expected_new_balance = initial_balance + sale_total
        self.assertEqual(self.cash_account.balance, expected_new_balance)
        
        # التحقق من وجود معاملة مالية
        transaction = Transaction.objects.filter(
            transaction_type='income',
            amount=sale_total,
            reference_id=str(sale.id),
            reference_type='sale'
        ).first()
        
        self.assertIsNotNone(transaction)
    
    def test_sale_return_integration(self):
        """
        اختبار تكامل مرتجع البيع مع المخزون والنظام المالي
        """
        # إنشاء عملية بيع أولاً
        sale = Sale.objects.create(
            customer=self.customer,
            invoice_no='INV-003',
            date='2023-05-18',
            payment_method='cash',
            account=self.cash_account,
            notes='بيع للاختبار',
            created_by=self.user
        )
        
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product1,
            quantity=8,
            price=Decimal('150.00'),
            created_by=self.user
        )
        
        # حفظ الكمية بعد عملية البيع
        self.stock1.refresh_from_db()
        quantity_after_sale = self.stock1.quantity
        
        # حفظ الرصيد بعد عملية البيع
        self.cash_account.refresh_from_db()
        balance_after_sale = self.cash_account.balance
        
        # إنشاء مرتجع بيع
        sale_return = SaleReturn.objects.create(
            sale=sale,
            date='2023-05-19',
            account=self.cash_account,
            notes='مرتجع بيع للاختبار',
            created_by=self.user
        )
        
        sale_return_item = SaleReturnItem.objects.create(
            sale_return=sale_return,
            product=self.product1,
            quantity=3,  # إرجاع 3 من أصل 8
            price=Decimal('150.00'),
            created_by=self.user
        )
        
        # إعادة تحميل المخزون والحساب
        self.stock1.refresh_from_db()
        self.cash_account.refresh_from_db()
        
        # التحقق من زيادة المخزون
        expected_quantity = quantity_after_sale + 3
        self.assertEqual(self.stock1.quantity, expected_quantity)
        
        # التحقق من نقص الرصيد
        return_total = Decimal('450.00')  # 3 قطع × 150
        expected_balance = balance_after_sale - return_total
        self.assertEqual(self.cash_account.balance, expected_balance)
        
        # التحقق من وجود حركة مخزون
        stock_movement = StockMovement.objects.filter(
            product=self.product1,
            warehouse=self.warehouse,
            movement_type='in',
            reference_type='sale_return',
            quantity=3
        ).first()
        
        self.assertIsNotNone(stock_movement)
        
        # التحقق من وجود معاملة مالية
        transaction = Transaction.objects.filter(
            transaction_type='expense',
            amount=return_total,
            reference_id=str(sale_return.id),
            reference_type='sale_return'
        ).first()
        
        self.assertIsNotNone(transaction)
    
    def test_purchase_return_integration(self):
        """
        اختبار تكامل مرتجع الشراء مع المخزون والنظام المالي
        """
        # إنشاء عملية شراء أولاً
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_no='PO-003',
            date='2023-05-20',
            payment_method='cash',
            account=self.cash_account,
            notes='شراء للاختبار',
            created_by=self.user
        )
        
        purchase_item = PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product2,
            quantity=15,
            price=Decimal('200.00'),
            created_by=self.user
        )
        
        # حفظ الكمية بعد عملية الشراء
        self.stock2.refresh_from_db()
        quantity_after_purchase = self.stock2.quantity
        
        # حفظ الرصيد بعد عملية الشراء
        self.cash_account.refresh_from_db()
        balance_after_purchase = self.cash_account.balance
        
        # إنشاء مرتجع شراء
        purchase_return = PurchaseReturn.objects.create(
            purchase=purchase,
            date='2023-05-21',
            account=self.cash_account,
            notes='مرتجع شراء للاختبار',
            created_by=self.user
        )
        
        purchase_return_item = PurchaseReturnItem.objects.create(
            purchase_return=purchase_return,
            product=self.product2,
            quantity=5,  # إرجاع 5 من أصل 15
            price=Decimal('200.00'),
            created_by=self.user
        )
        
        # إعادة تحميل المخزون والحساب
        self.stock2.refresh_from_db()
        self.cash_account.refresh_from_db()
        
        # التحقق من نقص المخزون
        expected_quantity = quantity_after_purchase - 5
        self.assertEqual(self.stock2.quantity, expected_quantity)
        
        # التحقق من زيادة الرصيد
        return_total = Decimal('1000.00')  # 5 قطع × 200
        expected_balance = balance_after_purchase + return_total
        self.assertEqual(self.cash_account.balance, expected_balance)
        
        # التحقق من وجود حركة مخزون
        stock_movement = StockMovement.objects.filter(
            product=self.product2,
            warehouse=self.warehouse,
            movement_type='out',
            reference_type='purchase_return',
            quantity=5
        ).first()
        
        self.assertIsNotNone(stock_movement)
        
        # التحقق من وجود معاملة مالية
        transaction = Transaction.objects.filter(
            transaction_type='income',
            amount=return_total,
            reference_id=str(purchase_return.id),
            reference_type='purchase_return'
        ).first()
        
        self.assertIsNotNone(transaction)
    
    def test_complete_business_cycle(self):
        """
        اختبار دورة أعمال كاملة تشمل الشراء، البيع، المرتجعات، وتأثيرها على المخزون والمالية
        """
        # حفظ الحالة الأولية
        initial_stock_p1 = self.stock1.quantity
        initial_stock_p2 = self.stock2.quantity
        initial_balance = self.cash_account.balance
        
        # 1. شراء منتجات
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_no='PO-CYCLE',
            date='2023-06-01',
            payment_method='cash',
            account=self.cash_account,
            notes='شراء دورة الأعمال',
            created_by=self.user
        )
        
        purchase_item1 = PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product1,
            quantity=50,
            price=Decimal('90.00'),
            created_by=self.user
        )
        
        purchase_item2 = PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product2,
            quantity=30,
            price=Decimal('180.00'),
            created_by=self.user
        )
        
        purchase_total = Decimal('50 * 90 + 30 * 180')
        
        # 2. بيع بعض المنتجات
        sale = Sale.objects.create(
            customer=self.customer,
            invoice_no='INV-CYCLE',
            date='2023-06-05',
            payment_method='cash',
            account=self.cash_account,
            notes='بيع دورة الأعمال',
            created_by=self.user
        )
        
        sale_item1 = SaleItem.objects.create(
            sale=sale,
            product=self.product1,
            quantity=20,
            price=Decimal('150.00'),
            created_by=self.user
        )
        
        sale_item2 = SaleItem.objects.create(
            sale=sale,
            product=self.product2,
            quantity=10,
            price=Decimal('300.00'),
            created_by=self.user
        )
        
        sale_total = Decimal('20 * 150 + 10 * 300')
        
        # 3. مرتجع بعض المبيعات
        sale_return = SaleReturn.objects.create(
            sale=sale,
            date='2023-06-06',
            account=self.cash_account,
            notes='مرتجع بيع دورة الأعمال',
            created_by=self.user
        )
        
        sale_return_item = SaleReturnItem.objects.create(
            sale_return=sale_return,
            product=self.product1,
            quantity=5,
            price=Decimal('150.00'),
            created_by=self.user
        )
        
        sale_return_total = Decimal('5 * 150')
        
        # 4. مرتجع بعض المشتريات
        purchase_return = PurchaseReturn.objects.create(
            purchase=purchase,
            date='2023-06-07',
            account=self.cash_account,
            notes='مرتجع شراء دورة الأعمال',
            created_by=self.user
        )
        
        purchase_return_item = PurchaseReturnItem.objects.create(
            purchase_return=purchase_return,
            product=self.product2,
            quantity=8,
            price=Decimal('180.00'),
            created_by=self.user
        )
        
        purchase_return_total = Decimal('8 * 180')
        
        # إعادة تحميل بيانات المخزون والحساب
        self.stock1.refresh_from_db()
        self.stock2.refresh_from_db()
        self.cash_account.refresh_from_db()
        
        # التحقق من صحة كميات المخزون النهائية
        expected_stock_p1 = initial_stock_p1 + 50 - 20 + 5
        expected_stock_p2 = initial_stock_p2 + 30 - 10 - 8
        
        self.assertEqual(self.stock1.quantity, expected_stock_p1)
        self.assertEqual(self.stock2.quantity, expected_stock_p2)
        
        # التحقق من صحة الرصيد النهائي
        expected_balance = initial_balance - purchase_total + sale_total - sale_return_total + purchase_return_total
        self.assertEqual(self.cash_account.balance, expected_balance)
        
        # التحقق من عدد حركات المخزون
        stock_movements_count = StockMovement.objects.filter(
            product__in=[self.product1, self.product2],
            warehouse=self.warehouse
        ).count()
        
        expected_movements = 6  # 2 حركات شراء + 2 حركات بيع + 1 حركة مرتجع بيع + 1 حركة مرتجع شراء
        self.assertEqual(stock_movements_count, expected_movements)
        
        # التحقق من عدد المعاملات المالية
        transactions_count = Transaction.objects.filter(
            reference_type__in=['purchase', 'sale', 'purchase_return', 'sale_return']
        ).count()
        
        expected_transactions = 4  # 1 معاملة شراء + 1 معاملة بيع + 1 معاملة مرتجع بيع + 1 معاملة مرتجع شراء
        self.assertEqual(transactions_count, expected_transactions) 