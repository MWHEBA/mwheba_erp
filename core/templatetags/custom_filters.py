from django import template
from decimal import Decimal, ROUND_HALF_UP
import json
from django.utils.safestring import mark_safe
from django.template.defaultfilters import floatformat
import locale

register = template.Library()

@register.filter
def custom_number_format(value, decimals=2):
    """
    تنسيق الأرقام بالشكل المطلوب:
    - علامة عشرية واحدة فقط إذا كانت هناك كسور
    - بدون علامة عشرية إذا كان العدد صحيح
    - فاصلة لكل ألف
    """
    if value is None:
        return "0"
    
    try:
        value = float(value)
        formatted = "{:,.{prec}f}".format(value, prec=decimals)
        
        # إذا كانت القيمة عدد صحيح، نعرضها بدون علامة عشرية
        if value == int(value):
            formatted = "{:,}".format(int(value))
            
        return formatted
    except (ValueError, TypeError):
        return value

@register.filter
def custom_load_json(json_string):
    """
    تحويل سلسلة JSON إلى كائن بايثون
    استخدام: {{ json_string|custom_load_json }}
    """
    try:
        if isinstance(json_string, str):
            return json.loads(json_string)
        return json_string
    except json.JSONDecodeError:
        return [] 

@register.filter
def format_phone(value):
    """
    تنسيق رقم الهاتف بطريقة صحيحة دون معاملته كرقم عُملة
    مع ضبط الاتجاه من اليسار إلى اليمين
    """
    if value is None or value == '':
        return "-"
    
    # إزالة أي علامات تنسيق أضيفت بالخطأ
    phone = str(value).replace(',', '').replace('.', '').strip()
    
    # تنسيق الرقم حسب الطول
    if len(phone) == 11 and phone.startswith('01'):  # أرقام مصرية
        formatted = f"{phone[:3]} {phone[3:7]} {phone[7:]}"
    elif len(phone) > 10:  # أرقام دولية طويلة
        if phone.startswith('+'):
            country_code = phone[:3]  # رمز الدولة مع +
            rest = phone[3:]
            formatted = f"{country_code} {rest}"
        else:
            formatted = phone
    else:
        formatted = phone
    
    # إضافة وسم direction لضبط اتجاه النص من اليسار إلى اليمين وجعله آمن
    return mark_safe(f'<span dir="ltr" style="display:inline-block; text-align:left;">{formatted}</span>')

# الفلاتر المضافة من تطبيق product

@register.filter
def divide(value, arg):
    """قسمة القيمة الأولى على القيمة الثانية"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def div(value, arg):
    """مرادف لفلتر divide للتوافق"""
    return divide(value, arg)

@register.filter
def multiply(value, arg):
    """ضرب القيمة الأولى في القيمة الثانية"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0

@register.filter
def mul(value, arg):
    """مرادف لفلتر multiply للتوافق"""
    return multiply(value, arg)

@register.filter
def subtract(value, arg):
    """طرح القيمة الثانية من القيمة الأولى"""
    try:
        return float(value) - float(arg)
    except ValueError:
        return 0

@register.filter
def add_float(value, arg):
    """جمع القيمة الأولى مع القيمة الثانية"""
    try:
        return float(value) + float(arg)
    except ValueError:
        return 0

@register.filter
def percentage(value, arg):
    """حساب النسبة المئوية للقيمة الأولى من القيمة الثانية"""
    try:
        return (float(value) / float(arg)) * 100
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def get_attr(obj, attr):
    """
    الحصول على قيمة سمة من كائن باستخدام اسم السمة
    يدعم أيضًا معالجة الكائنات المتداخلة باستخدام النقاط في سلسلة السمة
    مثال: {{ object|get_attr:"user.name" }}
    """
    if obj is None:
        return ""
    
    if "." in attr:
        # تقسيم السمة بالنقط للوصول إلى السمات المتداخلة
        parts = attr.split(".")
        result = obj
        for part in parts:
            if result is None:
                return ""
            
            # محاولة تنفيذ تابع بدون وسيطات إذا كان
            if callable(getattr(result, part, None)):
                result = getattr(result, part)()
            else:
                result = getattr(result, part, "")
        
        return result
    else:
        # محاولة تنفيذ تابع بدون وسيطات إذا كان
        attr_value = getattr(obj, attr, "")
        if callable(attr_value):
            return attr_value()
        return attr_value

@register.filter
def call(obj, method_name):
    """
    استدعاء طريقة (تابع) من كائن باسم التابع
    مثال: {{ object|call:"get_absolute_url" }}
    """
    if obj is None:
        return ""
    
    method = getattr(obj, method_name, None)
    if callable(method):
        return method()
    return ""

@register.filter
def replace_id(url, obj_id):
    """
    استبدال '{id}' أو '{pk}' بقيمة محددة في URL
    مثال: {{ "product/{id}/edit"|replace_id:product.id }}
    """
    if url is None or obj_id is None:
        return ""
    
    return str(url).replace('{id}', str(obj_id)).replace('{pk}', str(obj_id))

@register.filter
def split(value, sep):
    """
    تقسيم سلسلة نصية بناءً على فاصل معين وإرجاع قائمة
    مثال: {{ "10,25,50,100"|split:"," }}
    """
    if value is None:
        return []
    return str(value).split(sep)

@register.filter
def to_int(value, default=0):
    """
    تحويل قيمة إلى عدد صحيح
    مثال: {{ "15"|to_int }}
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

@register.filter
def to_float(value, default=0.0):
    """
    تحويل قيمة إلى عدد عشري
    مثال: {{ "15.5"|to_float }}
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

@register.filter
def format_table_cell(value, format_type):
    """
    تنسيق خلية في جدول حسب نوع التنسيق
    يستخدم: {{ value|format_table_cell:"currency" }}
    """
    if value is None:
        return "-"
    
    if format_type == 'currency':
        return f"{custom_number_format(value)} ج.م"
    elif format_type == 'date':
        return value.strftime('%Y-%m-%d') if value else "-"
    elif format_type == 'datetime':
        return value.strftime('%Y-%m-%d %H:%M') if value else "-"
    elif format_type == 'boolean':
        return "نعم" if value else "لا"
    elif format_type == 'percentage':
        return f"{custom_number_format(value, 1)}%"
    else:
        return value 