/**
 * Main JavaScript File for MWHEBA ERP System
 * 
 * Contains all custom scripts for the ERP system
 * 
 * @author MWHEBA ERP Team
 * @version 1.0.0
 */

// التحكم في تصحيح الأخطاء
const DEBUG_DROPDOWNS = true;

$(document).ready(function() {
    // تهيئة السلايد بار
    initSidebar();
    
    // تهيئة التوسترات
    initTooltips();
    
    // تهيئة حوارات تأكيد الحذف
    initDeleteConfirmations();
    
    // تهيئة التحقق من الفورم
    initFormValidations();
    
    // تهيئة الفورم الديناميكية
    initDynamicForms();
    
    // تهيئة التبويبات المحفوظة
    initSavedTabs();
    
    // تهيئة النوافذ المنبثقة
    initModals();
    
    // تهيئة الفلاتر
    initFilters();
    
    // تهيئة القوائم المنسدلة وضمان استدعائها قبل ظهور أي شيء
    setTimeout(() => {
        initDropdowns();
    }, 0);
});

// إغلاق القوائم المنسدلة عند تحميل الصفحة بالكامل
$(window).on('load', function() {
    // التأكد من إغلاق جميع القوائم المنسدلة عند تحميل الصفحة بالكامل
    $('.dropdown-menu').removeClass('show');
});

/**
 * تهيئة التوسترات
 */
function initTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * تهيئة حوارات تأكيد الحذف
 */
function initDeleteConfirmations() {
    $(document).on("click", ".btn-delete", function(e) {
        e.preventDefault();
        const url = $(this).attr("href");
        const title = $(this).data("title") || "هل أنت متأكد من الحذف؟";
        const message = $(this).data("message") || "لن تتمكن من استعادة هذا العنصر بعد الحذف!";
        
        confirmAction(message, title, function() {
            window.location.href = url;
        });
    });
}

/**
 * تهيئة التحقق من الفورم 
 */
function initFormValidations() {
    // التحقق من صحة النماذج
    const forms = document.querySelectorAll('.needs-validation');
    
    if (forms.length > 0) {
        forms.forEach(form => {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                    
                    // عرض رسالة خطأ
                    notify('يرجى التحقق من البيانات المدخلة', 'error');
                }
                
                form.classList.add('was-validated');
            }, false);
        });
    }
}

/**
 * تهيئة الفورم الديناميكية
 */
function initDynamicForms() {
    // إضافة صف جديد في نماذج البيانات المتعددة
    $(document).on("click", ".add-form-row", function() {
        const formsetName = $(this).data("formset");
        const formsetContainer = $("#" + formsetName + "-container");
        const totalForms = $("#id_" + formsetName + "-TOTAL_FORMS");
        const formNum = parseInt(totalForms.val());
        
        // نسخ النموذج الأخير
        const newForm = formsetContainer.find(".formset-row:last").clone(true);
        
        // تحديث المعرفات والأسماء
        newForm.find(":input").each(function() {
            const name = $(this).attr("name").replace("-" + (formNum - 1) + "-", "-" + formNum + "-");
            const id = "id_" + name;
            
            $(this).attr({"name": name, "id": id}).val("").removeAttr("checked");
        });
        
        // تحديث عناوين الحقول
        newForm.find("label").each(function() {
            const newFor = $(this).attr("for").replace("-" + (formNum - 1) + "-", "-" + formNum + "-");
            $(this).attr("for", newFor);
        });
        
        // إضافة النموذج الجديد
        formsetContainer.append(newForm);
        
        // تحديث العدد الإجمالي للنماذج
        totalForms.val(formNum + 1);
    });
    
    // حذف صف من نماذج البيانات المتعددة
    $(document).on("click", ".remove-form-row", function() {
        const formsetName = $(this).data("formset");
        const totalForms = $("#id_" + formsetName + "-TOTAL_FORMS");
        
        // حذف الصف فقط إذا كان هناك أكثر من صف واحد
        if (parseInt(totalForms.val()) > 1) {
            $(this).closest(".formset-row").remove();
            
            // تحديث عدد النماذج
            totalForms.val(parseInt(totalForms.val()) - 1);
            
            // إعادة ترقيم النماذج
            $(".formset-row").each(function(i) {
                $(this).find(":input").each(function() {
                    if ($(this).attr("name")) {
                        const name = $(this).attr("name").replace(/-\d+-/, "-" + i + "-");
                        const id = "id_" + name;
                        
                        $(this).attr({"name": name, "id": id});
                    }
                });
                
                $(this).find("label").each(function() {
                    if ($(this).attr("for")) {
                        const newFor = $(this).attr("for").replace(/-\d+-/, "-" + i + "-");
                        $(this).attr("for", newFor);
                    }
                });
            });
        } else {
            // إذا كان هناك صف واحد فقط، فقم بإعادة تعيين قيمه
            $(this).closest(".formset-row").find(":input").val("").prop("checked", false);
        }
    });
}

