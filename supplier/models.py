from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator


class Supplier(models.Model):
    """
    نموذج المورد
    """
    name = models.CharField(_('اسم المورد'), max_length=255)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("يجب أن يكون رقم الهاتف بالصيغة: '+999999999'. يسمح بـ 15 رقم كحد أقصى.")
    )
    phone = models.CharField(_('رقم الهاتف'), validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(_('العنوان'), blank=True, null=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True, null=True)
    code = models.CharField(_('كود المورد'), max_length=20, unique=True)
    contact_person = models.CharField(_('الشخص المسؤول'), max_length=255, blank=True, null=True)
    balance = models.DecimalField(_('الرصيد الحالي'), max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=50, blank=True, null=True)
    notes = models.TextField(_('ملاحظات'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'),
                                   related_name='suppliers_created', null=True)
    
    class Meta:
        verbose_name = _('مورد')
        verbose_name_plural = _('الموردين')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class SupplierPayment(models.Model):
    """
    نموذج لتسجيل المدفوعات المدفوعة للموردين
    """
    PAYMENT_METHODS = (
        ('cash', _('نقدي')),
        ('bank_transfer', _('تحويل بنكي')),
        ('check', _('شيك')),
    )
    
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, verbose_name=_('المورد'),
                                 related_name='payments')
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    payment_date = models.DateField(_('تاريخ الدفع'))
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(_('رقم المرجع'), max_length=50, blank=True, null=True)
    notes = models.TextField(_('ملاحظات'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'),
                                   related_name='supplier_payments_created', null=True)
    
    class Meta:
        verbose_name = _('مدفوعات المورد')
        verbose_name_plural = _('مدفوعات الموردين')
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.supplier} - {self.amount} - {self.payment_date}"
