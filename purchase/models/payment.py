from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class PurchasePayment(models.Model):
    """
    نموذج مدفوعات فواتير المشتريات
    """
    PAYMENT_METHODS = (
        ('cash', _('نقدي')),
        ('bank_transfer', _('تحويل بنكي')),
        ('check', _('شيك')),
    )
    
    purchase = models.ForeignKey('purchase.Purchase', on_delete=models.CASCADE, verbose_name=_('الفاتورة'), related_name='payments')
    amount = models.DecimalField(_('المبلغ'), max_digits=12, decimal_places=2)
    payment_date = models.DateField(_('تاريخ الدفع'))
    payment_method = models.CharField(_('طريقة الدفع'), max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(_('رقم المرجع'), max_length=50, blank=True, null=True)
    notes = models.TextField(_('ملاحظات'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 verbose_name=_('أنشئ بواسطة'), related_name='purchase_payments_created')
    # حقل للإشارة إلى المعاملة المالية المرتبطة
    financial_transaction = models.ForeignKey('financial.Transaction', on_delete=models.SET_NULL, 
                                             null=True, blank=True, verbose_name=_('المعاملة المالية'))
    
    class Meta:
        verbose_name = _('دفعة الفاتورة')
        verbose_name_plural = _('دفعات الفواتير')
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.purchase} - {self.amount} - {self.payment_date}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # تحديث حالة الدفع للفاتورة
        if self.purchase:
            self.purchase.update_payment_status() 