/**
 * تهيئة التبويبات المحفوظة
 */
function initSavedTabs() {
    // حفظ التبويب النشط في التخزين المحلي
    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        const tabId = $(e.target).attr('href');
        const tabContainer = $(e.target).closest('.tabs-container');
        const containerId = tabContainer.attr('id') || 'default-tabs';
        
        localStorage.setItem('activeTab-' + containerId, tabId);
    });
    
    // استعادة التبويب النشط
    $('.tabs-container').each(function() {
        const containerId = $(this).attr('id') || 'default-tabs';
        const activeTab = localStorage.getItem('activeTab-' + containerId);
        
        if (activeTab) {
            try {
                const tab = new bootstrap.Tab($(this).find('a[href="' + activeTab + '"]')[0]);
                tab.show();
            } catch (e) {
                // في حالة حدوث خطأ، لا تفعل شيئًا
            }
        }
    });
}

/**
 * تهيئة النوافذ المنبثقة
 */
function initModals() {
    // تحميل المحتوى عبر AJAX للنوافذ المنبثقة
    $(document).on('click', '[data-bs-toggle="ajax-modal"]', function(e) {
        e.preventDefault();
        
        const url = $(this).attr('href') || $(this).data('url');
        const target = $(this).data('bs-target');
        const modal = $(target);
        
        if (!url || !modal.length) return;
        
        // عرض شاشة التحميل
        modal.find('.modal-content').html('<div class="text-center my-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">جاري التحميل...</span></div><p class="mt-2">جاري التحميل...</p></div>');
        
        // فتح النافذة المنبثقة
        const bsModal = new bootstrap.Modal(modal[0]);
        bsModal.show();
        
        // تحميل المحتوى
        $.get(url, function(data) {
            modal.find('.modal-content').html(data);
            
            // تهيئة عناصر النموذج داخل النافذة المنبثقة
            modal.find('select.select2').select2({
                dropdownParent: modal
            });
            
            // تفعيل التحقق من صحة النموذج
            initFormValidations();
        }).fail(function() {
            modal.find('.modal-content').html('<div class="modal-header"><h5 class="modal-title">خطأ</h5><button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="إغلاق"></button></div><div class="modal-body"><div class="alert alert-danger">حدث خطأ أثناء تحميل المحتوى</div></div>');
        });
    });
    
    // تنظيف النافذة المنبثقة بعد إغلاقها
    $(document).on('hidden.bs.modal', '.modal', function() {
        if ($(this).hasClass('clear-on-close')) {
            $(this).find('.modal-body').html('');
        }
    });
}

/**
 * تهيئة الفلاتر
 */
