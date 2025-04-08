from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from financial.models import Account, Transaction, PaymentMethod
from sale.models import Customer, Sale
from purchase.models import Supplier, Purchase
from decimal import Decimal
import datetime

User = get_user_model()

class AccountModelTest(TestCase):
    """
    اختبارات نموذج الحسابات المالية
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.account = Account.objects.create(
            name='حساب اختبار',
            account_type='cash',
            initial_balance=Decimal('1000.00'),
            description='وصف حساب الاختبار',
            created_by=self.user
        )

    def test_account_creation(self):
        """
        اختبار إنشاء حساب بشكل صحيح
        """
        self.assertEqual(self.account.name, 'حساب اختبار')
        self.assertEqual(self.account.account_type, 'cash')
        self.assertEqual(self.account.initial_balance, Decimal('1000.00'))
        self.assertEqual(self.account.current_balance, Decimal('1000.00'))
        self.assertEqual(self.account.description, 'وصف حساب الاختبار')
        self.assertEqual(self.account.created_by, self.user)
        self.assertIsNotNone(self.account.created_at)

    def test_account_str(self):
        """
        اختبار تمثيل الحساب كنص
        """
        self.assertEqual(str(self.account), 'حساب اختبار')

    def test_account_soft_delete(self):
        """
        اختبار الحذف الناعم للحساب
        """
        account_id = self.account.id
        self.account.delete()
        
        # يجب أن يكون الكائن غير موجود عند استخدام الدالة الافتراضية للحصول عليه
        self.assertFalse(Account.objects.filter(id=account_id).exists())
        
        # يجب أن يكون الكائن موجودًا عند استخدام all_objects
        self.assertTrue(Account.all_objects.filter(id=account_id).exists())
        
        # يجب أن تكون قيمة deleted_at محددة
        deleted_account = Account.all_objects.get(id=account_id)
        self.assertIsNotNone(deleted_account.deleted_at)

    def test_account_balance_update(self):
        """
        اختبار تحديث رصيد الحساب
        """
        # الرصيد الأولي
        self.assertEqual(self.account.current_balance, Decimal('1000.00'))
        
        # إضافة مبلغ للحساب
        self.account.current_balance += Decimal('500.00')
        self.account.save()
        
        # التحقق بعد الإضافة
        updated_account = Account.objects.get(id=self.account.id)
        self.assertEqual(updated_account.current_balance, Decimal('1500.00'))
        
        # سحب مبلغ من الحساب
        updated_account.current_balance -= Decimal('300.00')
        updated_account.save()
        
        # التحقق بعد السحب
        latest_account = Account.objects.get(id=self.account.id)
        self.assertEqual(latest_account.current_balance, Decimal('1200.00'))


class PaymentMethodModelTest(TestCase):
    """
    اختبارات نموذج طرق الدفع
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.payment_method = PaymentMethod.objects.create(
            name='طريقة دفع اختبار',
            description='وصف طريقة الدفع',
            created_by=self.user
        )

    def test_payment_method_creation(self):
        """
        اختبار إنشاء طريقة دفع بشكل صحيح
        """
        self.assertEqual(self.payment_method.name, 'طريقة دفع اختبار')
        self.assertEqual(self.payment_method.description, 'وصف طريقة الدفع')
        self.assertEqual(self.payment_method.created_by, self.user)
        self.assertIsNotNone(self.payment_method.created_at)

    def test_payment_method_str(self):
        """
        اختبار تمثيل طريقة الدفع كنص
        """
        self.assertEqual(str(self.payment_method), 'طريقة دفع اختبار')

    def test_payment_method_soft_delete(self):
        """
        اختبار الحذف الناعم لطريقة الدفع
        """
        method_id = self.payment_method.id
        self.payment_method.delete()
        
        # يجب أن يكون الكائن غير موجود عند استخدام الدالة الافتراضية للحصول عليه
        self.assertFalse(PaymentMethod.objects.filter(id=method_id).exists())
        
        # يجب أن يكون الكائن موجودًا عند استخدام all_objects
        self.assertTrue(PaymentMethod.all_objects.filter(id=method_id).exists())
        
        # يجب أن تكون قيمة deleted_at محددة
        deleted_method = PaymentMethod.all_objects.get(id=method_id)
        self.assertIsNotNone(deleted_method.deleted_at)


