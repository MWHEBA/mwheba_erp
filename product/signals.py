from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone
from decimal import Decimal
from .models import StockMovement, Stock, Product, ProductImage
from sale.models import Sale
from purchase.models import Purchase


@receiver(pre_save, sender=Product)
def ensure_unique_sku(sender, instance, **kwargs):
    """
    التأكد من أن الـ SKU فريد وإنشاءه تلقائيًا إذا لم يتم توفيره
    """
    if not instance.sku:
        # إنشاء sku فريد من اسم المنتج والوقت
        timestamp = timezone.now().strftime('%y%m%d%H%M')
        base_slug = slugify(instance.name)[:10]
        instance.sku = f"{base_slug}-{timestamp}"


@receiver(post_save, sender=ProductImage)
def ensure_single_primary_image(sender, instance, created, **kwargs):
    """
    التأكد من وجود صورة رئيسية واحدة فقط لكل منتج
    """
    if instance.is_primary:
        # إذا تم تعيين هذه الصورة كصورة رئيسية، قم بإلغاء تعيين أي صور أخرى كصور رئيسية
        ProductImage.objects.filter(
            product=instance.product,
            is_primary=True
        ).exclude(pk=instance.pk).update(is_primary=False)
    else:
        # إذا لم تكن هناك صورة رئيسية للمنتج، قم بتعيين أول صورة كصورة رئيسية
        if not ProductImage.objects.filter(product=instance.product, is_primary=True).exists():
            instance.is_primary = True
            instance.save()


@receiver(post_save, sender=StockMovement)
def update_stock_on_movement(sender, instance, created, **kwargs):
    """
    تحديث المخزون بعد حفظ حركة المخزون
    """
    # تجنب تحديث المخزون عدة مرات لنفس الفاتورة
    # نقوم بتحديث المخزون فقط عند إنشاء حركة جديدة
    if created:
        # تحقق ما إذا كان هناك متغير خاص بالأمان في الكوكيز - إذا كان موجودًا فلا تقم بتحديث المخزون
        if hasattr(instance, '_skip_update') and instance._skip_update:
            return
        
        # تأشير هذه الحركة لمنع تحديثها مرة أخرى
        instance._skip_update = True
        
        # الحصول على المخزون الحالي أو إنشاء واحد جديد إذا لم يكن موجودًا
        stock, created_stock = Stock.objects.get_or_create(
            product=instance.product,
            warehouse=instance.warehouse,
            defaults={'quantity': Decimal('0')}
        )
        
        # تحديث المخزون بناءً على نوع الحركة
        if instance.movement_type == 'in':
            # حركة إضافة للمخزون
            stock.quantity += Decimal(instance.quantity)
        elif instance.movement_type == 'out':
            # حركة سحب من المخزون (لا تسمح بالقيم السالبة)
            stock.quantity = max(Decimal('0'), stock.quantity - Decimal(instance.quantity))
        elif instance.movement_type == 'transfer' and instance.destination_warehouse:
            # حركة تحويل بين المخازن
            # خفض المخزون من المخزن المصدر
            stock.quantity = max(Decimal('0'), stock.quantity - Decimal(instance.quantity))
            
            # زيادة المخزون في المخزن الوجهة
            dest_stock, dest_created = Stock.objects.get_or_create(
                product=instance.product,
                warehouse=instance.destination_warehouse,
                defaults={'quantity': Decimal('0')}
            )
            dest_stock.quantity += Decimal(instance.quantity)
            dest_stock.save()
        elif instance.movement_type == 'adjustment':
            # حركة تسوية المخزون (تحديد كمية مطلقة)
            stock.quantity = Decimal(instance.quantity)
        
        # حفظ التغييرات على المخزون
        stock.save()


@receiver(post_delete, sender=StockMovement)
def revert_stock_on_movement_delete(sender, instance, **kwargs):
    """
    إلغاء تأثير حركة المخزون عند حذفها
    """
    try:
        # البحث عن سجل المخزون المرتبط
        stock = Stock.objects.get(product=instance.product, warehouse=instance.warehouse)
        
        if instance.movement_type == 'in':
            # إلغاء تأثير الإضافة - خفض المخزون
            stock.quantity = max(Decimal('0'), stock.quantity - Decimal(instance.quantity))
        elif instance.movement_type == 'out':
            # إلغاء تأثير السحب - زيادة المخزون
            stock.quantity += Decimal(instance.quantity)
        elif instance.movement_type == 'transfer':
            # إلغاء تأثير التحويل
            stock.quantity += Decimal(instance.quantity)
            
            # معالجة المخزن المستلم إذا كان موجودًا
            if instance.destination_warehouse:
                try:
                    dest_stock = Stock.objects.get(
                        product=instance.product, 
                        warehouse=instance.destination_warehouse
                    )
                    dest_stock.quantity = max(Decimal('0'), dest_stock.quantity - Decimal(instance.quantity))
                    dest_stock.save()
                except Stock.DoesNotExist:
                    pass
        
        # حفظ التغييرات على المخزون
        stock.save()
    except Stock.DoesNotExist:
        # إذا لم يكن هناك سجل مخزون، فلا يوجد شيء للتعديل
        pass


@receiver(post_delete, sender=Sale)
def handle_sale_delete(sender, instance, **kwargs):
    """
    معالجة حذف فاتورة المبيعات
    """
    # لا نقوم بإعادة تعيين الرقم التسلسلي عند الحذف
    pass


@receiver(post_delete, sender=Purchase)
def handle_purchase_delete(sender, instance, **kwargs):
    """
    معالجة حذف فاتورة المشتريات
    """
    # لا نقوم بإعادة تعيين الرقم التسلسلي عند الحذف
    pass


@receiver(post_delete, sender=StockMovement)
def handle_stock_movement_delete(sender, instance, **kwargs):
    """
    معالجة حذف حركة المخزون
    """
    # لا نقوم بإعادة تعيين الرقم التسلسلي عند الحذف
    pass 