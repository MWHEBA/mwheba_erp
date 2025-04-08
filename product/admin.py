from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Category, Product, Warehouse, Stock, StockMovement,
    Brand, Unit, ProductImage, ProductVariant
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    إدارة فئات المنتجات
    """
    list_display = ('name', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """
    إدارة العلامات التجارية
    """
    list_display = ('name', 'website', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description', 'website')


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    """
    إدارة وحدات القياس
    """
    list_display = ('name', 'symbol', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'symbol')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    إدارة المنتجات
    """
    list_display = ('name', 'sku', 'barcode', 'category', 'brand', 'cost_price', 'selling_price', 
                   'current_stock', 'profit_margin', 'is_active')
    list_filter = ('category', 'brand', 'is_active', 'is_featured')
    search_fields = ('name', 'sku', 'barcode', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fieldsets = (
        (None, {'fields': ('name', 'sku', 'barcode', 'category', 'brand', 'unit')}),
        (_('التسعير'), {'fields': ('cost_price', 'selling_price', 'tax_rate', 'discount_rate')}),
        (_('المخزون'), {'fields': ('min_stock', 'max_stock')}),
        (_('معلومات إضافية'), {'fields': ('description', 'is_active', 'is_featured')}),
        (_('معلومات النظام'), {'fields': ('created_at', 'updated_at', 'created_by')}),
    )
    
    def current_stock(self, obj):
        return obj.current_stock
    current_stock.short_description = _('المخزون الحالي')
    
    def profit_margin(self, obj):
        return f"{obj.profit_margin:.2f}%"
    profit_margin.short_description = _('هامش الربح')
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    إدارة صور المنتجات
    """
    list_display = ('product', 'image', 'is_primary', 'alt_text', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'product__sku', 'alt_text')
    

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    إدارة متغيرات المنتجات
    """
    list_display = ('product', 'name', 'sku', 'cost_price', 'selling_price', 'stock', 'is_active')
    list_filter = ('is_active', 'product')
    search_fields = ('product__name', 'name', 'sku', 'barcode')


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    """
    إدارة المستودعات
    """
    list_display = ('name', 'code', 'location', 'manager', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'location')
    

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """
    إدارة المخزون
    """
    list_display = ('product', 'warehouse', 'quantity', 'updated_at')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku', 'warehouse__name')
    readonly_fields = ('updated_at',)
    

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """
    إدارة حركات المخزون
    """
    list_display = ('product', 'movement_type', 'warehouse', 'quantity', 'timestamp', 'created_by')
    list_filter = ('movement_type', 'warehouse', 'timestamp')
    search_fields = ('product__name', 'product__sku', 'reference_number', 'notes')
    readonly_fields = ('timestamp', 'created_by')
    fieldsets = (
        (None, {'fields': ('product', 'warehouse', 'movement_type', 'quantity')}),
        (_('معلومات إضافية'), {'fields': ('reference_number', 'notes', 'destination_warehouse')}),
        (_('معلومات النظام'), {'fields': ('timestamp', 'created_by')}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
