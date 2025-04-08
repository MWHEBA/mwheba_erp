from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Supplier, SupplierPayment


class SupplierForm(forms.ModelForm):
    """
    نموذج إضافة وتعديل المورد
    """
    class Meta:
        model = Supplier
        fields = [
            'name', 'phone', 'address', 'email', 'code', 
            'contact_person', 'tax_number', 'is_active', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_code(self):
        """
        التحقق من أن كود المورد فريد
        """
        code = self.cleaned_data.get('code')
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # في حالة التعديل، نتحقق فقط إذا تم تغيير الكود
            if Supplier.objects.exclude(pk=instance.pk).filter(code=code).exists():
                raise forms.ValidationError(_('هذا الكود مستخدم من قبل، الرجاء استخدام كود آخر'))
        else:
            # في حالة الإضافة الجديدة
            if Supplier.objects.filter(code=code).exists():
                raise forms.ValidationError(_('هذا الكود مستخدم من قبل، الرجاء استخدام كود آخر'))
        return code


class SupplierPaymentForm(forms.ModelForm):
    """
    نموذج إضافة مدفوعات للمورد
    """
    class Meta:
        model = SupplierPayment
        fields = [
            'supplier', 'amount', 'payment_date', 'payment_method', 
            'reference_number', 'notes'
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control select2'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        } 