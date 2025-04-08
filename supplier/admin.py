from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Supplier, SupplierPayment


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    إعدادات عرض نموذج المورد في لوحة الإدارة
    """
    list_display = ('name', 'code', 'phone', 'email', 'contact_person', 'balance', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'phone', 'email', 'contact_person')
    readonly_fields = ('balance', 'created_at', 'updated_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('name', 'code', 'phone', 'email', 'address')}),
        (_('معلومات إضافية'), {'fields': ('contact_person', 'tax_number')}),
        (_('المعلومات المالية'), {'fields': ('balance',)}),
        (_('إعدادات أخرى'), {'fields': ('is_active', 'notes')}),
        (_('معلومات النظام'), {'fields': ('created_at', 'updated_at', 'created_by')}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    """
    إعدادات عرض نموذج مدفوعات المورد في لوحة الإدارة
    """
    list_display = ('supplier', 'amount', 'payment_date', 'payment_method', 'reference_number')
    list_filter = ('payment_date', 'payment_method')
    search_fields = ('supplier__name', 'reference_number', 'notes')
    raw_id_fields = ('supplier',)
    readonly_fields = ('created_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('supplier', 'amount', 'payment_date', 'payment_method')}),
        (_('معلومات إضافية'), {'fields': ('reference_number', 'notes')}),
        (_('معلومات النظام'), {'fields': ('created_at', 'created_by')}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
