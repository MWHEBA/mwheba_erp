from django import forms
from django.core.exceptions import ValidationError
from .models import Purchase, PurchaseItem, PurchasePayment, PurchaseOrder, PurchaseOrderItem, PurchaseReturn, PurchaseReturnItem
from supplier.models import Supplier
from product.models import Product, Warehouse
from django.utils import timezone

class PurchaseOrderForm(forms.ModelForm):
    """
    نموذج إنشاء طلب شراء جديد
    """
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        label="المورد"
    )
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label="المستودع"
    )
    
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'warehouse', 'date', 'number', 'expected_date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'expected_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تعيين أول مستودع بشكل افتراضي
        warehouses = Warehouse.objects.filter(is_active=True)
        if warehouses.exists() and not self.initial.get('warehouse'):
            self.initial['warehouse'] = warehouses.first().pk
    
    def clean_number(self):
        number = self.cleaned_data.get('number')
        if not self.instance.pk and PurchaseOrder.objects.filter(number=number).exists():
            raise ValidationError('رقم الطلب موجود بالفعل')
        return number


class PurchaseOrderItemForm(forms.ModelForm):
    """
    نموذج إضافة عنصر لطلب الشراء
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label="المنتج"
    )
    
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'unit_price']
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError('الكمية يجب أن تكون أكبر من صفر')
        return quantity


class PurchaseForm(forms.ModelForm):
    """
    نموذج إنشاء فاتورة مشتريات جديدة
    """
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        label="المورد"
    )
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label="المستودع"
    )
    
    purchase_order = forms.ModelChoiceField(
        queryset=PurchaseOrder.objects.filter(status='pending'),
        label="طلب الشراء",
        required=False
    )
    
    class Meta:
        model = Purchase
        fields = ['supplier', 'warehouse', 'purchase_order', 'date', 'number', 'discount', 'payment_method', 'notes']
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
        if not self.instance.pk and Purchase.objects.filter(number=number).exists():
            raise ValidationError('رقم الفاتورة موجود بالفعل')
        return number
    
    def clean_discount(self):
        discount = self.cleaned_data.get('discount', 0)
        if discount < 0:
            raise ValidationError('لا يمكن أن يكون الخصم قيمة سالبة')
        return discount


class PurchaseUpdateForm(forms.ModelForm):
    """
    نموذج تعديل فاتورة المشتريات (فقط للبيانات الأساسية بدون البنود)
    """
    # إضافة حقول للعرض فقط
    supplier_display = forms.CharField(label="المورد", required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    warehouse_display = forms.CharField(label="المستودع", required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    tax = forms.DecimalField(label="الضريبة", required=False, min_value=0, initial=0, 
                            widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}))
    
    class Meta:
        model = Purchase
        fields = ['date', 'payment_method', 'discount', 'notes', 'number']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'number': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # لا نسمح بتعديل المورد أو المخزن بعد إنشاء الفاتورة
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
        
        # إذا كان هناك كائن موجود، نقوم بتعبئة حقول العرض فقط
        if self.instance and self.instance.pk:
            self.initial['supplier_display'] = self.instance.supplier.name if self.instance.supplier else ''
            self.initial['warehouse_display'] = self.instance.warehouse.name if self.instance.warehouse else ''
            
            # التأكد من توفير قيم افتراضية لحقلي discount و tax
            if 'discount' in self.fields and not self.initial.get('discount'):
                self.initial['discount'] = 0
            if 'tax' in self.fields and not self.initial.get('tax'):
                self.initial['tax'] = 0
    
    def clean_discount(self):
        discount = self.cleaned_data.get('discount', 0)
        if discount < 0:
            raise ValidationError('لا يمكن أن يكون الخصم قيمة سالبة')
        return discount
    
    def clean_tax(self):
        tax = self.cleaned_data.get('tax', 0)
        if tax is None:
            tax = 0
        elif tax < 0:
            raise ValidationError('لا يمكن أن تكون الضريبة قيمة سالبة')
        return tax


class PurchaseItemForm(forms.ModelForm):
    """
    نموذج إضافة عنصر لفاتورة المشتريات
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label="المنتج"
    )
    
    class Meta:
        model = PurchaseItem
        fields = ['product', 'quantity', 'unit_price']
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError('الكمية يجب أن تكون أكبر من صفر')
        return quantity


class PurchasePaymentForm(forms.ModelForm):
    """
    نموذج تسجيل دفعة على فاتورة المشتريات
    """
    class Meta:
        model = PurchasePayment
        fields = ['amount', 'payment_date', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.purchase = kwargs.pop('purchase', None)
        super().__init__(*args, **kwargs)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError('المبلغ يجب أن يكون أكبر من صفر')
        
        if self.purchase:
            # التحقق من أن المبلغ لا يتجاوز المبلغ المتبقي
            remaining = self.purchase.amount_due
            if amount > remaining:
                raise ValidationError(f'المبلغ يتجاوز المبلغ المتبقي ({remaining})')
        
        return amount 


class PurchaseReturnForm(forms.ModelForm):
    """
    نموذج مرتجع المشتريات
    """
    class Meta:
        model = PurchaseReturn
        fields = ['date', 'warehouse', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
        
        # تعيين التاريخ الحالي كقيمة افتراضية
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()
            
        # جعل حقل المخزن اختياري
        self.fields['warehouse'].required = False
        self.fields['notes'].required = False

class PurchaseReturnItemForm(forms.ModelForm):
    """
    نموذج بند مرتجع المشتريات
    """
    class Meta:
        model = PurchaseReturnItem
        fields = ['purchase_item', 'quantity', 'unit_price', 'discount', 'reason']
        widgets = {
            'reason': forms.TextInput(attrs={'placeholder': 'سبب الإرجاع'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['purchase_item'].queryset = PurchaseItem.objects.none()
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        purchase_item = self.cleaned_data.get('purchase_item')
        
        if quantity and purchase_item:
            if quantity > purchase_item.quantity:
                raise forms.ValidationError('الكمية المرتجعة لا يمكن أن تتجاوز الكمية المشتراة')
        
        return quantity 