# بيانات تجريبية للنظام

هذا المجلد يحتوي على ملفات البيانات التجريبية اللازمة لتهيئة النظام للاختبار والتطوير.

## قائمة ملفات البيانات التجريبية في النظام

### تطبيق المستخدمين (users)
- `users/fixtures/initial_data.json`: بيانات المستخدمين وسجلات النشاط
- `users/fixtures/groups.json`: مجموعات المستخدمين
- `users/fixtures/user_groups.json`: ربط المستخدمين بالمجموعات (استخدم الأمر المخصص بدلاً منه)

### تطبيق العملاء (client)
- `client/fixtures/initial_data.json`: بيانات العملاء

### تطبيق الموردين (supplier)
- `supplier/fixtures/initial_data.json`: بيانات الموردين

### تطبيق المنتجات (product)
- `product/fixtures/initial_data.json`: بيانات المنتجات والفئات والعلامات التجارية والمخازن والمخزون

### تطبيق المشتريات (purchase)
- `purchase/fixtures/initial_data.json`: بيانات فواتير المشتريات الأساسية
- `purchase/fixtures/initial_data_extra.json`: بيانات إضافية للمشتريات

### تطبيق المبيعات (sale)
- `sale/fixtures/initial_data.json`: بيانات فواتير المبيعات الأساسية
- `sale/fixtures/initial_data_extra.json`: بيانات إضافية للمبيعات

### تطبيق المالية (financial)
- `financial/fixtures/initial_data.json`: بيانات الحسابات والمعاملات المالية

### تطبيق النظام الأساسي (core)
- `core/fixtures/initial_data.json`: إعدادات النظام والإحصائيات والإشعارات

## كيفية تحميل البيانات التجريبية

يمكن تحميل جميع البيانات التجريبية باستخدام الأمر التالي:

```bash
# تحميل البيانات الأساسية أولاً
python manage.py loaddata users/fixtures/initial_data.json
python manage.py loaddata users/fixtures/groups.json

# ربط المستخدمين بالمجموعات
python manage.py add_user_groups

# تحميل باقي البيانات
python manage.py loaddata client/fixtures/initial_data.json
python manage.py loaddata supplier/fixtures/initial_data.json
python manage.py loaddata product/fixtures/initial_data.json
python manage.py loaddata financial/fixtures/initial_data.json
python manage.py loaddata purchase/fixtures/initial_data.json
python manage.py loaddata sale/fixtures/initial_data.json
python manage.py loaddata core/fixtures/initial_data.json

# تحميل البيانات الإضافية
python manage.py loaddata purchase/fixtures/initial_data_extra.json
python manage.py loaddata sale/fixtures/initial_data_extra.json
```

## نظرة عامة على البيانات

### المستخدمين
تتضمن بيانات المستخدمين 6 مستخدمين مختلفين بأدوار متنوعة:
- مدير النظام
- محاسب
- مدير مخزون
- مندوبي مبيعات (2)
- مستخدم غير نشط

### المخازن
تتضمن البيانات 3 مخازن مختلفة:
- المخزن الرئيسي (القاهرة)
- مخزن الفرع (الإسكندرية)
- مخزن الأجهزة (القاهرة)

### المنتجات
تتضمن البيانات 7 منتجات أساسية مختلفة:
- هواتف ذكية
- ملابس متنوعة
- أجهزة كهربائية
- أثاث

### فواتير المبيعات
تتضمن بيانات المبيعات 10 فواتير متنوعة:
- 5 فواتير أساسية
- 5 فواتير إضافية
- مدفوعات متنوعة (كاملة، جزئية، غير مدفوعة)
- 5 حالات مرتجعات مبيعات

### فواتير المشتريات
تتضمن بيانات المشتريات 10 فواتير متنوعة:
- 5 فواتير أساسية
- 5 فواتير إضافية
- مدفوعات متنوعة (كاملة، جزئية، غير مدفوعة)
- 5 حالات مرتجعات مشتريات
- 2 طلبات شراء

### الإحصائيات وإعدادات النظام
تتضمن بيانات التطبيق الأساسي:
- 10 إعدادات نظام متنوعة
- 4 إحصائيات للوحة التحكم
- 4 إشعارات متنوعة للمستخدمين 