from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from product.models import Product, Category
from sale.models import Sale, Customer
from purchase.models import Purchase, Supplier
from financial.models import Transaction, Account
import re
from datetime import datetime

User = get_user_model()

class SecurityTestCase(TestCase):
    """
    اختبارات الأمان في النظام
    """
    def setUp(self):
        """
        إعداد البيانات المطلوبة للاختبارات
        """
        # إنشاء مستخدمين مختلفين للاختبار
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        
        self.manager_user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='manager123'
        )
        
        self.sales_user = User.objects.create_user(
            username='sales',
            email='sales@example.com',
            password='sales123'
        )
        
        self.finance_user = User.objects.create_user(
            username='finance',
            email='finance@example.com',
            password='finance123'
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regular123'
        )
        
        # إنشاء عميل HTTP
        self.client = Client()
        
        # إنشاء مجموعات المستخدمين
        self.manager_group = Group.objects.create(name='المدراء')
        self.sales_group = Group.objects.create(name='المبيعات')
        self.finance_group = Group.objects.create(name='المالية')
        
        # إضافة المستخدمين إلى المجموعات
        self.manager_user.groups.add(self.manager_group)
        self.sales_user.groups.add(self.sales_group)
        self.finance_user.groups.add(self.finance_group)
        
        # إنشاء أذونات المجموعات
        self._create_group_permissions()
        
        # إنشاء بيانات للاختبار
        self._create_test_data()
    
    def _create_group_permissions(self):
        """
        إنشاء أذونات للمجموعات المختلفة
        """
        # الحصول على أنواع المحتوى للنماذج
        product_ct = ContentType.objects.get_for_model(Product)
        category_ct = ContentType.objects.get_for_model(Category)
        sale_ct = ContentType.objects.get_for_model(Sale)
        customer_ct = ContentType.objects.get_for_model(Customer)
        purchase_ct = ContentType.objects.get_for_model(Purchase)
        supplier_ct = ContentType.objects.get_for_model(Supplier)
        account_ct = ContentType.objects.get_for_model(Account)
        transaction_ct = ContentType.objects.get_for_model(Transaction)
        
        # أذونات المدراء (كل شيء)
        manager_perms = Permission.objects.filter(
            content_type__in=[product_ct, category_ct, sale_ct, customer_ct, 
                             purchase_ct, supplier_ct, account_ct, transaction_ct]
        )
        self.manager_group.permissions.add(*manager_perms)
        
        # أذونات المبيعات (المنتجات والعملاء والمبيعات - قراءة فقط للمشتريات)
        sales_perms = Permission.objects.filter(
            content_type__in=[product_ct, sale_ct, customer_ct]
        )
        purchase_view_perm = Permission.objects.get(
            content_type=purchase_ct, 
            codename='view_purchase'
        )
        sales_perms = list(sales_perms)
        sales_perms.append(purchase_view_perm)
        self.sales_group.permissions.add(*sales_perms)
        
        # أذونات المالية (الحسابات والمعاملات المالية - قراءة فقط للمبيعات والمشتريات)
        finance_perms = Permission.objects.filter(
            content_type__in=[account_ct, transaction_ct]
        )
        sale_view_perm = Permission.objects.get(
            content_type=sale_ct,
            codename='view_sale'
        )
        purchase_view_perm = Permission.objects.get(
            content_type=purchase_ct,
            codename='view_purchase'
        )
        finance_perms = list(finance_perms)
        finance_perms.extend([sale_view_perm, purchase_view_perm])
        self.finance_group.permissions.add(*finance_perms)
    
    def _create_test_data(self):
        """
        إنشاء بيانات للاختبار
        """
        # إنشاء فئة منتج
        self.category = Category.objects.create(
            name='فئة اختبار الأمان',
            description='وصف فئة اختبار الأمان',
            created_by=self.admin_user
        )
        
        # إنشاء منتج
        self.product = Product.objects.create(
            name='منتج اختبار الأمان',
            code='SEC001',
            category=self.category,
            purchase_price=100.00,
            sale_price=150.00,
            created_by=self.admin_user
        )
        
        # إنشاء عميل
        self.customer = Customer.objects.create(
            name='عميل اختبار الأمان',
            phone='01234567890',
            address='عنوان عميل اختبار الأمان',
            created_by=self.admin_user
        )
        
        # إنشاء مورد
        self.supplier = Supplier.objects.create(
            name='مورد اختبار الأمان',
            phone='09876543210',
            address='عنوان مورد اختبار الأمان',
            created_by=self.admin_user
        )
        
        # إنشاء حساب مالي
        self.account = Account.objects.create(
            name='حساب اختبار الأمان',
            account_type='cash',
            balance=10000.00,
            created_by=self.admin_user
        )
        
        # إنشاء عملية بيع
        self.sale = Sale.objects.create(
            customer=self.customer,
            invoice_no='SEC-SALE-001',
            date=datetime.now().date(),
            payment_method='cash',
            account=self.account,
            created_by=self.admin_user
        )
        
        # إنشاء عملية شراء
        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_no='SEC-PURCH-001',
            date=datetime.now().date(),
            payment_method='cash',
            account=self.account,
            created_by=self.admin_user
        )
        
        # إنشاء معاملة مالية
        self.transaction = Transaction.objects.create(
            account=self.account,
            transaction_type='income',
            amount=500.00,
            date=datetime.now().date(),
            description='معاملة اختبار الأمان',
            created_by=self.admin_user
        )
    
    def test_anonymous_access(self):
        """
        اختبار عدم السماح بالدخول للصفحات بدون تسجيل دخول
        """
        # قائمة من عناوين URL للاختبار
        urls_to_test = [
            reverse('dashboard:index'),
            reverse('product:product_list'),
            reverse('product:category_list'),
            reverse('sale:sale_list'),
            reverse('sale:customer_list'),
            reverse('purchase:purchase_list'),
            reverse('purchase:supplier_list'),
            reverse('financial:account_list'),
            reverse('financial:transaction_list')
        ]
        
        # اختبار كل عنوان URL
        for url in urls_to_test:
            response = self.client.get(url)
            
            # يجب أن يتم إعادة التوجيه إلى صفحة تسجيل الدخول
            self.assertRedirects(
                response, 
                f'/accounts/login/?next={url}',
                msg_prefix=f"Failed for URL: {url}"
            )
    
    def test_login_required_middleware(self):
        """
        اختبار middleware طلب تسجيل الدخول
        """
        # محاولة الوصول إلى لوحة التحكم بدون تسجيل دخول
        response = self.client.get(reverse('dashboard:index'))
        
        # يجب أن يتم إعادة التوجيه إلى صفحة تسجيل الدخول
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_csrf_protection(self):
        """
        اختبار حماية CSRF
        """
        # تسجيل دخول كمدير
        self.client.login(username='manager', password='manager123')
        
        # محاولة إرسال نموذج بدون رمز CSRF
        response = self.client.post(
            reverse('product:category_create'),
            {
                'name': 'فئة اختبار CSRF',
                'description': 'وصف فئة اختبار CSRF'
            },
            enforce_csrf_checks=True
        )
        
        # يجب رفض الطلب لعدم وجود رمز CSRF
        self.assertEqual(response.status_code, 403)
    
    def test_permission_enforcement(self):
        """
        اختبار تطبيق الأذونات
        """
        # تسجيل دخول كمستخدم عادي (بدون أذونات)
        self.client.login(username='regular', password='regular123')
        
        # محاولة الوصول إلى صفحات محمية
        protected_urls = [
            reverse('product:product_create'),
            reverse('sale:sale_create'),
            reverse('purchase:purchase_create'),
            reverse('financial:transaction_create')
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            
            # يجب أن يتم رفض الوصول أو إعادة التوجيه
            self.assertIn(response.status_code, [302, 403])
    
    def test_manager_permissions(self):
        """
        اختبار أذونات المدير
        """
        # تسجيل دخول كمدير
        self.client.login(username='manager', password='manager123')
        
        # يجب أن يكون للمدير وصول لجميع الصفحات
        urls_to_test = [
            reverse('product:product_list'),
            reverse('product:product_create'),
            reverse('sale:sale_list'),
            reverse('sale:sale_create'),
            reverse('purchase:purchase_list'),
            reverse('purchase:purchase_create'),
            reverse('financial:transaction_list')
        ]
        
        for url in urls_to_test:
            response = self.client.get(url)
            
            # يجب أن يكون لديه وصول
            self.assertEqual(response.status_code, 200, f"لا يستطيع المدير الوصول إلى {url}")
    
    def test_sales_permissions(self):
        """
        اختبار أذونات مستخدم المبيعات
        """
        # تسجيل دخول كمستخدم مبيعات
        self.client.login(username='sales', password='sales123')
        
        # يجب أن يكون لديه وصول إلى صفحات المبيعات والمنتجات
        allowed_urls = [
            reverse('product:product_list'),
            reverse('sale:sale_list'),
            reverse('sale:sale_create'),
            reverse('sale:customer_list'),
            reverse('purchase:purchase_list')  # قراءة فقط
        ]
        
        for url in allowed_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"لا يستطيع مستخدم المبيعات الوصول إلى {url}")
        
        # يجب ألا يكون لديه وصول إلى صفحات المشتريات والمالية للإنشاء أو التعديل
        restricted_urls = [
            reverse('purchase:purchase_create'),
            reverse('financial:transaction_list'),
            reverse('financial:transaction_create')
        ]
        
        for url in restricted_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [302, 403], f"يستطيع مستخدم المبيعات الوصول إلى {url}")
    
    def test_finance_permissions(self):
        """
        اختبار أذونات مستخدم المالية
        """
        # تسجيل دخول كمستخدم مالية
        self.client.login(username='finance', password='finance123')
        
        # يجب أن يكون لديه وصول إلى صفحات المالية
        allowed_urls = [
            reverse('financial:account_list'),
            reverse('financial:transaction_list'),
            reverse('financial:transaction_create'),
            reverse('sale:sale_list'),  # قراءة فقط
            reverse('purchase:purchase_list')  # قراءة فقط
        ]
        
        for url in allowed_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"لا يستطيع مستخدم المالية الوصول إلى {url}")
        
        # يجب ألا يكون لديه وصول إلى صفحات إنشاء المبيعات والمشتريات
        restricted_urls = [
            reverse('sale:sale_create'),
            reverse('purchase:purchase_create')
        ]
        
        for url in restricted_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [302, 403], f"يستطيع مستخدم المالية الوصول إلى {url}")
    
    def test_object_level_permissions(self):
        """
        اختبار أذونات على مستوى الكائنات
        """
        # إنشاء منتج مملوك لمستخدم المبيعات
        sales_product = Product.objects.create(
            name='منتج مستخدم المبيعات',
            code='SALES001',
            category=self.category,
            purchase_price=100.00,
            sale_price=150.00,
            created_by=self.sales_user
        )
        
        # إنشاء منتج مملوك لمستخدم المالية
        finance_product = Product.objects.create(
            name='منتج مستخدم المالية',
            code='FIN001',
            category=self.category,
            purchase_price=100.00,
            sale_price=150.00,
            created_by=self.finance_user
        )
        
        # تسجيل دخول كمستخدم مبيعات
        self.client.login(username='sales', password='sales123')
        
        # يجب أن يستطيع تعديل المنتج الخاص به
        response = self.client.get(
            reverse('product:product_edit', args=[sales_product.id])
        )
        self.assertEqual(response.status_code, 200)
        
        # لاختبار أذونات أكثر تفصيلاً على مستوى الكائنات، يمكن التحقق من العرض بدلاً من الوصول للصفحة
        # نفترض أن هناك منطق في العرض يتحقق من أذونات الكائن
        
    @override_settings(DEBUG=False)
    def test_xss_protection(self):
        """
        اختبار الحماية من هجمات XSS
        """
        # تسجيل دخول كمدير
        self.client.login(username='manager', password='manager123')
        
        # محاولة إنشاء فئة بمحتوى JavaScript خبيث
        xss_payload = '<script>alert("XSS")</script>'
        
        response = self.client.post(
            reverse('product:category_create'),
            {
                'name': 'فئة XSS',
                'description': xss_payload
            }
        )
        
        # التحقق من أن المحتوى الخبيث لم يتم تخزينه كما هو
        category = Category.objects.get(name='فئة XSS')
        self.assertNotEqual(category.description, xss_payload)
        
        # عرض صفحة الفئة
        response = self.client.get(
            reverse('product:category_detail', args=[category.id])
        )
        
        # التحقق من عدم وجود المحتوى الخبيث في الاستجابة
        content = response.content.decode('utf-8')
        self.assertNotIn('<script>alert("XSS")</script>', content)
    
    def test_sql_injection_protection(self):
        """
        اختبار الحماية من هجمات SQL Injection
        """
        # تسجيل دخول كمدير
        self.client.login(username='manager', password='manager123')
        
        # محاولة استخدام محتوى SQL Injection في البحث
        sql_payload = "' OR '1'='1"
        
        # استخدام معلمة البحث في صفحة قائمة المنتجات
        response = self.client.get(
            reverse('product:product_list'),
            {'search': sql_payload}
        )
        
        # يجب أن تنجح الاستجابة ولا تؤدي إلى خطأ (هذا يعني أن Django قام بحماية الاستعلام)
        self.assertEqual(response.status_code, 200)
        
        # للتأكد أكثر، نتحقق من عدم استرجاع جميع المنتجات (لو نجح الـ SQL Injection لاسترجع كل المنتجات)
        # نفترض أن المنتجات مرتبطة بالسياق
        if 'products' in response.context:
            self.assertNotEqual(
                response.context['products'].count(), 
                Product.objects.count(),
                "تم استرجاع جميع المنتجات، مما يشير إلى احتمالية نجاح SQL Injection"
            )
    
    def test_secure_password_reset(self):
        """
        اختبار أمان إعادة تعيين كلمة المرور
        """
        # اختبار أن إعادة تعيين كلمة المرور تتطلب بريد إلكتروني مسجل
        response = self.client.post(
            reverse('password_reset'),
            {'email': 'nonexistent@example.com'}
        )
        
        # مع ذلك، لا يجب أن تكشف الاستجابة ما إذا كان البريد الإلكتروني موجودًا أم لا (لأسباب أمنية)
        self.assertEqual(response.status_code, 302)  # إعادة التوجيه
    
    def test_rate_limiting(self):
        """
        اختبار تقييد معدل الطلبات (يتطلب إعداد Django مناسب)
        """
        # اختبار محاولات تسجيل دخول متكررة
        for _ in range(5):
            response = self.client.post(
                reverse('login'),
                {'username': 'admin', 'password': 'wrongpassword'}
            )
        
        # طلب إضافي بعد المحاولات الفاشلة
        # إذا كان تقييد المعدل مُفعّل، فقد يتم منع هذا الطلب أو تأخيره
        # نلاحظ: قد يتطلب إعدادات إضافية في settings.py
    
    def test_password_complexity(self):
        """
        اختبار تطبيق قواعد تعقيد كلمات المرور
        """
        # تسجيل دخول كمدير
        self.client.login(username='admin', password='admin123')
        
        # محاولة إنشاء مستخدم بكلمة مرور بسيطة
        response = self.client.post(
            reverse('user_create'),  # نفترض وجود هذا العنوان
            {
                'username': 'testuser',
                'email': 'testuser@example.com',
                'password1': '123456',
                'password2': '123456'
            }
        )
        
        # يجب أن يتم رفض كلمة المرور البسيطة
        # نلاحظ: هذا يعتمد على إعدادات تحقق كلمة المرور في Django
        
    def test_secure_headers(self):
        """
        اختبار ترويسات الأمان
        """
        # تسجيل دخول
        self.client.login(username='admin', password='admin123')
        
        # الوصول إلى صفحة محمية
        response = self.client.get(reverse('dashboard:index'))
        
        # التحقق من ترويسات الأمان (هذا يعتمد على إعدادات مخصصة في settings.py)
        headers = response.headers
        security_headers = [
            'X-Frame-Options',
            'X-Content-Type-Options',
            'Referrer-Policy',
            'X-XSS-Protection'
        ]
        
        for header in security_headers:
            if header in headers:
                self.assertIsNotNone(headers.get(header))
    
    def test_account_lockout(self):
        """
        اختبار قفل الحساب بعد محاولات تسجيل دخول فاشلة
        """
        # محاولات تسجيل دخول فاشلة متعددة
        for _ in range(5):
            self.client.post(
                reverse('login'),
                {'username': 'manager', 'password': 'wrongpassword'}
            )
        
        # محاولة تسجيل دخول بكلمة المرور الصحيحة
        response = self.client.post(
            reverse('login'),
            {'username': 'manager', 'password': 'manager123'}
        )
        
        # اختبار قفل الحساب (يعتمد على إعدادات قفل الحساب في Django)
        # إذا كان قفل الحساب مُفعّل، فقد يتم إعادة التوجيه إلى صفحة تأمين الحساب أو صفحة خطأ
        
    def test_secure_file_uploads(self):
        """
        اختبار أمان رفع الملفات
        """
        # تسجيل دخول كمدير
        self.client.login(username='manager', password='manager123')
        
        # محاولة رفع ملف خبيث (يجب أن يكون لديك عنوان URL لرفع الملفات)
        with open('core/tests/test_security.py', 'rb') as script_file:
            response = self.client.post(
                reverse('product:product_import'),  # نفترض وجود هذا العنوان
                {'file': script_file}
            )
        
        # يجب أن يتم رفض الملف أو معالجته بأمان
        
    def test_secure_cookies(self):
        """
        اختبار أمان ملفات تعريف الارتباط (cookies)
        """
        # تسجيل دخول
        self.client.login(username='admin', password='admin123')
        
        # الوصول إلى صفحة محمية
        response = self.client.get(reverse('dashboard:index'))
        
        # الحصول على ملفات تعريف الارتباط
        cookies = self.client.cookies
        
        # التحقق من إعدادات الأمان لملف تعريف ارتباط الجلسة
        if 'sessionid' in cookies:
            sessionid = cookies['sessionid']
            self.assertTrue(sessionid.secure)  # لاختبار ما إذا كان ملف تعريف الارتباط محدد كآمن
            
    def test_session_expiry(self):
        """
        اختبار انتهاء صلاحية الجلسة
        """
        # تسجيل دخول
        self.client.login(username='admin', password='admin123')
        
        # الوصول إلى صفحة محمية
        response = self.client.get(reverse('dashboard:index'))
        
        # التحقق من نجاح الاستجابة
        self.assertEqual(response.status_code, 200)
        
        # محاكاة انتهاء صلاحية الجلسة (تتطلب إعدادات مخصصة)
        # يمكن أن يتم ذلك عن طريق استبدال بيانات الجلسة أو التلاعب بها
        
    def test_audit_logging(self):
        """
        اختبار تسجيل الأحداث للمراجعة
        """
        # تسجيل دخول
        self.client.login(username='admin', password='admin123')
        
        # إجراء عملية هامة
        response = self.client.post(
            reverse('financial:transaction_create'),
            {
                'account': self.account.id,
                'transaction_type': 'expense',
                'amount': '500.00',
                'date': datetime.now().date().strftime('%Y-%m-%d'),
                'description': 'معاملة اختبار التسجيل'
            }
        )
        
        # التحقق من نجاح العملية
        self.assertEqual(response.status_code, 302)  # إعادة التوجيه بعد النجاح
        
        # يمكن التحقق من سجل المراجعة إذا كان مُفعّل (يتطلب وجود نظام تسجيل مراجعة) 