function initFilters() {
    // تحديث الفلاتر عند التغيير
    $(document).on('change', '.filter-on-change', function() {
        $(this).closest('form').submit();
    });
    
    // زر إعادة ضبط الفلاتر
    $(document).on('click', '.reset-filters', function(e) {
        e.preventDefault();
        window.location.href = $(this).attr('href') || window.location.pathname;
    });
}

/**
 * عرض إشعار للمستخدم
 */
function notify(message, type = 'success', title = null) {
    if (!title) {
        if (type === 'success') title = 'تم بنجاح';
        else if (type === 'error') title = 'خطأ';
        else if (type === 'warning') title = 'تحذير';
        else title = 'معلومات';
    }
    
    Swal.fire({
        title: title,
        text: message,
        icon: type,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        rtl: true
    });
}

/**
 * تنسيق الأرقام كعملة
 */
function formatCurrency(amount, currency = 'ج.م', decimals = 2) {
    // استخدام دالة formatNumber من ملف number_formatter.js
    if (typeof formatNumber === 'function') {
        return formatNumber(amount) + ' ' + currency;
    }
    
    // الطريقة الاحتياطية في حالة عدم توفر دالة formatNumber
    if (isNaN(amount)) return '0.00 ' + currency;
    return parseFloat(amount).toFixed(decimals).replace(/\d(?=(\d{3})+\.)/g, '$&,') + ' ' + currency;
}

/**
 * تنسيق التاريخ
 */
function formatDate(dateString, format = 'yyyy-mm-dd') {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    if (format === 'yyyy-mm-dd') {
        return `${year}-${month}-${day}`;
    } else if (format === 'dd/mm/yyyy') {
        return `${day}/${month}/${year}`;
    } else if (format === 'mm/dd/yyyy') {
        return `${month}/${day}/${year}`;
    }
    
    return `${year}-${month}-${day}`;
}

/**
 * تحويل حجم الملف إلى تنسيق مقروء
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 بايت';
    
    const k = 1024;
    const sizes = ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت', 'تيرابايت'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * وظائف التنبيهات والتأكيدات
 */

/**
 * عرض رسالة تنبيه باستخدام SweetAlert2
 * @param {string} message - نص الرسالة
 * @param {string} type - نوع التنبيه (success, error, warning, info)
 * @param {string} title - عنوان التنبيه (اختياري)
 * @param {number} timer - وقت إخفاء التنبيه بالمللي ثانية (اختياري، الافتراضي 3000)
 */
function showAlert(message, type = 'info', title = '', timer = 3000) {
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: timer,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer);
            toast.addEventListener('mouseleave', Swal.resumeTimer);
        }
    });
    
    Toast.fire({
        icon: type,
        title: title || message,
        text: title ? message : '',
    });
}

/**
 * عرض نافذة تأكيد مع خيارات نعم/لا
 * @param {string} message - نص السؤال
 * @param {string} title - عنوان النافذة
 * @param {Function} callback - دالة ترجع المستدعاة عند النقر على زر "نعم"
 * @param {string} confirmButtonText - نص زر التأكيد (اختياري، الافتراضي "نعم")
 * @param {string} cancelButtonText - نص زر الإلغاء (اختياري، الافتراضي "لا")
 */
function confirmAction(message, title, callback, confirmButtonText = 'نعم', cancelButtonText = 'لا') {
    Swal.fire({
        title: title,
        text: message,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: confirmButtonText,
        cancelButtonText: cancelButtonText,
        focusConfirm: false,
        focusCancel: true,
    }).then((result) => {
        if (result.isConfirmed && typeof callback === 'function') {
            callback();
        }
    });
}

/**
 * عرض نافذة تنبيه للنجاح مع زر موافق
 * @param {string} message - نص الرسالة
 * @param {string} title - عنوان النافذة (اختياري)
 * @param {Function} callback - دالة ترجع المستدعاة بعد إغلاق النافذة (اختياري)
 */
