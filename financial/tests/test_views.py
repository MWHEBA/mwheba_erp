from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from financial.models import Account, Transaction, PaymentMethod
from sale.models import Customer
from purchase.models import Supplier
from decimal import Decimal
import json

User = get_user_model()

class AccountViewsTest(TestCase):
    """
    اختبارات صفحات الحسابات المالية
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # إنشاء حسابات للاختبار
        self.cash_account = Account.objects.create(
            name='الصندوق',
            account_type='cash',
            initial_balance=Decimal('5000.00'),
            description='حساب الصندوق للاختبار',
            created_by=self.user
        )
        
        self.bank_account = Account.objects.create(
            name='البنك',
            account_type='bank',
            initial_balance=Decimal('10000.00'),
            description='حساب البنك للاختبار',
            created_by=self.user
        )

    def test_account_list_view(self):
        """
        اختبار عرض قائمة الحسابات
        """
        url = reverse('financial:account_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/account_list.html')
        self.assertContains(response, 'الصندوق')
        self.assertContains(response, 'البنك')
        self.assertContains(response, '5000.00')
        self.assertContains(response, '10000.00')

    def test_account_detail_view(self):
        """
        اختبار عرض تفاصيل الحساب
        """
        url = reverse('financial:account_detail', args=[self.cash_account.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/account_detail.html')
        self.assertContains(response, 'الصندوق')
        self.assertContains(response, 'حساب الصندوق للاختبار')
        self.assertContains(response, '5000.00')

    def test_account_create_view_get(self):
        """
        اختبار صفحة إنشاء حساب - طلب GET
        """
        url = reverse('financial:account_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/account_form.html')
        self.assertContains(response, 'إنشاء حساب جديد')

    def test_account_create_view_post(self):
        """
        اختبار إنشاء حساب جديد - طلب POST
        """
        url = reverse('financial:account_create')
        
        account_data = {
            'name': 'حساب جديد',
            'account_type': 'other',
            'initial_balance': '2000.00',
            'description': 'وصف الحساب الجديد',
        }
        
        response = self.client.post(url, account_data, follow=True)
        
        self.assertEqual(response.status_code, 200)
        
        # التحقق من إنشاء الحساب بنجاح
        new_account = Account.objects.filter(name='حساب جديد').first()
        self.assertIsNotNone(new_account)
        self.assertEqual(new_account.account_type, 'other')
        self.assertEqual(new_account.initial_balance, Decimal('2000.00'))
        self.assertEqual(new_account.current_balance, Decimal('2000.00'))
        self.assertEqual(new_account.description, 'وصف الحساب الجديد')

    def test_account_edit_view(self):
        """
        اختبار تعديل حساب
        """
        url = reverse('financial:account_edit', args=[self.cash_account.id])
        
        # اختبار طلب GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/account_form.html')
        self.assertContains(response, 'تعديل حساب')
        self.assertContains(response, 'الصندوق')
        
        # اختبار طلب POST لتعديل الحساب
        edit_data = {
            'name': 'الصندوق المحدث',
            'account_type': 'cash',
            'initial_balance': '5000.00',  # لا يتغير الرصيد الأولي عادة
            'description': 'وصف محدث للصندوق',
        }
        
        response = self.client.post(url, edit_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # التحقق من تحديث الحساب بنجاح
        updated_account = Account.objects.get(id=self.cash_account.id)
        self.assertEqual(updated_account.name, 'الصندوق المحدث')
        self.assertEqual(updated_account.description, 'وصف محدث للصندوق')

    def test_account_delete_view(self):
        """
        اختبار حذف حساب
        """
        url = reverse('financial:account_delete', args=[self.cash_account.id])
        response = self.client.post(url, follow=True)
        
        # التحقق من تحويل المستخدم بعد الحذف
        self.assertEqual(response.status_code, 200)
        
        # التحقق من حذف الحساب بنجاح (الحذف الناعم)
        self.assertFalse(Account.objects.filter(id=self.cash_account.id).exists())
        
        # التحقق من وجود الحساب في all_objects (حذف ناعم)
        self.assertTrue(Account.all_objects.filter(id=self.cash_account.id).exists())


class TransactionViewsTest(TestCase):
    """
    اختبارات صفحات المعاملات المالية
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # إنشاء حساب للاختبار
        self.account = Account.objects.create(
            name='حساب اختبار',
            account_type='cash',
            initial_balance=Decimal('5000.00'),
            created_by=self.user
        )
        
        # إنشاء طريقة دفع
        self.payment_method = PaymentMethod.objects.create(
            name='نقدي',
            created_by=self.user
        )
        
        # إنشاء عميل ومورد
        self.customer = Customer.objects.create(
            name='عميل اختبار',
            phone='01234567890',
            created_by=self.user
        )
        
        self.supplier = Supplier.objects.create(
            name='مورد اختبار',
            phone='09876543210',
            created_by=self.user
        )
        
        # إنشاء معاملات مختلفة
        # معاملة مصروفات
        self.expense = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='expense',
            amount=Decimal('500.00'),
            account=self.account,
            payment_method=self.payment_method,
            description='مصروف اختبار',
            reference='EXP-001',
            created_by=self.user
        )
        
        # معاملة إيرادات
        self.income = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='income',
            amount=Decimal('1000.00'),
            account=self.account,
            payment_method=self.payment_method,
            description='إيراد اختبار',
            reference='INC-001',
            created_by=self.user
        )
        
        # معاملة مرتبطة بعميل
        self.customer_payment = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='income',
            amount=Decimal('800.00'),
            account=self.account,
            payment_method=self.payment_method,
            description='تحصيل من عميل',
            reference='CUST-PAY-001',
            related_to='customer',
            customer=self.customer,
            created_by=self.user
        )
        
        # معاملة مرتبطة بمورد
        self.supplier_payment = Transaction.objects.create(
            date=timezone.now().date(),
            transaction_type='expense',
            amount=Decimal('1200.00'),
            account=self.account,
            payment_method=self.payment_method,
            description='دفع لمورد',
            reference='SUPP-PAY-001',
            related_to='supplier',
            supplier=self.supplier,
            created_by=self.user
        )

    def test_transaction_list_view(self):
        """
        اختبار عرض قائمة المعاملات
        """
        url = reverse('financial:transaction_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/transaction_list.html')
        self.assertContains(response, 'مصروف اختبار')
        self.assertContains(response, 'إيراد اختبار')
        self.assertContains(response, 'تحصيل من عميل')
        self.assertContains(response, 'دفع لمورد')
        self.assertContains(response, '500.00')
        self.assertContains(response, '1000.00')

    def test_transaction_detail_view(self):
        """
        اختبار عرض تفاصيل المعاملة
        """
        url = reverse('financial:transaction_detail', args=[self.expense.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/transaction_detail.html')
        self.assertContains(response, 'مصروف اختبار')
        self.assertContains(response, '500.00')
        self.assertContains(response, 'EXP-001')
        self.assertContains(response, 'حساب اختبار')

    def test_transaction_create_expense_view(self):
        """
        اختبار إنشاء معاملة مصروفات
        """
        url = reverse('financial:expense_create')
        
        # اختبار طلب GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/transaction_form.html')
        self.assertContains(response, 'إنشاء معاملة مصروفات')
        
        # اختبار طلب POST
        expense_data = {
            'date': timezone.now().date().isoformat(),
            'amount': '300.00',
            'account': self.account.id,
            'payment_method': self.payment_method.id,
            'description': 'مصروف جديد',
            'reference': 'EXP-002',
        }
        
        response = self.client.post(url, expense_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # التحقق من إنشاء المعاملة بنجاح
        new_expense = Transaction.objects.filter(reference='EXP-002').first()
        self.assertIsNotNone(new_expense)
        self.assertEqual(new_expense.transaction_type, 'expense')
        self.assertEqual(new_expense.amount, Decimal('300.00'))
        self.assertEqual(new_expense.description, 'مصروف جديد')

    def test_transaction_create_income_view(self):
        """
        اختبار إنشاء معاملة إيرادات
        """
        url = reverse('financial:income_create')
        
        # اختبار طلب GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/transaction_form.html')
        self.assertContains(response, 'إنشاء معاملة إيرادات')
        
        # اختبار طلب POST
        income_data = {
            'date': timezone.now().date().isoformat(),
            'amount': '450.00',
            'account': self.account.id,
            'payment_method': self.payment_method.id,
            'description': 'إيراد جديد',
            'reference': 'INC-002',
        }
        
        response = self.client.post(url, income_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # التحقق من إنشاء المعاملة بنجاح
        new_income = Transaction.objects.filter(reference='INC-002').first()
        self.assertIsNotNone(new_income)
        self.assertEqual(new_income.transaction_type, 'income')
        self.assertEqual(new_income.amount, Decimal('450.00'))
        self.assertEqual(new_income.description, 'إيراد جديد')

    def test_transaction_create_transfer_view(self):
        """
        اختبار إنشاء معاملة تحويل بين الحسابات
        """
        # إنشاء حساب آخر للتحويل إليه
        destination_account = Account.objects.create(
            name='حساب الوجهة',
            account_type='bank',
            initial_balance=Decimal('2000.00'),
            created_by=self.user
        )
        
        url = reverse('financial:transfer_create')
        
        # اختبار طلب GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/transaction_form.html')
        self.assertContains(response, 'إنشاء معاملة تحويل')
        
        # اختبار طلب POST
        transfer_data = {
            'date': timezone.now().date().isoformat(),
            'amount': '600.00',
            'account': self.account.id,
            'destination_account': destination_account.id,
            'payment_method': self.payment_method.id,
            'description': 'تحويل بين الحسابات',
            'reference': 'TRF-001',
        }
        
        response = self.client.post(url, transfer_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # التحقق من إنشاء المعاملة بنجاح
        new_transfer = Transaction.objects.filter(reference='TRF-001').first()
        self.assertIsNotNone(new_transfer)
        self.assertEqual(new_transfer.transaction_type, 'transfer')
        self.assertEqual(new_transfer.amount, Decimal('600.00'))
        self.assertEqual(new_transfer.account, self.account)
        self.assertEqual(new_transfer.destination_account, destination_account)

    def test_transaction_edit_view(self):
        """
        اختبار تعديل معاملة
        """
        url = reverse('financial:transaction_edit', args=[self.expense.id])
        
        # اختبار طلب GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/transaction_form.html')
        self.assertContains(response, 'تعديل معاملة')
        self.assertContains(response, '500.00')
        
        # اختبار طلب POST لتعديل المعاملة
        edit_data = {
            'date': timezone.now().date().isoformat(),
            'amount': '550.00',
            'account': self.account.id,
            'payment_method': self.payment_method.id,
            'description': 'مصروف اختبار محدث',
            'reference': 'EXP-001-UPDATED',
        }
        
        response = self.client.post(url, edit_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # التحقق من تحديث المعاملة بنجاح
        updated_expense = Transaction.objects.get(id=self.expense.id)
        self.assertEqual(updated_expense.amount, Decimal('550.00'))
        self.assertEqual(updated_expense.description, 'مصروف اختبار محدث')
        self.assertEqual(updated_expense.reference, 'EXP-001-UPDATED')

    def test_transaction_delete_view(self):
        """
        اختبار حذف معاملة
        """
        url = reverse('financial:transaction_delete', args=[self.expense.id])
        response = self.client.post(url, follow=True)
        
        # التحقق من تحويل المستخدم بعد الحذف
        self.assertEqual(response.status_code, 200)
        
        # التحقق من حذف المعاملة بنجاح
        self.assertFalse(Transaction.objects.filter(id=self.expense.id).exists())


class PaymentMethodViewsTest(TestCase):
    """
    اختبارات صفحات طرق الدفع
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # إنشاء طرق دفع للاختبار
        self.payment_method = PaymentMethod.objects.create(
            name='نقدي',
            description='الدفع نقداً',
            created_by=self.user
        )

    def test_payment_method_list_view(self):
        """
        اختبار عرض قائمة طرق الدفع
        """
        url = reverse('financial:payment_method_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/payment_method_list.html')
        self.assertContains(response, 'نقدي')
        self.assertContains(response, 'الدفع نقداً')

    def test_payment_method_create_view(self):
        """
        اختبار إنشاء طريقة دفع جديدة
        """
        url = reverse('financial:payment_method_create')
        
        # اختبار طلب GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/payment_method_form.html')
        self.assertContains(response, 'إنشاء طريقة دفع جديدة')
        
        # اختبار طلب POST
        method_data = {
            'name': 'بطاقة ائتمان',
            'description': 'الدفع باستخدام بطاقة الائتمان',
        }
        
        response = self.client.post(url, method_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # التحقق من إنشاء طريقة الدفع بنجاح
        new_method = PaymentMethod.objects.filter(name='بطاقة ائتمان').first()
        self.assertIsNotNone(new_method)
        self.assertEqual(new_method.description, 'الدفع باستخدام بطاقة الائتمان')

    def test_payment_method_edit_view(self):
        """
        اختبار تعديل طريقة دفع
        """
        url = reverse('financial:payment_method_edit', args=[self.payment_method.id])
        
        # اختبار طلب GET
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'financial/payment_method_form.html')
        self.assertContains(response, 'تعديل طريقة دفع')
        self.assertContains(response, 'نقدي')
        
        # اختبار طلب POST لتعديل طريقة الدفع
        edit_data = {
            'name': 'نقدي محدث',
            'description': 'وصف محدث للدفع النقدي',
        }
        
        response = self.client.post(url, edit_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # التحقق من تحديث طريقة الدفع بنجاح
        updated_method = PaymentMethod.objects.get(id=self.payment_method.id)
        self.assertEqual(updated_method.name, 'نقدي محدث')
        self.assertEqual(updated_method.description, 'وصف محدث للدفع النقدي')

    def test_payment_method_delete_view(self):
        """
        اختبار حذف طريقة دفع
        """
        url = reverse('financial:payment_method_delete', args=[self.payment_method.id])
        response = self.client.post(url, follow=True)
        
        # التحقق من تحويل المستخدم بعد الحذف
        self.assertEqual(response.status_code, 200)
        
        # التحقق من حذف طريقة الدفع بنجاح (الحذف الناعم)
        self.assertFalse(PaymentMethod.objects.filter(id=self.payment_method.id).exists())
        
        # التحقق من وجود طريقة الدفع في all_objects (حذف ناعم)
        self.assertTrue(PaymentMethod.all_objects.filter(id=self.payment_method.id).exists()) 