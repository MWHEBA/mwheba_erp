# MWHEBA_ERP - نظام إدارة الموارد المؤسسية

نظام متكامل لإدارة موارد المؤسسات يشمل إدارة المالية، المخزون، المبيعات، المشتريات وأكثر.

## المميزات الرئيسية

- إدارة المعاملات المالية
- إدارة الحسابات والميزانيات
- إدارة المخزون والمنتجات
- إدارة العملاء والموردين
- إدارة المبيعات والمشتريات
- التقارير والإحصائيات

## المكونات والأنظمة

### نظام الجداول الموحد (تحديث جديد)

تم تطوير نظام موحد لعرض جداول البيانات في التطبيق بتنسيق متناسق ومتجاوب. يتكون النظام من:

- قالب موحد لعرض البيانات: `templates/components/data_table.html`
- تنسيقات CSS موحدة: `static/css/tables.css`
- وظائف جافاسكريبت للتفاعل: `static/js/global-table.js`

المميزات الرئيسية:
- تصميم متناسق لكافة الجداول في النظام
- دعم الترتيب والفلترة والبحث
- تنسيق تلقائي للحقول (تاريخ، عملة، صور، إلخ)
- دعم الصفحات وعدد العناصر المعروضة
- إمكانية تصدير البيانات إلى Excel وPDF
- توافق مع الأجهزة المختلفة (تصميم متجاوب)

للمزيد من المعلومات، راجع [وثائق نظام الجداول](docs/tables_system.md)

## التثبيت والإعداد

### المتطلبات

- Python 3.8+
- Django 3.2+
- PostgreSQL 12+

### خطوات التثبيت

1. استنساخ المستودع:
```
git clone https://github.com/username/MWHEBA_ERP.git
cd MWHEBA_ERP
```

2. إنشاء البيئة الافتراضية:
```
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. تثبيت التبعيات:
```
pip install -r requirements.txt
```

4. إعداد ملف البيئة:
```
cp .env.example .env
# قم بتعديل ملف .env بإعدادات قاعدة البيانات وإعدادات أخرى
```

5. تنفيذ الترحيلات وإنشاء مستخدم:
```
python manage.py migrate
python manage.py createsuperuser
```

6. تشغيل الخادم:
```
python manage.py runserver
```

## هيكل المشروع

```
MWHEBA_ERP/
│
├── accounts/           # تطبيق المستخدمين والصلاحيات
├── config/             # إعدادات المشروع
├── docs/               # وثائق المشروع
├── financial/          # تطبيق النظام المالي
├── inventory/          # تطبيق إدارة المخزون
├── product/            # تطبيق إدارة المنتجات
├── sales/              # تطبيق إدارة المبيعات
├── purchase/           # تطبيق إدارة المشتريات
├── reports/            # تطبيق التقارير
├── static/             # الملفات الثابتة (CSS، JS، الصور)
│   ├── css/            # ملفات CSS
│   ├── js/             # ملفات JavaScript
│   ├── img/            # الصور
│   └── fonts/          # الخطوط
│
├── templates/          # قوالب HTML
│   ├── base.html       # القالب الأساسي
│   ├── components/     # مكونات قابلة لإعادة الاستخدام
│   ├── accounts/       # قوالب تطبيق الحسابات
│   └── financial/      # قوالب النظام المالي
│
├── .env                # ملف البيئة (غير مُضمن في Git)
├── .env.example        # مثال لملف البيئة
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

## المساهمة

نرحب بمساهمتكم في تطوير هذا المشروع. يرجى إتباع هذه الخطوات:

1. قم بعمل fork للمشروع
2. قم بإنشاء فرع جديد للميزة: `git checkout -b feature/your-feature-name`
3. قم بتطوير التغييرات والاختبارات
4. قم بعمل commit: `git commit -m 'إضافة ميزة جديدة'`
5. قم برفع التغييرات: `git push origin feature/your-feature-name`
6. قم بإنشاء طلب سحب (Pull Request)

## الترخيص

هذا المشروع مرخص تحت [ترخيص MIT](LICENSE).

# نظام إدارة موهبة للمبيعات والمخازن

نظام متكامل لإدارة المخزون والمبيعات والمشتريات والمحاسبة المالية مبني باستخدام Django 4.2.

## المميزات الرئيسية

- إدارة المستخدمين والصلاحيات
- إدارة العملاء والموردين
- إدارة المخزون والمنتجات
- إدارة المبيعات والفواتير
- نظام المشتريات وأوامر الشراء
- النظام المالي والحسابات
- تنبيهات النظام والإشعارات
- تقارير مفصلة وإحصائيات

## متطلبات التشغيل

- Python 3.8+
- PostgreSQL
- تثبيت المكتبات المطلوبة من ملف `requirements.txt`

## طريقة التثبيت

1. إنشاء بيئة افتراضية:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

2. تثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