function successAlert(message, title = 'تمت العملية بنجاح', callback = null) {
    Swal.fire({
        icon: 'success',
        title: title,
        text: message,
        confirmButtonText: 'موافق'
    }).then(() => {
        if (typeof callback === 'function') {
            callback();
        }
    });
}

/**
 * عرض نافذة تنبيه للخطأ مع زر موافق
 * @param {string} message - نص رسالة الخطأ
 * @param {string} title - عنوان النافذة (اختياري)
 */
function errorAlert(message, title = 'حدث خطأ') {
    Swal.fire({
        icon: 'error',
        title: title,
        text: message,
        confirmButtonText: 'موافق'
    });
}

/**
 * تهيئة القائمة الجانبية وإضافة الأحداث
 */
function initSidebar() {
    const body = document.body;
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mobileSidebarToggle = document.getElementById('mobile-sidebar-toggle');
    const sidebar = document.querySelector('.sidebar-wrapper');
    
    // التحقق من حجم الشاشة المبدئي وضبط الإعدادات
    checkScreenSize();
    
    // تبديل حالة القائمة الجانبية عند الضغط على الزر
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            body.classList.toggle('sidebar-collapsed');
            
            // حفظ حالة القائمة الجانبية في localStorage
            localStorage.setItem('sidebar-collapsed', body.classList.contains('sidebar-collapsed'));
        });
    }
    
    // تبديل حالة القائمة الجانبية في الأجهزة المحمولة
    if (mobileSidebarToggle) {
        mobileSidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            body.classList.toggle('mobile-sidebar-visible');
        });
    }
    
    // إغلاق القائمة الجانبية عند النقر خارجها في الشاشات الصغيرة
    document.addEventListener('click', function(e) {
        if (body.classList.contains('mobile-sidebar-visible') && 
            !sidebar.contains(e.target) && 
            e.target !== mobileSidebarToggle) {
            body.classList.remove('mobile-sidebar-visible');
        }
    });
    
    // ضبط القوائم الفرعية
    setupSubmenus();
    
    // استعادة حالة القائمة الجانبية من localStorage
    restoreSidebarState();
    
    // استعادة حالة القوائم الفرعية المفتوحة من localStorage
    restoreOpenSubmenus();
    
    // مراقبة تغيير حجم النافذة
    window.addEventListener('resize', checkScreenSize);
}

/**
 * التحقق من حجم الشاشة وتطبيق الإعدادات المناسبة
 */
function checkScreenSize() {
    const body = document.body;
    
    if (window.innerWidth <= 991) {
        // إعادة تعيين حالة القائمة في الشاشات الصغيرة
        body.classList.remove('sidebar-collapsed');
    } else {
        // إزالة حالة القائمة المرئية في الأجهزة المحمولة في الشاشات الكبيرة
        body.classList.remove('mobile-sidebar-visible');
    }
}

/**
 * إعداد القوائم الفرعية في القائمة الجانبية
 */
