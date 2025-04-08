/**
 * تهيئة الجداول في النظام
 * =======================
 * هذا الملف يحتوي على الدوال الخاصة بتهيئة وتنسيق الجداول في النظام
 * 
 * الاستخدام:
 * 1. أضف <script src="{% static 'js/global-table.js' %}"></script> في base.html
 * 2. استدعي الدالة initGlobalTable مع معرف الجدول والإعدادات المناسبة
 */

/**
 * تهيئة الجدول العام
 * @param {string} tableId - معرف الجدول (مطلوب)
 * @param {Object} options - الإعدادات (اختياري)
 */
function initGlobalTable(tableId, options = {}) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // الإعدادات الافتراضية
    const defaultOptions = {
        responsive: true,
        order: [],
        pageLength: 25,
        lengthMenu: [10, 25, 50, 100],
        language: {
            lengthMenu: "عرض _MENU_ عنصر",
            search: "بحث:",
            info: "عرض _START_ إلى _END_ من إجمالي _TOTAL_ عنصر",
            infoEmpty: "لا توجد عناصر للعرض",
            infoFiltered: "(تمت تصفيتها من _MAX_ عنصر)",
            zeroRecords: "لم يتم العثور على سجلات مطابقة",
            paginate: {
                first: "الأول",
                last: "الأخير",
                next: "التالي",
                previous: "السابق"
            }
        },
        columnDefs: [],
        dom: '<"row"<"col-sm-12 col-md-12"l>><"row"<"col-sm-12"tr>><"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        autoWidth: true,
        scrollX: false,
        scrollY: false,
        scrollCollapse: false,
        paging: true,
        info: true
    };
    
    // دمج الإعدادات
    const mergedOptions = {...defaultOptions, ...options};
    
    // تهيئة البحث في حالة وجود مربع بحث خارجي
    setupTableSearch(tableId);
    
    // إعداد تغيير عدد العناصر المعروضة
    setupTableLengthChange(tableId);
    
    // ترقيم الصفوف
    addTableRowNumbers(tableId);
    
    // فلترة الجدول تلقائيًا لأي معلمات بحث في عنوان URL
    autoFilterFromURL(tableId);
    
    // تعديل عرض الجدول ليناسب محتواه
    adjustTableWidth(tableId);
    
    // إصلاح مشكلة عدد الأعمدة قبل تهيئة DataTables
    fixColumnCount(tableId);
    
    // تهيئة DataTables
    if ($.fn.DataTable) {
        // تعديل إعدادات DataTables ليستخدم عناصر التحكم الخارجية إذا وجدت
        // التحقق من وجود عناصر تحكم خارجية
        const hasExternalSearch = document.querySelector('.table-search[data-table="' + tableId + '"]') !== null;
        const hasExternalLength = document.querySelector('.table-length[data-table="' + tableId + '"]') !== null;
        
        // إذا كانت عناصر تحكم خارجية موجودة، تعديل dom للاستفادة منها
        if (hasExternalSearch || hasExternalLength) {
            // ضبط dom لعدم إظهار عناصر التحكم المدمجة إذا كانت الخارجية موجودة
            let domConfig = '<"row"';
            if (!hasExternalLength) {
                domConfig += '<"col-sm-12 col-md-6"l>';
            } else {
                domConfig += '<"col-sm-12 col-md-6">';
            }
            if (!hasExternalSearch) {
                domConfig += '<"col-sm-12 col-md-6"f>';
            } else {
                domConfig += '<"col-sm-12 col-md-6">';
            }
            domConfig += '><"row"<"col-sm-12"tr>><"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>';
            
            // تحديث الإعدادات
            mergedOptions.dom = domConfig;
        }
        
        // تهيئة DataTables
        const dataTable = $('#' + tableId).DataTable(mergedOptions);
        
        // ربط البحث الخارجي إذا وجد
        if (hasExternalSearch) {
            const searchInput = document.querySelector('.table-search[data-table="' + tableId + '"]');
            searchInput.addEventListener('keyup', function() {
                dataTable.search(this.value).draw();
            });
        }
        
        // ربط تغيير العدد الخارجي إذا وجد
        if (hasExternalLength) {
            const lengthSelect = document.querySelector('.table-length[data-table="' + tableId + '"]');
            lengthSelect.addEventListener('change', function() {
                dataTable.page.len(parseInt(this.value)).draw();
            });
            
            // تعيين القيمة الافتراضية
            const savedLength = localStorage.getItem('table_' + tableId + '_length');
            if (savedLength) {
                lengthSelect.value = savedLength;
                dataTable.page.len(parseInt(savedLength)).draw();
            }
        }
        
        // تخزين مرجع Datatables في سمة البيانات على الجدول
        document.getElementById(tableId).dataTable = dataTable;
        
        // إضافة استجابة عند تغيير مقاس الشاشة
        window.addEventListener('resize', function() {
            if (dataTable) {
                dataTable.columns.adjust();
                adjustTableWidth(tableId);
            }
        });
    }
}

