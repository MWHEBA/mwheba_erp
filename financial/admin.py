from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Account, Transaction, TransactionLine, Expense, Income, BankReconciliation


class TransactionLineInline(admin.TabularInline):
    """
    عرض بنود المعاملة المالية ضمن صفحة المعاملة
    """
    model = TransactionLine
    extra = 2
    min_num = 2
    fields = ('account', 'debit', 'credit', 'description')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """
    إدارة الحسابات المالية
    """
    list_display = ('name', 'code', 'account_type', 'parent', 'balance', 'is_active')
    list_filter = ('account_type', 'is_active', 'is_bank_reconciliation')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('balance', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('name', 'code', 'account_type', 'parent')}),
        (_('معلومات إضافية'), {'fields': ('description', 'balance', 'is_active', 'is_bank_reconciliation')}),
        (_('معلومات النظام'), {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    إدارة المعاملات المالية
    """
    list_display = ('id', 'date', 'transaction_type', 'amount', 'reference', 'is_reconciled')
    list_filter = ('transaction_type', 'date', 'is_reconciled')
    search_fields = ('reference', 'description')
    readonly_fields = ('created_at', 'created_by')
    inlines = [TransactionLineInline]
    fieldsets = (
        (None, {'fields': ('date', 'transaction_type', 'amount', 'reference')}),
        (_('معلومات إضافية'), {'fields': ('description', 'is_reconciled')}),
        (_('معلومات النظام'), {'fields': ('created_at', 'created_by')}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        
        # حفظ العناصر الجديدة أو المعدلة
        for instance in instances:
            instance.save()
        
        # حذف العناصر المحذوفة
        for obj in formset.deleted_objects:
            obj.delete()
            
        formset.save_m2m()
        
        # التأكد من أن مجموع المدين يساوي مجموع الدائن
        self.verify_transaction_balance(form.instance)
    
    def verify_transaction_balance(self, transaction):
        """
        التحقق من توازن المعاملة المالية (مجموع المدين = مجموع الدائن)
        """
        from django.db.models import Sum
        from django.contrib import messages
        
        total_debit = transaction.lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = transaction.lines.aggregate(Sum('credit'))['credit__sum'] or 0
        
        if total_debit != total_credit:
            # تسجيل الخطأ في سجل النظام
            error_message = f"عدم توازن القيد المحاسبي: المعاملة {transaction.id} - المدين: {total_debit} - الدائن: {total_credit} - الفرق: {total_debit - total_credit}"
            
            # تصحيح الخلل تلقائيًا إذا كان الفرق بسيطًا (مثلًا بسبب التقريب)
            if abs(total_debit - total_credit) < 0.01:
                # تحديث آخر قيد لتصحيح الفرق
                last_line = transaction.lines.last()
                if total_debit > total_credit:
                    last_line.credit += (total_debit - total_credit)
                else:
                    last_line.debit += (total_credit - total_debit)
                last_line.save(update_fields=['debit', 'credit'])
                
                transaction.description += "\n(تم تصحيح فرق تقريب بسيط)"
                transaction.save(update_fields=['description'])
            else:
                # إضافة علامة للمعاملة تشير إلى وجود خلل
                transaction.is_reconciled = False
                transaction.description += "\n!!! قيد غير متوازن - يرجى المراجعة !!!"
                transaction.save(update_fields=['is_reconciled', 'description'])


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """
    إدارة المصروفات
    """
    list_display = ('date', 'account', 'payment_account', 'amount', 'reference')
    list_filter = ('date', 'account', 'payment_account')
    search_fields = ('reference', 'description')
    readonly_fields = ('transaction', 'created_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('date', 'account', 'payment_account', 'amount', 'reference')}),
        (_('معلومات إضافية'), {'fields': ('description',)}),
        (_('معلومات النظام'), {'fields': ('transaction', 'created_at', 'created_by')}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
            
            # إنشاء معاملة مالية تلقائيًا عند إنشاء مصروف جديد
            if not obj.transaction:
                transaction = Transaction.objects.create(
                    date=obj.date,
                    transaction_type='expense',
                    amount=obj.amount,
                    reference=obj.reference,
                    description=obj.description,
                    created_by=request.user
                )
                obj.transaction = transaction
                
                # إنشاء بنود المعاملة
                # مدين: حساب المصروف
                TransactionLine.objects.create(
                    transaction=transaction,
                    account=obj.account,
                    debit=obj.amount,
                    credit=0,
                    description=obj.description
                )
                
                # دائن: حساب الدفع
                TransactionLine.objects.create(
                    transaction=transaction,
                    account=obj.payment_account,
                    debit=0,
                    credit=obj.amount,
                    description=obj.description
                )
                
                # تحديث رصيد الحسابات
                obj.account.balance += obj.amount
                obj.account.save(update_fields=['balance'])
                
                obj.payment_account.balance -= obj.amount
                obj.payment_account.save(update_fields=['balance'])
                
        super().save_model(request, obj, form, change)


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    """
    إدارة الإيرادات
    """
    list_display = ('date', 'account', 'receiving_account', 'amount', 'reference')
    list_filter = ('date', 'account', 'receiving_account')
    search_fields = ('reference', 'description')
    readonly_fields = ('transaction', 'created_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('date', 'account', 'receiving_account', 'amount', 'reference')}),
        (_('معلومات إضافية'), {'fields': ('description',)}),
        (_('معلومات النظام'), {'fields': ('transaction', 'created_at', 'created_by')}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
            
            # إنشاء معاملة مالية تلقائيًا عند إنشاء إيراد جديد
            if not obj.transaction:
                transaction = Transaction.objects.create(
                    date=obj.date,
                    transaction_type='income',
                    amount=obj.amount,
                    reference=obj.reference,
                    description=obj.description,
                    created_by=request.user
                )
                obj.transaction = transaction
                
                # إنشاء بنود المعاملة
                # مدين: حساب الاستلام
                TransactionLine.objects.create(
                    transaction=transaction,
                    account=obj.receiving_account,
                    debit=obj.amount,
                    credit=0,
                    description=obj.description
                )
                
                # دائن: حساب الإيراد
                TransactionLine.objects.create(
                    transaction=transaction,
                    account=obj.account,
                    debit=0,
                    credit=obj.amount,
                    description=obj.description
                )
                
                # تحديث رصيد الحسابات
                obj.receiving_account.balance += obj.amount
                obj.receiving_account.save(update_fields=['balance'])
                
                obj.account.balance += obj.amount
                obj.account.save(update_fields=['balance'])
                
        super().save_model(request, obj, form, change)


@admin.register(BankReconciliation)
class BankReconciliationAdmin(admin.ModelAdmin):
    """
    إدارة التسويات البنكية
    """
    list_display = ('account', 'reconciliation_date', 'system_balance', 'bank_balance', 'difference')
    list_filter = ('account', 'reconciliation_date')
    search_fields = ('account__name', 'notes')
    readonly_fields = ('system_balance', 'difference', 'created_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('account', 'reconciliation_date', 'bank_balance')}),
        (_('معلومات النظام'), {'fields': ('system_balance', 'difference', 'created_at', 'created_by')}),
        (_('ملاحظات'), {'fields': ('notes',)}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
            obj.system_balance = obj.account.balance
            obj.difference = obj.bank_balance - obj.system_balance
        
        super().save_model(request, obj, form, change)