3. إعداد ملف `.env` بمتغيرات البيئة:
```
DEBUG=True
SECRET_KEY=your_secret_key
DB_NAME=mwheba_erp
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

4. تهيئة قاعدة البيانات:
```bash
python manage.py migrate
```

5. إنشاء مستخدم المشرف:
```bash
python manage.py createsuperuser
```

6. تشغيل الخادم المحلي:
```bash
python manage.py runserver
```

## الهيكل العام للمشروع

- `core`: النواة المشتركة بين التطبيقات
- `users`: إدارة المستخدمين والأدوار والصلاحيات
- `client`: إدارة العملاء وبياناتهم
- `supplier`: إدارة الموردين وبياناتهم
- `product`: إدارة المنتجات والمخزون والفئات
- `sale`: إدارة المبيعات والفواتير
- `purchase`: إدارة أوامر الشراء وفواتير المشتريات
- `financial`: إدارة الحسابات المالية والمصروفات والإيرادات
- `helpers`: أدوات مساعدة ووظائف مشتركة

## المساهمة في المشروع

يرجى اتباع الخطوات التالية للمساهمة في تطوير المشروع:
1. عمل نسخة Fork من المشروع
2. إنشاء فرع جديد Feature Branch لكل ميزة جديدة
3. تقديم طلب Pull Request مع شرح مفصل للتغييرات 

# استعادة ترحيلات وبيانات Django في نظام MWHEBA ERP

## مشكلة قفل قاعدة البيانات على نظام Windows

عند محاولة إعادة ضبط قاعدة البيانات، قد تواجه مشكلة قفل ملف قاعدة البيانات `db.sqlite3` على نظام Windows. هذا يحدث عادة عندما تكون هناك عمليات Python أخرى تستخدم الملف، مثل خادم التطوير أو واجهة الإدارة.

## الطريقة المثلى لإعادة ضبط قاعدة البيانات

لدينا الآن طرق مُحسّنة للتعامل مع مشكلة قفل قاعدة البيانات:

### الطريقة 1: استخدام سكريبت إنهاء العمليات (موصى بها)

قمنا بإضافة سكريبت خاص لإنهاء جميع عمليات Python قبل تشغيل سكريبت إعادة الضبط:

```bash
python kill_python_processes.py
```

هذا السكريبت سيقوم بما يلي:
1. إنهاء جميع عمليات Python الجارية (باستثناء عملية تشغيل السكريبت نفسه).
2. تشغيل سكريبت `reset_migrations.py` مع خيار `--no-db-reset` لتجنب مشكلة قفل قاعدة البيانات.

#### خيارات سكريبت kill_python_processes.py

- بدون خيارات: ينهي جميع عمليات Python ثم يشغل سكريبت reset_migrations.py بشكل آمن
```bash
python kill_python_processes.py
```

- مع خيار `--reset-only`: ينهي عمليات Python فقط دون تشغيل سكريبت آخر
```bash
python kill_python_processes.py --reset-only
```

- تمرير وسائط إضافية إلى سكريبت reset_migrations.py
```bash
python kill_python_processes.py --simple-db-reset --no-server
```

### الطريقة 2: استخدام خيار --kill-python مع reset_migrations.py

تم إضافة خيار جديد لإنهاء عمليات Python قبل تشغيل reset_migrations.py:

```bash
python reset_migrations.py --kill-python
```

يقوم هذا الخيار بما يلي:
1. استدعاء سكريبت kill_python_processes.py لإنهاء عمليات Python في بداية تنفيذ reset_migrations.py
2. الانتظار لمدة 5 ثوانٍ للتأكد من إغلاق جميع العمليات
3. متابعة باقي خطوات إعادة ضبط قاعدة البيانات والترحيلات

### الطريقة 3: تخطي إعادة ضبط قاعدة البيانات مباشرة

إذا كنت تفضل تشغيل السكريبت الأصلي مباشرة، استخدم:

```bash
python reset_migrations.py --no-db-reset --wait 30
```

يقوم هذا الخيار بما يلي:
1. تخطي محاولة حذف قاعدة البيانات (وبالتالي تجنب مشكلة القفل).
2. الانتظار لفترة 30 ثانية قبل بدء عملية الترحيل، مما يعطي فرصة للعمليات الأخرى لإنهاء عملها.

### الطريقة 4: استخدام خيار إعادة الضبط المبسط

```bash
python reset_migrations.py --simple-db-reset
```

يستخدم هذا الخيار طريقة أبسط لحذف ملف قاعدة البيانات والآن يستدعي سكريبت kill_python_processes.py تلقائياً لإنهاء العمليات المرتبطة به.

## نصائح لتجنب المشكلة مستقبلاً

1. تأكد دائمًا من إيقاف خادم التطوير (باستخدام Ctrl+C) قبل تشغيل سكريبت إعادة الضبط.
2. أغلق جميع نوافذ الصدفة التفاعلية لـ Django.
3. أغلق أي تطبيقات أخرى قد تكون تستخدم ملف قاعدة البيانات.
4. استخدم خيار `--kill-python` قبل محاولة إعادة ضبط قاعدة البيانات.

## خيارات السكريبت المتاحة

- `--no-backup`: تخطي إنشاء نسخة احتياطية.
- `--no-migrations`: تخطي حذف وإعادة إنشاء ملفات الترحيل.
- `--no-db-reset`: تخطي إعادة ضبط قاعدة البيانات.
- `--no-fixtures`: تخطي تحميل البيانات الافتراضية.
- `--no-server`: تخطي تشغيل الخادم بعد الانتهاء.
- `--simple-db-reset`: استخدام طريقة مبسطة لإعادة ضبط قاعدة البيانات.
- `--wait N`: الانتظار لمدة N ثانية قبل بدء الترحيلات (مفيد مع `--no-db-reset`).
- `--kill-python`: إنهاء جميع عمليات Python قبل البدء (مفيد جداً لتجنب مشاكل قفل قاعدة البيانات).

## ملاحظات هامة

- عند استخدام خيار `--no-db-reset`، سيتم تنظيف البيانات الموجودة في قاعدة البيانات باستخدام أمر `flush`، لكن هيكل قاعدة البيانات سيبقى كما هو.
- إذا استمرت مشكلة قفل قاعدة البيانات، جرب تشغيل سكريبت `kill_python_processes.py` بشكل منفصل أولاً.
- يمكنك الجمع بين عدة خيارات، مثل `--kill-python --simple-db-reset --no-server` للحصول على أفضل تجربة.
- في بعض الحالات، قد تحتاج لتشغيل سكريبت `kill_python_processes.py` كمسؤول (Administrator) للتمكن من إنهاء جميع العمليات.

# Page Header Component (مكون عنوان الصفحة)

تم تطوير مكون موحد لعنوان الصفحة مع شريط التنقل (Breadcrumb) لاستخدامه في جميع صفحات النظام. يوفر هذا المكون طريقة احترافية وموحدة لعرض:

1. شريط التنقل (Breadcrumb)
2. عنوان الصفحة الرئيسي
3. وصف فرعي (اختياري)
4. أزرار الإجراءات (Actions) على اليمين

## طريقة الاستخدام

أضف المكون في بداية محتوى القالب الخاص بك:

```html
{% include "components/page_header.html" with 
    title="عنوان الصفحة" 
    subtitle="وصف فرعي للصفحة" 
    icon="fas fa-icon-name"
    action_buttons=action_buttons
%}
```

## خيارات المكون

| الخيار | الوصف | النوع | مثال |
|--------|-------|------|------|
| `title` | عنوان الصفحة الرئيسي | نص | `"المبيعات"` |
| `subtitle` | وصف فرعي للصفحة (اختياري) | نص | `"إدارة جميع المبيعات والفواتير"` |
| `icon` | أيقونة Font Awesome لعنوان الصفحة (اختياري) | نص | `"fas fa-shopping-cart"` |
| `action_buttons` | قائمة بأزرار الإجراءات على اليمين (اختياري) | قائمة قواميس | `[{'url': url, 'text': 'إضافة', 'icon': 'fa-plus', 'class': 'btn-primary'}]` |

## أمثلة للاستخدام

### مثال أساسي
```html
{% include "components/page_header.html" with 
    title="العملاء" 
    icon="fas fa-users"
%}
```

### مثال مع وصف فرعي
```html
{% include "components/page_header.html" with 
    title="المنتجات" 
    subtitle="إدارة جميع منتجات المخزون"
    icon="fas fa-box"
%}
```

### مثال مع أزرار إجراءات
```html
{% include "components/page_header.html" with 
    title="المبيعات" 
    subtitle="قائمة بجميع فواتير المبيعات"
    icon="fas fa-shopping-cart"
    action_buttons="[
        {'url': '{% url 'sale:sale_create' %}', 'text': 'فاتورة جديدة', 'icon': 'fa-plus', 'class': 'btn-primary'},
        {'url': '{% url 'sale:sale_report' %}', 'text': 'تقرير', 'icon': 'fa-chart-bar', 'class': 'btn-outline-secondary'}
    ]"
%}
```

### مثال مع دالة شرطية
```html
{% include "components/page_header.html" with 
    title=page_title 
    icon=page_icon
    action_buttons=can_add|yesno:"[{'url': '{% url 'app:create' %}', 'text': 'إضافة', 'icon': 'fa-plus', 'class': 'btn-primary'}],[]" 
%}
```

### ربط مع نموذج
لربط زر مع نموذج (form)، استخدم خاصية `form_id`:

```html
{% include "components/page_header.html" with 
    title="الإشعارات" 
    subtitle="إدارة إشعارات النظام"
    icon="fas fa-bell"
    action_buttons="[{'text': 'تعليم الكل كمقروء', 'icon': 'fa-check-double', 'class': 'btn-outline-primary', 'url': '#', 'form_id': 'mark_all_read_form'}]" 
%}

<!-- النموذج المرتبط -->
<form id="mark_all_read_form" method="post" class="d-none">
    {% csrf_token %}
    <input type="hidden" name="action" value="mark_all_read">
</form>

<script>
    // ربط زر الإجراء بتقديم النموذج
    $('.page-header-actions a[data-form-id="mark_all_read_form"]').on('click', function(e) {
        e.preventDefault();
        $('#mark_all_read_form').submit();
    });
</script>
``` 