// وظيفة لإصلاح مشكلة عدم تطابق عدد الأعمدة في الجدول
function fixColumnCount(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // الحصول على عدد الأعمدة في رأس الجدول
    const headColumns = table.querySelectorAll('thead th').length;
    
    // التحقق من وجود خلية td واحدة في حالة عدم وجود بيانات
    const emptyRow = table.querySelector('tbody tr td[colspan]');
    if (emptyRow) {
        // تحديث عدد الأعمدة في خلية الرسالة الفارغة
        emptyRow.setAttribute('colspan', headColumns);
    }
    
    // التحقق من عدد الأعمدة في كل صف من صفوف البيانات
    const dataRows = table.querySelectorAll('tbody tr');
    dataRows.forEach(row => {
        // تجاهل الصفوف التي تحتوي على خلية colspan
        if (row.querySelector('td[colspan]')) {
            return;
        }
        
        const cellCount = row.querySelectorAll('td').length;
        if (cellCount > 0 && cellCount !== headColumns) {
            console.warn(`تصحيح عدد الأعمدة في الجدول ${tableId}: الرأس=${headColumns}, الصف=${cellCount}`);
            
            // إضافة أعمدة فارغة إذا كان هناك نقص
            if (cellCount < headColumns) {
                for (let i = 0; i < headColumns - cellCount; i++) {
                    const newCell = document.createElement('td');
                    newCell.className = 'empty-cell';
                    row.appendChild(newCell);
                }
            }
        }
    });
}

// وظيفة لتعديل عرض الجدول ليناسب محتواه
function adjustTableWidth(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // تأكد من أن الجدول يأخذ 100% من عرض الحاوية
    table.style.width = '100%';
    
    // تعديل عرض الأعمدة بناءً على محتواها
    const headerCells = table.querySelectorAll('thead th');
    headerCells.forEach((cell, index) => {
        // تخصيص عرض لعمود الإجراءات
        if (cell.classList.contains('col-actions')) {
            cell.style.width = 'auto';
            cell.style.minWidth = '100px';
        }
    });
}

// تهيئة مربع البحث الخارجي
function setupTableSearch(tableId) {
    const searchInput = document.querySelector('.table-search[data-table="' + tableId + '"]');
    if (!searchInput) return;
    
    // إضافة مستمع حدث للبحث
    searchInput.addEventListener('keyup', function() {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        if (table.dataTable) {
            // استخدام DataTables إذا كان متاحًا
            table.dataTable.search(this.value).draw();
        } else {
            // تنفيذ بحث بسيط باستخدام JavaScript
            customTableSearch(tableId, this.value);
        }
    });
}

// تنفيذ البحث البسيط باستخدام JavaScript فقط (للمتصفحات التي لا تستخدم DataTables)
function customTableSearch(tableId, searchValue) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tbody tr');
    const normalizedSearch = searchValue.toLowerCase().trim();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(normalizedSearch)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// تهيئة تغيير عدد العناصر المعروضة
function setupTableLengthChange(tableId) {
    const lengthSelect = document.querySelector('.table-length[data-table="' + tableId + '"]');
    
    // إذا كان عنصر التحكم في العدد موجودًا في الصفحة
    if (lengthSelect) {
        console.log('Found length select for table: ' + tableId); // للتشخيص
        
        lengthSelect.addEventListener('change', function() {
            const table = document.getElementById(tableId);
            if (!table) return;
            
            const newLength = parseInt(this.value);
            console.log('Changed length to: ' + newLength); // للتشخيص
            
            // استخدام DataTables API إذا كان متاحًا
            if (table.dataTable) {
                table.dataTable.page.len(newLength).draw();
                console.log('Applied length change to DataTable: ' + newLength);
            } else if ($.fn.DataTable && $.fn.DataTable.isDataTable('#' + tableId)) {
                // محاولة أخرى للوصول إلى DataTable
                const dtInstance = $('#' + tableId).DataTable();
                dtInstance.page.len(newLength).draw();
                console.log('Applied length change using jQuery: ' + newLength);
            } else {
                // حفظ التفضيل في التخزين المحلي
                localStorage.setItem('table_' + tableId + '_length', newLength);
                console.log('Saved length preference to localStorage: ' + newLength);
                
                // إعادة تحميل الصفحة مع معلمة العدد الجديدة
                const url = new URL(window.location.href);
                url.searchParams.set('length', newLength);
                window.location.href = url.toString();
            }
        });
        
        // محاولة تعيين القيمة الافتراضية من التخزين المحلي
        const savedLength = localStorage.getItem('table_' + tableId + '_length');
        if (savedLength) {
            lengthSelect.value = savedLength;
            console.log('Applied saved length from localStorage: ' + savedLength);
            
            // تطبيق الطول المحفوظ على الجدول إذا كان متاحًا
            const table = document.getElementById(tableId);
            if (table && table.dataTable) {
                table.dataTable.page.len(parseInt(savedLength)).draw();
            }
        }
    } else {
        console.log('Length select control not found for table: ' + tableId); // للتشخيص
    }
}