function setupSubmenus() {
    const sidebarLinks = document.querySelectorAll('.sidebar-link[data-bs-toggle="collapse"]');
    
    sidebarLinks.forEach(link => {
        // استخدام Bootstrap Collapse API للتعامل مع القوائم الفرعية بشكل أفضل
        link.addEventListener('click', function(e) {
            const submenuId = this.getAttribute('href');
            
            // في القائمة المصغرة ومع الشاشات الكبيرة، منع السلوك الافتراضي
            if (document.body.classList.contains('sidebar-collapsed') && window.innerWidth > 991) {
                e.preventDefault();
                showSubmenu(submenuId.substring(1)); // إزالة # من المعرف
                return;
            }
            
            // حفظ حالة القائمة الفرعية في localStorage
            const submenu = document.querySelector(submenuId);
            if (submenu) {
                // نتحقق إذا كان بيتم فتح أم إغلاق القائمة
                const willBeOpen = !submenu.classList.contains('show');
                
                // حفظ حالة القائمة الفرعية في localStorage
                if (willBeOpen) {
                    saveSubmenuState(submenuId.substring(1), true);
                } else {
                    // لا نقوم بإزالة الحالة المحفوظة عند الإغلاق للحفاظ عليها عند تصفح الصفحات الداخلية
                    // saveSubmenuState(submenuId.substring(1), false);
                }
                
                // ضبط ارتفاع القائمة الفرعية ديناميكيًا لتحسين الأداء
                if (submenu.classList.contains('show')) {
                    // عند إغلاق القائمة، ضبط الارتفاع على الحجم الحالي قبل الإغلاق
                    submenu.style.height = submenu.scrollHeight + 'px';
                    // ضروري لتطبيق الانتقال بشكل سلس
                    setTimeout(() => {
                        submenu.style.height = '0';
                        submenu.style.opacity = '0';
                        submenu.style.transform = 'translateY(-10px)';
                    }, 10);
                } else {
                    // عند فتح القائمة، ضبط الارتفاع على auto بعد انتهاء الانتقال
                    submenu.style.height = submenu.scrollHeight + 'px';
                    submenu.style.opacity = '1';
                    submenu.style.transform = 'translateY(0)';
                    setTimeout(() => {
                        submenu.style.height = 'auto';
                    }, 300);
                }
            }
        });
        
        // التعامل مع تحرك الماوس فوق العناصر في وضع القائمة المصغرة
        if (window.innerWidth > 991) {
            const submenuId = link.getAttribute('href');
            const submenu = document.querySelector(submenuId);
            const parentItem = link.parentElement;
            
            if (submenu && parentItem) {
                parentItem.addEventListener('mouseenter', function() {
                    if (document.body.classList.contains('sidebar-collapsed')) {
                        showSubmenu(submenuId.substring(1));
                    }
                });
                
                parentItem.addEventListener('mouseleave', function() {
                    if (document.body.classList.contains('sidebar-collapsed')) {
                        hideSubmenu(submenuId.substring(1));
                    }
                });
            }
        }
    });
}

/**
 * عرض القائمة الفرعية بطريقة أكثر كفاءة
 */
function showSubmenu(submenuId) {
    const submenu = document.getElementById(submenuId);
    if (submenu) {
        submenu.classList.add('show');
        submenu.style.opacity = '1';
        submenu.style.transform = 'translateY(0)';
        submenu.style.height = 'auto';
        
        // تحديث حالة الزر المرتبط بهذه القائمة
        const submenuLink = document.querySelector(`a[href="#${submenuId}"]`);
        if (submenuLink) {
            submenuLink.setAttribute('aria-expanded', 'true');
            submenuLink.classList.remove('collapsed');
        }
        
        // حفظ حالة القائمة الفرعية في localStorage
        saveSubmenuState(submenuId, true);
    }
}

/**
 * إخفاء القائمة الفرعية بطريقة أكثر كفاءة
 */
function hideSubmenu(submenuId) {
    const submenu = document.getElementById(submenuId);
    if (submenu) {
        submenu.classList.remove('show');
        submenu.style.opacity = '0';
        submenu.style.transform = 'translateY(-5px)';
        submenu.style.height = '0';
        
        // تحديث حالة الزر المرتبط بهذه القائمة
        const submenuLink = document.querySelector(`a[href="#${submenuId}"]`);
        if (submenuLink) {
            submenuLink.setAttribute('aria-expanded', 'false');
            submenuLink.classList.add('collapsed');
        }
        
        // لا نقوم بإزالة الحالة المحفوظة عند الإغلاق في وضع القائمة المصغرة
        if (!document.body.classList.contains('sidebar-collapsed')) {
            // saveSubmenuState(submenuId, false);
        }
    }
}

/**
 * استعادة حالة القائمة الجانبية من localStorage
 */
function restoreSidebarState() {
    const body = document.body;
    const savedState = localStorage.getItem('sidebar-collapsed');
    
    if (savedState === 'true' && window.innerWidth > 991) {
        body.classList.add('sidebar-collapsed');
    }
}

