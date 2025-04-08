from django import forms
from django.core.exceptions import ValidationError
from .models import Sale, SaleItem, SalePayment, SaleReturn, SaleReturnItem
from client.models import Customer
from product.models import Product, Stock, Warehouse
from django.db import models

class SaleForm(forms.ModelForm):
    """
    نموذج إنشاء فاتورة مبيعات جديدة
    """
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(is_active=True),
        label="العميل"
    )
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label="المستودع"
    )
    
    class Meta:
        model = Sale
        fields = ['customer', 'warehouse', 'date', 'number', 'discount', 'payment_method', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تعيين أول مستودع بشكل افتراضي
        warehouses = Warehouse.objects.filter(is_active=True)
        if warehouses.exists() and not self.initial.get('warehouse'):
            self.initial['warehouse'] = warehouses.first().pk
        
        # تعيين طريقة الدفع "نقدي" بشكل افتراضي
        if not self.initial.get('payment_method'):
            self.initial['payment_method'] = 'cash'
    
    def clean_number(self):
        number = self.cleaned_data.get('number')
        if not self.instance.pk and Sale.objects.filter(number=number).exists():
            raise ValidationError('رقم الفاتورة موجود بالفعل')
        return number
    
    def clean_discount(self):
        discount = self.cleaned_data.get('discount', 0)
        if discount < 0:
            raise ValidationError('لا يمكن أن يكون الخصم قيمة سالبة')
        return discount


class SaleItemForm(forms.ModelForm):
    """
    نموذج إضافة عنصر لفاتورة المبيعات
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label="المنتج"
    )
    
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price']
    
    def __init__(self, *args, **kwargs):
        self.warehouse = kwargs.pop('warehouse', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if not product or not quantity or not self.warehouse:
            return cleaned_data
        
        # التحقق من توفر المخزون الكافي
        available_stock = Stock.objects.filter(
            product=product,
            warehouse=self.warehouse
        ).aggregate(total=models.Sum('quantity')).get('total') or 0
        
        if quantity > available_stock:
            raise ValidationError(
                f'الكمية المتوفرة من {product.name} في المستودع هي {available_stock} فقط'
            )
        
        return cleaned_data


class SalePaymentForm(forms.ModelForm):
    """
    نموذج تسجيل دفعة على فاتورة المبيعات
    """
    class Meta:
        model = SalePayment
        fields = ['amount', 'payment_date', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.sale = kwargs.pop('sale', None)
        super().__init__(*args, **kwargs)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError('المبلغ يجب أن يكون أكبر من صفر')
        
        if self.sale:
            # التحقق من أن المبلغ لا يتجاوز المبلغ المتبقي
            remaining = self.sale.amount_due
            if amount > remaining:
                raise ValidationError(f'المبلغ يتجاوز المبلغ المتبقي ({remaining})')
        
        return amount 


class SaleReturnForm(forms.ModelForm):
    """
    نموذج مرتجع المبيعات
    """
    class Meta:
        model = SaleReturn
        fields = ['date', 'warehouse', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class SaleReturnItemForm(forms.ModelForm):
    """
    نموذج بند مرتجع المبيعات
    """
    class Meta:
        model = SaleReturnItem
        fields = ['sale_item', 'quantity', 'unit_price', 'discount', 'reason']
        widgets = {
            'reason': forms.TextInput(attrs={'placeholder': 'سبب الإرجاع'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sale_item'].queryset = SaleItem.objects.none()
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        sale_item = self.cleaned_data.get('sale_item')
        
        if quantity and sale_item:
            if quantity > sale_item.quantity:
                raise forms.ValidationError('الكمية المرتجعة لا يمكن أن تتجاوز الكمية المباعة')
        
        return quantity 