// إضافة أرقام الصفوف للجدول
function addTableRowNumbers(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // التحقق من وجود عمود للأرقام
    const hasNumberColumn = table.querySelector('thead th.row-number');
    if (!hasNumberColumn) return;
    
    // إضافة أرقام للصفوف
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach((row, index) => {
        const numberCell = row.querySelector('td.row-number');
        if (numberCell) {
            numberCell.textContent = index + 1;
        }
    });
}

// استخراج معلمات التصفية من عنوان URL وتطبيقها تلقائيًا
function autoFilterFromURL(tableId) {
    const urlParams = new URLSearchParams(window.location.search);
    const searchParam = urlParams.get('search');
    
    if (searchParam) {
        const searchInput = document.querySelector('.table-search[data-table="' + tableId + '"]');
        if (searchInput) {
            searchInput.value = searchParam;
            
            // تطبيق البحث
            const table = document.getElementById(tableId);
            if (table && table.dataTable) {
                table.dataTable.search(searchParam).draw();
            } else {
                customTableSearch(tableId, searchParam);
            }
        }
    }
}

// وظيفة للتصدير إلى CSV
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // استخراج بيانات الجدول
    const rows = [];
    
    // استخراج رؤوس الأعمدة
    const headers = [];
    const headerCells = table.querySelectorAll('thead th');
    headerCells.forEach(cell => {
        // تجاهل عمود الإجراءات
        if (!cell.classList.contains('col-actions')) {
            // إزالة علامات الترتيب والأيقونات
            const headerText = cell.textContent.replace(/^\s*|\s*$/g, '').replace(/[▲▼]/, '');
            headers.push(headerText);
        }
    });
    rows.push(headers);
    
    // استخراج بيانات الصفوف
    const dataCells = table.querySelectorAll('tbody tr');
    dataCells.forEach(row => {
        const rowData = [];
        row.querySelectorAll('td').forEach(cell => {
            // تجاهل عمود الإجراءات
            if (!cell.classList.contains('col-actions')) {
                // تنظيف البيانات وإزالة الفواصل الداخلية
                const cellContent = cell.textContent.trim().replace(/\s+/g, ' ');
                // استبدال الفواصل بفاصلة منقوطة لمنع تداخلها مع فواصل CSV
                rowData.push('"' + cellContent.replace(/"/g, '""') + '"');
            }
        });
        if (rowData.length > 0) {
            rows.push(rowData);
        }
    });
    
    // إنشاء محتوى CSV مع BOM لدعم العربية
    // BOM (Byte Order Mark) يساعد برامج مثل Excel في التعرف على ترميز UTF-8
    const BOM = "\uFEFF"; // علامة ترتيب البايت لدعم UTF-8
    let csvContent = BOM;
    
    rows.forEach(rowArray => {
        const row = rowArray.join(",");
        csvContent += row + "\r\n";
    });
    
    // إنشاء رابط التنزيل باستخدام Blob بدلاً من URI مباشرة
    // Blob يتعامل مع محتوى النصوص بشكل أفضل للغات غير اللاتينية
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // إنشاء عنصر الرابط وتنفيذ التحميل
    if (navigator.msSaveBlob) { // للمتصفح IE
        navigator.msSaveBlob(blob, (filename || 'export.csv'));
    } else {
        const link = document.createElement("a");
        
        // إنشاء URL من الـ Blob
        const url = URL.createObjectURL(blob);
        
        link.setAttribute("href", url);
        link.setAttribute("download", filename || "export.csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        
        // بدء التنزيل
        link.click();
        
        // حذف العنصر والرابط من الذاكرة
        setTimeout(function() {
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        }, 100);
    }
}

// إضافة مستمع للأحداث عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // تفعيل أزرار التصدير
    const exportButtons = document.querySelectorAll('.btn-export-table');
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTable = this.getAttribute('data-table');
            const filename = this.getAttribute('data-filename') || 'export.csv';
            exportTableToCSV(targetTable, filename);
        });
    });
    
    // تفعيل أزرار تصدير Excel
    const exportExcelButtons = document.querySelectorAll('.btn-export-excel');
    exportExcelButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTable = this.getAttribute('data-table');
            const filename = this.getAttribute('data-filename') || 'export.xlsx';
            exportTableToExcel(targetTable, filename);
        });
    });
});