/**
 * حفظ حالة القائمة الفرعية في localStorage
 * @param {string} submenuId - معرف القائمة الفرعية
 * @param {boolean} isOpen - هل القائمة مفتوحة أم لا
 */
function saveSubmenuState(submenuId, isOpen) {
    // لا نخزن حالة القوائم المنسدلة في الهيدر (تبدأ بـ header)
    if (submenuId.startsWith('header')) {
        return;
    }
    
    // نخزن حالة القوائم الفرعية في السايدبار فقط
    // نتحقق إن القائمة الفرعية هي في السايدبار من خلال بادئة الاسم
    const sidebarMenuPrefixes = ['salesMenu', 'purchaseMenu', 'clientMenu', 'supplierMenu', 
                                'inventoryMenu', 'financialMenu', 'reportMenu', 'userMenu', 'settingsMenu'];
    
    const isSidebarMenu = sidebarMenuPrefixes.some(prefix => submenuId.startsWith(prefix));
    
    if (!isSidebarMenu) {
        return; // لا نحفظ إلا القوائم الفرعية في السايدبار
    }
    
    // الحصول على حالة القوائم الفرعية المفتوحة من localStorage
    let openSubmenus = JSON.parse(localStorage.getItem('open-submenus') || '[]');
    
    if (isOpen) {
        // إضافة القائمة الفرعية إلى القائمة إذا لم تكن موجودة بالفعل
        if (!openSubmenus.includes(submenuId)) {
            openSubmenus.push(submenuId);
        }
    } else {
        // إزالة القائمة الفرعية من القائمة
        openSubmenus = openSubmenus.filter(id => id !== submenuId);
    }
    
    // حفظ القائمة المحدثة في localStorage
    localStorage.setItem('open-submenus', JSON.stringify(openSubmenus));
}

/**
 * استعادة حالة القوائم الفرعية المفتوحة من localStorage
 */
function restoreOpenSubmenus() {
    // الحصول على حالة القوائم الفرعية المفتوحة من localStorage
    const openSubmenus = JSON.parse(localStorage.getItem('open-submenus') || '[]');
    
    // فتح كل قائمة فرعية محفوظة في السايدبار
    openSubmenus.forEach(submenuId => {
        const submenu = document.getElementById(submenuId);
        const submenuLink = document.querySelector(`a[href="#${submenuId}"]`);
        
        if (submenu && submenuLink) {
            // في الشاشات الكبيرة بدون وضع القائمة المصغرة
            if (window.innerWidth > 991 && !document.body.classList.contains('sidebar-collapsed')) {
                // إضافة فئة 'show' للقائمة الفرعية
                submenu.classList.add('show');
                submenu.style.height = 'auto';
                submenu.style.opacity = '1';
                submenu.style.transform = 'translateY(0)';
                
                // تحديث حالة aria-expanded
                submenuLink.setAttribute('aria-expanded', 'true');
                submenuLink.classList.remove('collapsed');
            }
        }
    });
}

/**
 * تهيئة القوائم المنسدلة 
 */
