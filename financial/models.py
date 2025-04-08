from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

User = settings.AUTH_USER_MODEL


class Category(models.Model):
    """
    فئات المصروفات والإيرادات
    """
    TYPE_CHOICES = (
        ('expense', _('مصروف')),
        ('income', _('إيراد')),
    )
    
    name = models.CharField(_('الاسم'), max_length=100)
    type = models.CharField(_('النوع'), max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(_('الوصف'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('فئة')
        verbose_name_plural = _('الفئات')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Account(models.Model):
    """
    الحسابات المالية
    """
    TYPE_CHOICES = (
        ('cash', _('نقدي')),
        ('bank', _('بنكي')),
        ('wallet', _('محفظة إلكترونية')),
        ('other', _('آخر')),
    )
    
    name = models.CharField(_('الاسم'), max_length=100)
    account_number = models.CharField(_('رقم الحساب'), max_length=100, blank=True, null=True)
    type = models.CharField(_('النوع'), max_length=20, choices=TYPE_CHOICES, default='bank')
    code = models.CharField(_('الكود'), max_length=20, unique=True, blank=True, null=True)
    balance = models.DecimalField(_('الرصيد'), max_digits=12, decimal_places=2, default=0)
    description = models.TextField(_('الوصف'), blank=True, null=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                              verbose_name=_('الحساب الأب'), related_name='children')
    account_type = models.CharField(_('نوع الحساب'), max_length=50, blank=True, null=True)
    is_bank_reconciliation = models.BooleanField(_('يخضع للتسوية البنكية'), default=False)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('أنشئ بواسطة'), related_name='created_accounts')
    
    class Meta:
        verbose_name = _('حساب')
        verbose_name_plural = _('الحسابات')
        ordering = ['name']
    
    def __str__(self):
        return self.name
        
    def get_balance(self):
        """
        الحصول على الرصيد الحالي للحساب
        """
        return self.balance
        
    def update_balance(self, amount, operation='add'):
        """
        تحديث رصيد الحساب
        
        الوسائط:
            amount: المبلغ للإضافة أو الخصم
            operation: العملية ('add' للإضافة، 'subtract' للخصم)
        
        العائد:
            boolean: نجاح أو فشل العملية
        """
        print(f"Updating balance for account {self.id} - {self.name}: Current={self.balance}, Amount={amount}, Operation={operation}")
        
        if operation == 'add':
            self.balance += amount
        elif operation == 'subtract':
            if self.balance >= amount:
                self.balance -= amount
            else:
                print(f"Warning: Attempted to subtract {amount} from {self.balance} for account {self.id} - {self.name}")
                self.balance = 0
                
        try:
            from django.db import IntegrityError, transaction
            try:
                with transaction.atomic():
                    # تحديث فقط حقل الرصيد لتجنب تعارض التحديثات
                    Account.objects.filter(id=self.id).update(balance=self.balance)
                    # تحديث الكائن المحلي ليعكس التغييرات المخزنة
                    self.refresh_from_db(fields=['balance'])
                    print(f"Successfully updated balance for account {self.id} - {self.name}: New balance={self.balance}")
                    return True
            except IntegrityError as e:
                print(f"Database error updating balance: {str(e)}")
                return False
        except Exception as e:
            print(f"Error updating balance: {str(e)}")
            # على الأقل نحفظ الكائن المحلي
            self.save(update_fields=['balance', 'updated_at'])
            print(f"Fallback save for account {self.id} - {self.name}: New balance={self.balance}")
            return True
    
    def reconcile(self, bank_statement_balance, reconciliation_date=None):
        """
        إجراء التسوية البنكية
        
        الوسائط:
            bank_statement_balance: رصيد كشف الحساب البنكي
            reconciliation_date: تاريخ التسوية (افتراضيًا التاريخ الحالي)
        
        العائد:
            tuple: (نجاح/فشل، رسالة، الفرق)
        """
        if not self.is_bank_reconciliation:
            return (False, "هذا الحساب لا يخضع للتسوية البنكية", 0)
            
        if reconciliation_date is None:
            reconciliation_date = timezone.now().date()
            
        difference = bank_statement_balance - self.balance
        
        # تسجيل تفاصيل التسوية في سجل خاص
        BankReconciliation.objects.create(
            account=self,
            reconciliation_date=reconciliation_date,
            system_balance=self.balance,
            bank_balance=bank_statement_balance,
            difference=difference
        )
        
        if difference != 0:
            return (True, f"تمت التسوية مع وجود فرق بقيمة {difference}", difference)
        else:
            return (True, "تمت التسوية بدون فروقات", 0)


class BankReconciliation(models.Model):
    """
    نموذج التسوية البنكية
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name=_('الحساب'), related_name='reconciliations')
    reconciliation_date = models.DateField(_('تاريخ التسوية'), default=timezone.now)
    system_balance = models.DecimalField(_('رصيد النظام'), max_digits=12, decimal_places=2)
    bank_balance = models.DecimalField(_('رصيد البنك'), max_digits=12, decimal_places=2)
    difference = models.DecimalField(_('الفرق'), max_digits=12, decimal_places=2)
    notes = models.TextField(_('ملاحظات'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('أنشئ بواسطة'), related_name='bank_reconciliations')
    
    class Meta:
        verbose_name = _('تسوية بنكية')
        verbose_name_plural = _('التسويات البنكية')
        ordering = ['-reconciliation_date']
    
    def __str__(self):
        return f"{self.account.name} - {self.reconciliation_date}"


class Transaction(models.Model):
    """
    المعاملات المالية
    """
    TRANSACTION_TYPES = (
        ('income', _('إيراد')),
        ('expense', _('مصروف')),
        ('transfer', _('تحويل')),
    )
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True, verbose_name=_('الحساب'))
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='incoming_transactions', null=True, blank=True, verbose_name=_('الحساب المستلم'))
    transaction_type = models.CharField(_('نوع المعاملة'), max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    date = models.DateField(_('التاريخ'), default=timezone.now)
    description = models.TextField(_('الوصف'), blank=True, null=True)
    reference_number = models.CharField(_('رقم المرجع'), max_length=100, blank=True, null=True)
    reference = models.CharField(_('المرجع'), max_length=100, blank=True, null=True)
    is_reconciled = models.BooleanField(_('تمت التسوية'), default=False)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('أنشئ بواسطة'), related_name='created_transactions')
    
    class Meta:
        verbose_name = _('معاملة')
        verbose_name_plural = _('المعاملات')
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount}"
        
    def get_type_class(self):
        """
        استرجاع فئة CSS لنوع المعاملة
        """
        type_classes = {
            'income': 'income',
            'expense': 'expense',
            'transfer': 'transfer'
        }
        return type_classes.get(self.transaction_type, '')
    
    def get_type_icon(self):
        """
        استرجاع أيقونة لنوع المعاملة
        """
        type_icons = {
            'income': 'fa-arrow-down',
            'expense': 'fa-arrow-up',
            'transfer': 'fa-exchange-alt'
        }
        return type_icons.get(self.transaction_type, 'fa-circle')
    
    @property
    def deposit(self):
        """
        استرجاع مبلغ الإيداع (للإيرادات فقط)
        """
        if self.transaction_type == 'income':
            return self.amount
        return None
    
    @property
    def withdraw(self):
        """
        استرجاع مبلغ السحب (للمصروفات فقط)
        """
        if self.transaction_type == 'expense':
            return self.amount
        return None
    
    @property
    def balance_after(self):
        """
        استرجاع الرصيد بعد العملية
        """
        if not self.account:
            return None
            
        # الحصول على الرصيد الحالي للحساب
        current_balance = self.account.balance
        
        # الحصول على تاريخ المعاملة
        transaction_date = self.date
        
        # الحصول على معرف المعاملة الحالية
        transaction_id = self.id or 0
        
        # الحصول على جميع المعاملات للحساب حتى هذه المعاملة (بما فيها هذه المعاملة)
        all_transactions = Transaction.objects.filter(
            Q(account=self.account) | Q(to_account=self.account),
            Q(date__lt=transaction_date) | (Q(date=transaction_date) & Q(id__lte=transaction_id))
        ).order_by('date', 'id')
        
        # حساب الرصيد بعد كل معاملة
        running_balance = 0
        for trans in all_transactions:
            # إذا كانت المعاملة إيرادًا والحساب هو حساب المستلم، أضف المبلغ
            if trans.transaction_type == 'income' and trans.account == self.account:
                running_balance += trans.amount
            # إذا كانت المعاملة مصروفًا والحساب هو حساب المصدر، اطرح المبلغ
            elif trans.transaction_type == 'expense' and trans.account == self.account:
                running_balance -= trans.amount
            # إذا كانت المعاملة تحويلًا
            elif trans.transaction_type == 'transfer':
                # إذا كان الحساب هو حساب المصدر، اطرح المبلغ
                if trans.account == self.account:
                    running_balance -= trans.amount
                # إذا كان الحساب هو حساب المستلم، أضف المبلغ
                elif trans.to_account == self.account:
                    running_balance += trans.amount
        
        return running_balance


class TransactionLine(models.Model):
    """
    بنود المعاملة المالية (القيود المحاسبية)
    """
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='lines', verbose_name=_('المعاملة'))
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transaction_lines', verbose_name=_('الحساب'))
    debit = models.DecimalField(_('مدين'), max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(_('دائن'), max_digits=12, decimal_places=2, default=0)
    description = models.TextField(_('الوصف'), blank=True, null=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('بند معاملة')
        verbose_name_plural = _('بنود المعاملات')
    
    def __str__(self):
        return f"{self.account.name} - {self.debit or self.credit}"


class Expense(models.Model):
    """
    نموذج المصروفات المالية
    """
    STATUS_CHOICES = (
        ('pending', _('قيد الانتظار')),
        ('paid', _('مدفوع')),
        ('cancelled', _('ملغي')),
    )
    
    title = models.CharField(_('العنوان'), max_length=200)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='expenses_accounts', verbose_name=_('حساب المصروف'))
    payment_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='payment_expenses', verbose_name=_('حساب الدفع'))
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    date = models.DateField(_('تاريخ المصروف'), default=timezone.now)
    payment_date = models.DateField(_('تاريخ الدفع'), null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='expenses', verbose_name=_('الفئة'))
    description = models.TextField(_('الوصف'), blank=True, null=True)
    reference_number = models.CharField(_('رقم المرجع'), max_length=100, blank=True, null=True)
    reference = models.CharField(_('المرجع'), max_length=100, blank=True, null=True)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses', verbose_name=_('المعاملة المالية'))
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('أنشئ بواسطة'), related_name='created_expenses')
    
    class Meta:
        verbose_name = _('مصروف')
        verbose_name_plural = _('المصروفات')
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.title} - {self.amount}"


class Income(models.Model):
    """
    نموذج الإيرادات المالية
    """
    STATUS_CHOICES = (
        ('pending', _('قيد الانتظار')),
        ('received', _('مستلم')),
        ('cancelled', _('ملغي')),
    )
    
    title = models.CharField(_('العنوان'), max_length=200)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='income_accounts', verbose_name=_('حساب الإيراد'))
    receiving_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='received_incomes', verbose_name=_('حساب الاستلام'))
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    date = models.DateField(_('تاريخ الإيراد'), default=timezone.now)
    received_date = models.DateField(_('تاريخ الاستلام'), null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='incomes', verbose_name=_('الفئة'))
    description = models.TextField(_('الوصف'), blank=True, null=True)
    reference_number = models.CharField(_('رقم المرجع'), max_length=100, blank=True, null=True)
    reference = models.CharField(_('المرجع'), max_length=100, blank=True, null=True)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='incomes', verbose_name=_('المعاملة المالية'))
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('أنشئ بواسطة'), related_name='created_incomes')
    
    class Meta:
        verbose_name = _('إيراد')
        verbose_name_plural = _('الإيرادات')
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.title} - {self.amount}"