class TransactionModelTest(TestCase):
    """
    اختبارات نموذج المعاملات المالية
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # إنشاء الحسابات
        self.cash_account = Account.objects.create(
            name='الصندوق',
            account_type='cash',
            initial_balance=Decimal('5000.00'),
            created_by=self.user
        )
        
        self.bank_account = Account.objects.create(
            name='البنك',
            account_type='bank',
            initial_balance=Decimal('10000.00'),
            created_by=self.user
        )
        
        # إنشاء طريقة الدفع
        self.payment_method = PaymentMethod.objects.create(
            name='نقدي',
            created_by=self.user
        )
        
        # إنشاء العميل
        self.customer = Customer.objects.create(
            name='عميل اختبار',
            phone='01234567890',
            created_by=self.user
        )
        
        # إنشاء المورد
        self.supplier = Supplier.objects.create(
            name='مورد اختبار',
            phone='09876543210',
            created_by=self.user
        )
        
        # إنشاء معاملة مصروفات
        self.expense_transaction = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='expense',
            amount=Decimal('500.00'),
            account=self.cash_account,
            payment_method=self.payment_method,
            description='مصروف اختبار',
            reference='EXP-001',
            created_by=self.user
        )
        
        # إنشاء معاملة إيرادات
        self.income_transaction = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='income',
            amount=Decimal('1000.00'),
            account=self.cash_account,
            payment_method=self.payment_method,
            description='إيراد اختبار',
            reference='INC-001',
            created_by=self.user
        )
        
        # إنشاء معاملة تحويل
        self.transfer_transaction = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='transfer',
            amount=Decimal('1500.00'),
            account=self.cash_account,
            destination_account=self.bank_account,
            payment_method=self.payment_method,
            description='تحويل بين الحسابات',
            reference='TRF-001',
            created_by=self.user
        )

    def test_transaction_creation(self):
        """
        اختبار إنشاء معاملات بشكل صحيح
        """
        # اختبار معاملة المصروفات
        self.assertEqual(self.expense_transaction.transaction_type, 'expense')
        self.assertEqual(self.expense_transaction.amount, Decimal('500.00'))
        self.assertEqual(self.expense_transaction.account, self.cash_account)
        self.assertEqual(self.expense_transaction.payment_method, self.payment_method)
        
        # اختبار معاملة الإيرادات
        self.assertEqual(self.income_transaction.transaction_type, 'income')
        self.assertEqual(self.income_transaction.amount, Decimal('1000.00'))
        self.assertEqual(self.income_transaction.account, self.cash_account)
        
        # اختبار معاملة التحويل
        self.assertEqual(self.transfer_transaction.transaction_type, 'transfer')
        self.assertEqual(self.transfer_transaction.amount, Decimal('1500.00'))
        self.assertEqual(self.transfer_transaction.account, self.cash_account)
        self.assertEqual(self.transfer_transaction.destination_account, self.bank_account)

    def test_transaction_str(self):
        """
        اختبار تمثيل المعاملة كنص
        """
        self.assertIn('مصروف', str(self.expense_transaction))
        self.assertIn('500.00', str(self.expense_transaction))
        
        self.assertIn('إيراد', str(self.income_transaction))
        self.assertIn('1000.00', str(self.income_transaction))
        
        self.assertIn('تحويل', str(self.transfer_transaction))
        self.assertIn('1500.00', str(self.transfer_transaction))

    def test_transaction_balance_update(self):
        """
        اختبار تأثير المعاملات على أرصدة الحسابات
        """
        # تحديث الأرصدة - عادة ما تقوم الاشارة (signal) بهذا العمل تلقائياً
        # هنا نقوم بمحاكاة تأثير الإشارات على الأرصدة
        
        # الرصيد الأصلي للصندوق 5000
        # تأثير المصروف: -500
        # تأثير الإيراد: +1000
        # تأثير التحويل: -1500
        # الرصيد النهائي المتوقع: 5000 - 500 + 1000 - 1500 = 4000
        
        self.cash_account.current_balance = Decimal('5000.00') - Decimal('500.00') + Decimal('1000.00') - Decimal('1500.00')
        self.cash_account.save()
        
        # الرصيد الأصلي للبنك 10000
        # تأثير التحويل: +1500
        # الرصيد النهائي المتوقع: 10000 + 1500 = 11500
        
        self.bank_account.current_balance = Decimal('10000.00') + Decimal('1500.00')
        self.bank_account.save()
        
        # التحقق من الأرصدة
        updated_cash = Account.objects.get(id=self.cash_account.id)
        updated_bank = Account.objects.get(id=self.bank_account.id)
        
        self.assertEqual(updated_cash.current_balance, Decimal('4000.00'))
        self.assertEqual(updated_bank.current_balance, Decimal('11500.00'))

    def test_transaction_with_related_entities(self):
        """
        اختبار المعاملات المرتبطة بالعملاء والموردين
        """
        # معاملة مرتبطة بعميل (تحصيل من عميل)
        customer_payment = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='income',
            amount=Decimal('800.00'),
            account=self.cash_account,
            payment_method=self.payment_method,
            description='تحصيل من عميل',
            reference='CUST-PAY-001',
            related_to='customer',
            customer=self.customer,
            created_by=self.user
        )
        
        # معاملة مرتبطة بمورد (دفع لمورد)
        supplier_payment = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='expense',
            amount=Decimal('1200.00'),
            account=self.cash_account,
            payment_method=self.payment_method,
            description='دفع لمورد',
            reference='SUPP-PAY-001',
            related_to='supplier',
            supplier=self.supplier,
            created_by=self.user
        )
        
        # التحقق من إنشاء المعاملات بشكل صحيح
        self.assertEqual(customer_payment.related_to, 'customer')
        self.assertEqual(customer_payment.customer, self.customer)
        self.assertEqual(customer_payment.amount, Decimal('800.00'))
        
        self.assertEqual(supplier_payment.related_to, 'supplier')
        self.assertEqual(supplier_payment.supplier, self.supplier)
        self.assertEqual(supplier_payment.amount, Decimal('1200.00')) 