// إضافة مستمع حدث للزر sidebar-collapse
document.addEventListener('DOMContentLoaded', function() {
    // زر تصغير الشريط الجانبي
    const sidebarCollapseBtn = document.getElementById('sidebar-collapse');
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }

    // جعل النقر على أي عنصر في السايدبار المصغر يقوم بتوسيع السايدبار
    const sidebarLinks = document.querySelectorAll('.sidebar-item > .sidebar-link');
    if (sidebarLinks) {
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                // إذا كان السايدبار مصغرًا والرابط يحتوي على قائمة فرعية
                if (document.body.classList.contains('sidebar-collapsed') && this.getAttribute('data-bs-toggle') === 'collapse') {
                    e.preventDefault(); // منع السلوك الافتراضي
                    toggleSidebar(); // توسيع السايدبار
                }
            });
        });
    }

    // استعادة حالة الشريط الجانبي من localStorage عند تحميل الصفحة
    if (localStorage.getItem('sidebar-collapsed') === 'true') {
        document.body.classList.add('sidebar-collapsed');
    }

    // زر التبديل للهاتف المحمول
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-toggled');
        });
    }

    // وظيفة لتبديل حالة الشريط الجانبي
    function toggleSidebar() {
        document.body.classList.toggle('sidebar-collapsed');
        // حفظ حالة الشريط الجانبي في localStorage
        if (document.body.classList.contains('sidebar-collapsed')) {
            localStorage.setItem('sidebar-collapsed', 'true');
        } else {
            localStorage.setItem('sidebar-collapsed', 'false');
        }
    }
}); 