from django import forms
from django.utils import timezone
from django.core.validators import MinValueValidator
from .models import Account, Transaction, Expense, Income, Category, BankReconciliation

class AccountForm(forms.ModelForm):
    """
    نموذج إضافة وتعديل حساب مالي
    """
    TYPE_CHOICES = (
        ('cash', 'نقدي'),
        ('bank', 'بنكي'),
        ('wallet', 'محفظة إلكترونية'),
        ('other', 'آخر'),
    )
    
    ACCOUNT_TYPE_CHOICES = (
        ('asset', 'أصول'),
        ('liability', 'خصوم'),
        ('equity', 'حقوق ملكية'),
        ('income', 'إيرادات'),
        ('expense', 'مصروفات'),
    )
    
    type = forms.ChoiceField(
        label='نوع الحساب',
        choices=TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    account_type = forms.ChoiceField(
        label='تصنيف الحساب',
        choices=ACCOUNT_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    initial_balance = forms.DecimalField(
        label='الرصيد الافتتاحي',
        required=False,
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Account
        fields = ['name', 'account_number', 'type', 'account_type', 'code', 'description', 'parent',
                'is_bank_reconciliation', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'is_bank_reconciliation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # جعل حقل الرصيد الافتتاحي مخفي في حالة التعديل
        if self.instance and self.instance.pk:
            self.fields['initial_balance'].widget = forms.HiddenInput()
            self.fields['initial_balance'].initial = 0
        
        # تعديل الاختيارات في حقل الأب لتظهر فقط الحسابات النشطة
        self.fields['parent'].queryset = Account.objects.filter(is_active=True)
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        instance = getattr(self, 'instance', None)
        
        # التحقق من عدم تكرار الكود
        if code:
            qs = Account.objects.filter(code=code)
            if instance and instance.pk:
                qs = qs.exclude(pk=instance.pk)
            
            if qs.exists():
                raise forms.ValidationError("هذا الكود مستخدم بالفعل، يرجى استخدام كود آخر.")
        
        return code
    
    def clean(self):
        cleaned_data = super().clean()
        account_type = cleaned_data.get('type')
        is_bank_reconciliation = cleaned_data.get('is_bank_reconciliation')
        
        # التحقق من أن خاصية التسوية البنكية مفعلة فقط للحسابات البنكية
        if is_bank_reconciliation and account_type != 'bank':
            self.add_error('is_bank_reconciliation', 'خاصية التسوية البنكية متاحة فقط للحسابات البنكية')
        
        return cleaned_data


class TransactionForm(forms.ModelForm):
    """
    نموذج إضافة معاملة مالية
    """
    to_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label='الحساب المستلم',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Transaction
        fields = ['account', 'transaction_type', 'amount', 'date', 'description', 'reference', 'reference_number', 'to_account']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-control'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()
        
        # تعديل الاختيارات في حقل الحساب لتظهر فقط الحسابات النشطة
        self.fields['account'].queryset = Account.objects.filter(is_active=True)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        transaction_type = cleaned_data.get('transaction_type')
        amount = cleaned_data.get('amount')
        to_account = cleaned_data.get('to_account')
        
        # التحقق من وجود الحساب الرئيسي
        if not account:
            self.add_error('account', 'يجب تحديد الحساب الرئيسي للمعاملة')
        
        # التحقق من وجود حساب الوجهة في حالة التحويل
        if transaction_type == 'transfer' and not to_account:
            self.add_error('to_account', 'يجب تحديد الحساب المستلم في حالة التحويل')
        
        if account and transaction_type and amount:
            if transaction_type == 'expense' or transaction_type == 'transfer':
                current_balance = account.get_balance()
                if amount > current_balance:
                    self.add_error('amount', f'رصيد الحساب غير كاف. الرصيد الحالي: {current_balance}')
            
            # التأكد من أن الحساب المصدر والوجهة مختلفان في حالة التحويل
            if transaction_type == 'transfer' and account == to_account:
                self.add_error('to_account', 'لا يمكن التحويل إلى نفس الحساب')
        
        return cleaned_data


class ExpenseForm(forms.ModelForm):
    """
    نموذج إضافة مصروف
    """
    class Meta:
        model = Expense
        fields = ['title', 'account', 'payment_account', 'amount', 'date', 'payment_date', 'category', 'description', 'reference', 'reference_number']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'payment_account': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()
        
        # استخدام جميع الحسابات النشطة
        self.fields['account'].queryset = Account.objects.filter(is_active=True)
        self.fields['payment_account'].queryset = Account.objects.filter(is_active=True)
        
        # فلترة فئات المصروفات فقط
        self.fields['category'].queryset = Category.objects.filter(type='expense', is_active=True)
        
        # تعيين حساب الخزينة كحساب افتراضي للدفع 
        try:
            # محاولة الحصول على حساب الخزينة
            default_account = Account.objects.filter(name__icontains='خزينة', is_active=True).first()
            if not default_account:
                default_account = Account.objects.filter(type='cash', is_active=True).first()
            
            if default_account:
                self.fields['payment_account'].initial = default_account.pk
                
                # جعل حساب المصروف نفسه كحساب خزينة للبساطة
                self.fields['account'].initial = default_account.pk
        except:
            pass
            
        # إخفاء حقل حساب المصروف لأننا نستخدم نفس حساب الدفع
        self.fields['account'].widget = forms.HiddenInput()
        
        # التأكد أن جميع الحقول الإلزامية معلمة
        self.fields['payment_account'].required = True
        self.fields['payment_account'].error_messages = {
            'required': 'يجب تحديد حساب الدفع'
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        payment_account = cleaned_data.get('payment_account')
        amount = cleaned_data.get('amount')
        
        # تعيين حساب المصروف نفسه كحساب الدفع
        if payment_account:
            cleaned_data['account'] = payment_account
            
        if payment_account and amount:
            current_balance = payment_account.get_balance()
            if amount > current_balance:
                self.add_error('amount', f'رصيد الحساب غير كاف. الرصيد الحالي: {current_balance}')
        
        return cleaned_data


class IncomeForm(forms.ModelForm):
    """
    نموذج إضافة إيراد
    """
    class Meta:
        model = Income
        fields = ['title', 'receiving_account', 'amount', 'date', 'received_date', 'category', 'description', 'reference', 'reference_number']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'receiving_account': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'received_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()
        
        # استخدام جميع الحسابات النشطة
        self.fields['receiving_account'].queryset = Account.objects.filter(is_active=True)
        
        # فلترة فئات الإيرادات فقط
        self.fields['category'].queryset = Category.objects.filter(type='income', is_active=True)
        
        # تعيين حساب الخزينة كحساب افتراضي للإستلام
        try:
            # محاولة الحصول على حساب الخزينة
            default_account = Account.objects.filter(name__icontains='خزينة', is_active=True).first()
            if not default_account:
                default_account = Account.objects.filter(type='cash', is_active=True).first()
            
            if default_account:
                self.fields['receiving_account'].initial = default_account.pk
        except:
            pass
            
        # جعل حقل حساب الإستلام غير إجباري
        self.fields['receiving_account'].required = False
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر')
        return amount


class BankReconciliationForm(forms.ModelForm):
    """
    نموذج التسوية البنكية
    """
    class Meta:
        model = BankReconciliation
        fields = ['account', 'reconciliation_date', 'bank_balance', 'notes']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-control'}),
            'reconciliation_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bank_balance': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reconciliation_date'].initial = timezone.now().date()
        
        # فلترة الحسابات البنكية التي تخضع للتسوية فقط
        self.fields['account'].queryset = Account.objects.filter(is_bank_reconciliation=True, is_active=True)


class CategoryForm(forms.ModelForm):
    """
    نموذج إضافة وتعديل فئة (مصروفات/إيرادات)
    """
    TYPE_CHOICES = (
        ('expense', 'مصروفات'),
        ('income', 'إيرادات'),
    )
    
    type = forms.ChoiceField(
        label='نوع الفئة',
        choices=TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Category
        fields = ['name', 'type', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تعيين القيم الافتراضية
        if not self.instance.pk:
            self.fields['is_active'].initial = True
        
        # جعل الاسم إجباري وإضافة رسائل الخطأ
        self.fields['name'].required = True
        self.fields['name'].error_messages = {
            'required': 'يرجى إدخال اسم الفئة'
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        type_value = self.cleaned_data.get('type')
        instance = getattr(self, 'instance', None)
        
        # التحقق من عدم تكرار الاسم في نفس النوع
        if name and type_value:
            qs = Category.objects.filter(name=name, type=type_value)
            if instance and instance.pk:
                qs = qs.exclude(pk=instance.pk)
            
            if qs.exists():
                raise forms.ValidationError(f"يوجد فئة بنفس الاسم '{name}' ونفس النوع. يرجى استخدام اسم آخر.")
        
        return name 