/**
 * تحديث بيانات الجدول
 * @param {string} tableId - معرف الجدول (مطلوب)
 * @param {Array} data - البيانات الجديدة (مطلوب)
 */
function updateTableData(tableId, data) {
    if (!window.dataTables || !window.dataTables[tableId]) {
        console.error(`الجدول ${tableId} غير مهيأ بعد`);
        return;
    }
    
    const table = window.dataTables[tableId];
    
    // حذف جميع الصفوف الحالية
    table.clear();
    
    // إضافة البيانات الجديدة
    table.rows.add(data);
    
    // إعادة رسم الجدول
    table.draw();
}

/**
 * استرجاع بيانات الجدول عبر AJAX
 * @param {string} tableId - معرف الجدول (مطلوب)
 * @param {string} url - رابط استرجاع البيانات (مطلوب)
 * @param {Object} data - بيانات الطلب (اختياري)
 */
function loadTableData(tableId, url, data = {}) {
    $.ajax({
        url: url,
        type: 'GET',
        data: data,
        dataType: 'json',
        success: function(response) {
            updateTableData(tableId, response.data);
        },
        error: function(xhr, status, error) {
            console.error('خطأ في استرجاع البيانات:', error);
        }
    });
}

/**
 * تحسين أداء الجدول بتوقيف أحداث إعادة الرسم المؤقتة
 * @param {string} tableId - معرف الجدول (مطلوب)
 * @param {Function} callback - الدالة التي ستنفذ (مطلوب)
 */
function withTableOptimization(tableId, callback) {
    if (!window.dataTables || !window.dataTables[tableId]) {
        console.error(`الجدول ${tableId} غير مهيأ بعد`);
        return;
    }
    
    const table = window.dataTables[tableId];
    
    // توقيف إعادة الرسم
    table.processing(true);
    
    // تنفيذ الدالة
    callback(table);
    
    // إعادة تمكين الرسم
    table.processing(false);
    table.draw();
}

/**
 * وظيفة تصدير البيانات إلى ملف Excel
 * تدعم اللغة العربية بشكل كامل
 * @param {string} tableId - معرف الجدول
 * @param {string} filename - اسم الملف
 */
function exportTableToExcel(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    // إنشاء نسخة من الجدول لإزالة أعمدة الإجراءات منها قبل التصدير
    const tableCopy = table.cloneNode(true);
    
    // حذف عمود الإجراءات (آخر عمود)
    const actionColumnIndex = Array.from(tableCopy.querySelectorAll('thead th'))
        .findIndex(th => th.classList.contains('col-actions'));
    
    if (actionColumnIndex !== -1) {
        // حذف خلايا الرأس المرتبطة بعمود الإجراءات
        const headers = tableCopy.querySelectorAll('thead tr th');
        headers.forEach(row => {
            const actionHeader = row.querySelector('.col-actions');
            if (actionHeader) {
                actionHeader.parentNode.removeChild(actionHeader);
            }
        });
        
        // حذف خلايا البيانات المرتبطة بعمود الإجراءات
        const rows = tableCopy.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length > actionColumnIndex) {
                const actionCell = cells[actionColumnIndex];
                actionCell.parentNode.removeChild(actionCell);
            }
        });
    }
    
    // إنشاء ورقة عمل Excel
    const ws = XLSX.utils.table_to_sheet(tableCopy, {
        raw: true,
        display: true,
        headers: true
    });
    
    // تعديل عرض الأعمدة لتناسب المحتوى
    const colWidths = [];
    for (const cellRef in ws) {
        if (cellRef[0] === '!') continue; // تجاهل الخلايا الخاصة مثل !ref
        
        const cell = ws[cellRef];
        const colIndex = XLSX.utils.decode_col(cellRef.replace(/\d+$/, ''));
        
        if (cell && cell.v) {
            const cellWidth = String(cell.v).length;
            colWidths[colIndex] = Math.max(colWidths[colIndex] || 0, cellWidth);
        }
    }
    
    // تعيين عرض الأعمدة
    ws['!cols'] = colWidths.map(width => ({ width: Math.min(width + 2, 30) })); // حد أقصى 30 لعرض العمود
    
    // إعداد ورقة العمل للدعم الصحيح للغة العربية (اتجاه من اليمين إلى اليسار)
    if (!ws['!margins']) ws['!margins'] = {};
    ws['!margins'].right = 0.7;
    ws['!margins'].left = 0.7;
    
    // إنشاء مصنف Excel جديد
    const wb = XLSX.utils.book_new();
    
    // إضافة خصائص المصنف
    wb.Props = {
        Title: filename.replace('.xlsx', ''),
        Subject: 'بيانات مصدرة',
        Author: document.title,
        CreatedDate: new Date()
    };
    
    // إضافة ورقة العمل إلى المصنف
    XLSX.utils.book_append_sheet(wb, ws, 'البيانات المصدرة');
    
    // تنزيل الملف
    XLSX.writeFile(wb, filename || 'export.xlsx');
}

