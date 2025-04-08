# نظام الكروت العالمي

تم تطوير نظام كروت إحصائيات متكامل للاستخدام في جميع أجزاء النظام. يوفر هذا النظام أنماطًا متعددة من الكروت التي يمكن استخدامها لعرض الإحصائيات والبيانات بطريقة جذابة وموحدة.

## تكامل النظام

تم إضافة ملف `cards.css` إلى النظام كملف CSS عالمي يحتوي على جميع أنماط الكروت المتاحة. يتم تضمين هذا الملف تلقائيًا في جميع صفحات النظام من خلال قالب `base.html`.

## أنواع الكروت المتاحة

### 1. كروت الإحصائيات الأساسية

كروت بتصميم أساسي مع شريط ملون في الأعلى وأيقونة مميزة على الجانب.

```html
<div class="stats-card stats-card-primary">
  <div class="stats-card-header"></div>
  <div class="stats-card-body">
    <div class="stats-card-icon">
      <i class="fas fa-exchange-alt"></i>
    </div>
    <div class="stats-card-title">عنوان الكارت</div>
    <div class="stats-card-value">1,234</div>
    <div class="stats-card-unit">وحدة القياس</div>
  </div>
</div>
```

### 2. كروت بديلة أفقية

كروت بتصميم أفقي بدون شريط في الأعلى ومع أيقونة على اليمين.

```html
<div class="stats-card-alt primary">
  <div class="stats-card-alt-icon">
    <i class="fas fa-money-bill-wave"></i>
  </div>
  <div class="stats-card-alt-content">
    <div class="stats-card-alt-title">عنوان الكارت</div>
    <div class="stats-card-alt-value">1,234</div>
    <div class="stats-card-alt-unit">وحدة القياس</div>
  </div>
</div>
```

### 3. كروت بخلفية متدرجة

كروت بخلفية ملونة متدرجة وأيقونة كبيرة في الخلفية.

```html
<div class="stats-card-gradient primary">
  <div class="stats-card-gradient-icon">
    <i class="fas fa-percent"></i>
  </div>
  <div class="stats-card-gradient-title">عنوان الكارت</div>
  <div class="stats-card-gradient-value">87</div>
  <div class="stats-card-gradient-unit">%</div>
</div>
```

### 4. كروت المحتوى والمعلومات

كروت لعرض محتوى أكثر تفصيلاً مع رأس وجسم وتذييل اختياري.

```html
<div class="info-card">
  <div class="info-card-header">
    <h5 class="info-card-title">عنوان الكارت</h5>
    <div class="info-card-subtitle">عنوان فرعي اختياري</div>
  </div>
  <div class="info-card-body">
    محتوى الكارت هنا...
  </div>
  <div class="info-card-footer">
    تذييل الكارت (اختياري)
  </div>
</div>
```

## ألوان الكروت المتاحة

تتوفر جميع أنواع الكروت في الألوان التالية:

- `primary` - لون أزرق أساسي
- `success` - لون أخضر للنجاح
- `danger` - لون أحمر للتحذير
- `info` - لون أزرق فاتح للمعلومات
- `warning` - لون برتقالي للتنبيه

## أمثلة على الاستخدام

1. صفحة `transaction_list.html` - تستخدم كروت الإحصائيات الأساسية لعرض إحصائيات المعاملات المالية.
2. صفحة `analytics.html` - تستخدم كروت بديلة أفقية وكروت بخلفية متدرجة لعرض المؤشرات المالية.

## تحسينات RTL

تم تحسين جميع الكروت للاستخدام في واجهات RTL بشكل تلقائي. عند تفعيل وضع RTL في الصفحة (عن طريق `dir="rtl"` على عنصر `html`), سيتم تطبيق التحسينات اللازمة تلقائيًا. 