function initDropdowns() {
    // مسح الحالات المحفوظة للقوائم المنسدلة في الهيدر من localStorage فقط
    try {
        let allKeys = [];
        for (let i = 0; i < localStorage.length; i++) {
            let key = localStorage.key(i);
            // نحذف فقط مفاتيح القوائم المنسدلة في الهيدر وليس السايدبار
            if (key && (key.includes('dropdown') || key.includes('header-menu'))) {
                allKeys.push(key);
            }
        }
        // حذف المفاتيح المتعلقة بالقوائم المنسدلة في الهيدر
        allKeys.forEach(key => localStorage.removeItem(key));
        
        // التأكد من حذف المفاتيح المعروفة للقوائم المنسدلة في الهيدر
        localStorage.removeItem('openDropdowns');
        localStorage.removeItem('open-dropdown-menus');
        // لا نحذف 'open-submenus' لأنه خاص بالقوائم الفرعية في السايدبار
    } catch (e) {
        console.error('خطأ عند محاولة حذف حالات القوائم المنسدلة المحفوظة');
    }
    
    // إزالة أي مستمعات أحداث سابقة للقوائم المنسدلة في الهيدر
    $(document).off('click.customDropdown');
    $('[data-custom-dropdown]').off('click.customDropdown');
    $(document).off('keydown.customDropdown');
    
    // إغلاق كل القوائم المنسدلة في الهيدر
    $('.dropdown-menu').not('.submenu').removeClass('show');
    
    // إضافة مستمع أحداث للأزرار التي تفتح القوائم المنسدلة في الهيدر
    $('[data-custom-dropdown]').on('click.customDropdown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const $button = $(this);
        const $menu = $button.next('.dropdown-menu');
        
        // إغلاق كل القوائم المنسدلة الأخرى في الهيدر أولاً
        $('.dropdown-menu.show').not('.submenu').not($menu).removeClass('show');
        
        // تبديل حالة القائمة الحالية
        $menu.toggleClass('show');
    });
    
    // إغلاق القوائم المنسدلة في الهيدر عند النقر في أي مكان آخر
    $(document).on('click.customDropdown', function(e) {
        // التحقق مما إذا كان النقر خارج أي قائمة منسدلة في الهيدر وزر القائمة
        if (!$(e.target).closest('[data-custom-dropdown]').length && 
            !$(e.target).closest('.dropdown-menu').not('.submenu').length) {
            // إغلاق فقط القوائم المنسدلة في الهيدر
            $('.dropdown-menu.show').not('.submenu').removeClass('show');
        }
    });
    
    // إغلاق القوائم المنسدلة في الهيدر عند الضغط على زر Escape
    $(document).on('keydown.customDropdown', function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) { // ESC key
            // إغلاق فقط القوائم المنسدلة في الهيدر
            $('.dropdown-menu.show').not('.submenu').removeClass('show');
        }
    });
    
    // منع حفظ حالة القوائم المنسدلة في الهيدر عند إعادة تحميل الصفحة
    $(window).on('beforeunload', function() {
        // إغلاق فقط القوائم المنسدلة في الهيدر
        $('.dropdown-menu').not('.submenu').removeClass('show');
        
        // حذف البيانات المحفوظة للقوائم المنسدلة في الهيدر
        localStorage.removeItem('openDropdowns');
        localStorage.removeItem('open-dropdown-menus');
    });
}

// استدعاء مباشر لدالة initDropdowns لتأكيد تنفيذها
(function immediateInit() {
    // فرض إغلاق كل القوائم المنسدلة في الهيدر فقط
    $('.dropdown-menu').not('.submenu').removeClass('show');
    
    // حذف بيانات القوائم المنسدلة في الهيدر من localStorage
    try {
        localStorage.removeItem('openDropdowns');
        localStorage.removeItem('open-dropdown-menus');
        // نحتفظ بـ open-submenus للسايدبار
        
        // البحث عن وحذف مفاتيح localStorage المتعلقة بالقوائم المنسدلة في الهيدر
        let allKeys = [];
        for (let i = 0; i < localStorage.length; i++) {
            let key = localStorage.key(i);
            if (key && (key.includes('dropdown') || key.includes('header-menu'))) {
                allKeys.push(key);
            }
        }
        allKeys.forEach(key => localStorage.removeItem(key));
    } catch (e) {
        console.error('فشل حذف بيانات القوائم المنسدلة من التخزين المحلي');
    }
    
    // استدعاء دالة التهيئة على الفور
    setTimeout(function() {
        initDropdowns();
        console.log('تم تنفيذ استدعاء فوري لإعداد القوائم المنسدلة');
    }, 0);
})(); 