/**
 * تصدير الجدول إلى PDF
 * @param {string} tableId - معرف الجدول (مطلوب)
 * @param {string} filename - اسم الملف (اختياري، افتراضي: 'export')
 */
function exportTableToPDF(tableId, filename = 'export') {
    if (!window.dataTables || !window.dataTables[tableId]) {
        console.error(`الجدول ${tableId} غير مهيأ بعد`);
        return;
    }
    
    if (!$.fn.dataTable.buttons) {
        console.error('مكتبة DataTables Buttons غير متوفرة');
        return;
    }
    
    const table = window.dataTables[tableId];
    
    // إنشاء زر تصدير مؤقت
    const exportBtn = new $.fn.dataTable.Buttons(table, {
        buttons: [
            {
                extend: 'pdf',
                text: 'تصدير',
                filename: filename,
                title: document.title,
                orientation: 'landscape',
                pageSize: 'A4',
                exportOptions: {
                    columns: ':visible'
                },
                customize: function(doc) {
                    // تخصيص مستند PDF
                    doc.defaultStyle.font = 'Cairo';
                    doc.defaultStyle.alignment = 'right';
                    doc.styles.tableHeader.alignment = 'right';
                }
            }
        ]
    });
    
    // تنفيذ عملية التصدير
    exportBtn.buttons().trigger();
}

/**
 * إضافة أزرار التصدير إلى الجدول
 * @param {string} tableId - معرف الجدول (مطلوب)
 * @param {string} containerSelector - محدد HTML لحاوية الأزرار (مطلوب)
 */
function addExportButtons(tableId, containerSelector) {
    if (!$.fn.dataTable.buttons) {
        console.error('مكتبة DataTables Buttons غير متوفرة');
        return;
    }
    
    const container = $(containerSelector);
    
    if (container.length === 0) {
        console.error(`حاوية الأزرار "${containerSelector}" غير موجودة`);
        return;
    }
    
    // إضافة أزرار التصدير
    const exportButtons = $(`
        <div class="export-buttons">
            <button type="button" class="btn btn-sm btn-outline-primary export-excel">
                <i class="far fa-file-excel me-1"></i> Excel
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger export-pdf ms-2">
                <i class="far fa-file-pdf me-1"></i> PDF
            </button>
        </div>
    `);
    
    // إضافة الأزرار إلى الحاوية
    container.append(exportButtons);
    
    // ربط أحداث النقر بالأزرار
    exportButtons.find('.export-excel').on('click', function() {
        exportTableToExcel(tableId);
    });
    
    exportButtons.find('.export-pdf').on('click', function() {
        exportTableToPDF(tableId);
    });
}

// إعداد الأحداث عند اكتمال تحميل المستند
$(document).ready(function() {
    // البحث عن جميع جداول البيانات وتهيئتها تلقائيًا
    $('.transaction-table[data-auto-init="true"]').each(function() {
        const tableId = $(this).attr('id');
        const options = {
            responsive: $(this).data('responsive') !== false,
            sortable: $(this).data('sortable') !== false,
            searchable: $(this).data('searchable') !== false,
            pageLength: $(this).data('page-length') || 10,
            order: $(this).data('order') ? JSON.parse($(this).data('order')) : [0, 'asc']
        };
        
        initGlobalTable(tableId, options);
    });
}); 