from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator


class Customer(models.Model):
    """
    نموذج العميل
    """
    name = models.CharField(_('اسم العميل'), max_length=255)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("يجب أن يكون رقم الهاتف بالصيغة: '+999999999'. يسمح بـ 15 رقم كحد أقصى.")
    )
    phone = models.CharField(_('رقم الهاتف'), validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(_('العنوان'), blank=True, null=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True, null=True)
    code = models.CharField(_('كود العميل'), max_length=20, unique=True)
    credit_limit = models.DecimalField(_('الحد الائتماني'), max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(_('الرصيد الحالي'), max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=50, blank=True, null=True)
    notes = models.TextField(_('ملاحظات'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'),
                                   related_name='customers_created', null=True)
    
    class Meta:
        verbose_name = _('عميل')
        verbose_name_plural = _('العملاء')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def available_credit(self):
        """
        حساب الرصيد المتاح
        """
        return self.credit_limit - self.balance


class CustomerPayment(models.Model):
    """
    نموذج لتسجيل المدفوعات المستلمة من العملاء
    """
    PAYMENT_METHODS = (
        ('cash', _('نقدي')),
        ('bank_transfer', _('تحويل بنكي')),
        ('check', _('شيك')),
    )
    
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name=_('العميل'),
                                 related_name='payments')
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    payment_date = models.DateField(_('تاريخ الدفع'))
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(_('رقم المرجع'), max_length=50, blank=True, null=True)
    notes = models.TextField(_('ملاحظات'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'),
                                   related_name='customer_payments_created', null=True)
    
    class Meta:
        verbose_name = _('مدفوعات العميل')
        verbose_name_plural = _('مدفوعات العملاء')
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.customer} - {self.amount} - {self.payment_date}"
