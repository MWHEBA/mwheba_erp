"""
أداة مساعدة لإنهاء جميع عمليات Python قبل تشغيل سكريبت reset_migrations.py
"""

import os
import sys
import subprocess
import time
import ctypes
import platform
import argparse

# تعريف ألوان الطباعة
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_colored(text, color=None):
    """
    طباعة نص ملون في الطرفية
    """
    if color:
        print(f"{color}{text}{RESET}")
    else:
        print(text)

def is_admin():
    """
    التحقق مما إذا كان السكريبت يعمل بصلاحيات المسؤول
    """
    try:
        if platform.system() == 'Windows':
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            # على أنظمة Unix، نتحقق إذا كان معرف المستخدم هو 0 (المستخدم الجذر)
            return os.getuid() == 0
    except:
        return False

def kill_all_python_processes(auto_continue=False):
    """
    إنهاء جميع عمليات Python باستثناء العملية الحالية
    
    Parameters:
        auto_continue (bool): إذا كان True، سيستمر البرنامج حتى لو فشل في إنهاء بعض العمليات
    """
    # تلقائيًا جعل auto_continue بقيمة True عند الاستدعاء من ملف آخر
    # هذا سيساعد عند استدعاء الملف من reset_migrations.py
    if not sys.argv[0].endswith('kill_python_processes.py'):
        auto_continue = True

    current_pid = os.getpid()
    print_colored(f"[!] معرف العملية الحالية: {current_pid} (سيتم تجاهله)", YELLOW)
    
    success = False
    
    try:
        if platform.system() == 'Windows':
            # الحصول على قائمة بجميع عمليات Python الجارية
            print_colored("[*] البحث عن عمليات Python الجارية...", BLUE)
            
            # استخدام tasklist لعرض جميع العمليات المرتبطة بـ Python
            tasklist_process = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True
            )
            
            if tasklist_process.returncode != 0:
                print_colored("[!] فشل في الحصول على قائمة العمليات", RED)
                return auto_continue  # إرجاع auto_continue إذا فشل الحصول على القائمة
            
            output_lines = tasklist_process.stdout.strip().split('\n')
            
            # تجاهل السطر الأول (العناوين)
            if len(output_lines) > 1:
                python_processes = []
                for line in output_lines[1:]:
                    if '"python.exe"' in line:
                        # استخراج معرف العملية (PID)
                        parts = line.split('","')
                        if len(parts) > 1:
                            pid = parts[1].replace('"', '')
                            try:
                                pid = int(pid)
                                if pid != current_pid:  # تجاهل العملية الحالية
                                    python_processes.append(pid)
                            except ValueError:
                                pass
                
                if not python_processes:
                    print_colored("[✓] لا توجد عمليات Python أخرى تعمل حاليًا", GREEN)
                    return True
                
                print_colored(f"[!] تم العثور على {len(python_processes)} عملية Python: {python_processes}", YELLOW)
                
                # إنهاء العمليات المحددة
                killed_count = 0
                for pid in python_processes:
                    try:
                        print_colored(f"[*] محاولة إنهاء العملية {pid}...", BLUE)
                        
                        if is_admin():
                            # إذا كان لدينا صلاحيات المسؤول، استخدم /F لإجبار العملية على الإنهاء
                            result = subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, text=True, check=False)
                            if result.returncode == 0:
                                print_colored(f"[✓] تم إنهاء العملية {pid} بنجاح", GREEN)
                                killed_count += 1
                        else:
                            # محاولة إنهاء العملية بشكل عادي أولاً
                            result = subprocess.run(['taskkill', '/PID', str(pid)], capture_output=True, text=True, check=False)
                            
                            # إذا نجحت
                            if result.returncode == 0:
                                print_colored(f"[✓] تم إنهاء العملية {pid} بنجاح", GREEN)
                                killed_count += 1
                            else:
                                # محاولة أخرى باستخدام /F
                                print_colored("[*] محاولة استخدام الإنهاء القسري...", BLUE)
                                result = subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, text=True, check=False)
                                if result.returncode == 0:
                                    print_colored(f"[✓] تم إنهاء العملية {pid} بنجاح باستخدام الطريقة القسرية", GREEN)
                                    killed_count += 1
                                else:
                                    print_colored(f"[!] فشل في إنهاء العملية {pid}", RED)
                    except Exception as e:
                        print_colored(f"[!] خطأ أثناء إنهاء العملية {pid}: {str(e)}", RED)
                
                # طباعة ملخص
                if killed_count == len(python_processes):
                    print_colored(f"[✓] تم إنهاء جميع عمليات Python ({killed_count} عملية) بنجاح", GREEN)
                    success = True
                else:
                    print_colored(f"[!] تم إنهاء {killed_count} من أصل {len(python_processes)} عملية Python", YELLOW)
                    
                    # محاولة نهائية باستخدام أمر قتل كل عمليات Python
                    print_colored("[*] محاولة نهائية لإنهاء جميع عمليات Python المتبقية...", BLUE)
                    subprocess.run(
                        ['taskkill', '/F', '/IM', 'python.exe', '/T'],
                        capture_output=True,
                        check=False
                    )
                    
                    # التحقق من العمليات المتبقية
                    time.sleep(2)
                    check_process = subprocess.run(
                        ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                        capture_output=True,
                        text=True
                    )
                    
                    remaining = 0
                    for line in check_process.stdout.strip().split('\n')[1:]:
                        if '"python.exe"' in line:
                            parts = line.split('","')
                            if len(parts) > 1:
                                try:
                                    pid = int(parts[1].replace('"', ''))
                                    if pid != current_pid:
                                        remaining += 1
                                except ValueError:
                                    pass
                    
                    if remaining == 0:
                        print_colored("[✓] تم إنهاء جميع عمليات Python بنجاح", GREEN)
                        success = True
                    else:
                        print_colored(f"[!] لا تزال هناك {remaining} عملية Python قيد التشغيل", RED)
                        print_colored("    قد تحتاج إلى إنهاء هذه العمليات يدويًا باستخدام Task Manager", YELLOW)
                        if auto_continue:
                            print_colored("[*] متابعة العملية رغم وجود عمليات لم يتم إنهاؤها", BLUE)
                            success = True  # لاستمرار البرنامج
                        else:
                            success = False
            else:
                print_colored("[✓] لا توجد عمليات Python أخرى تعمل حاليًا", GREEN)
                success = True
        else:
            # على أنظمة Unix، استخدم pkill
            print_colored("[*] إنهاء عمليات Python على نظام Unix...", BLUE)
            os.system(f"pkill -9 -f python")
            print_colored("[✓] تم إنهاء عمليات Python", GREEN)
            success = True
    except Exception as e:
        print_colored(f"[!] خطأ أثناء إنهاء عمليات Python: {str(e)}", RED)
        success = False
    
    return success

def run_reset_migrations(args):
    """
    تشغيل سكريبت reset_migrations.py مع الخيارات المحددة
    """
    # التأكد من إضافة --no-db-reset إذا لم يتم تحديده
    has_no_db_reset = '--no-db-reset' in args
    
    if not has_no_db_reset:
        print_colored("[!] إضافة خيار --no-db-reset لتجنب مشاكل قفل قاعدة البيانات", YELLOW)
        args.append('--no-db-reset')
    
    # بناء الأمر الكامل
    command = [sys.executable, 'reset_migrations.py'] + args
    command_str = ' '.join(command)
    
    print_colored(f"[*] تشغيل: {command_str}", BLUE)
    
    try:
        # تشغيل السكريبت وتمرير المخرجات مباشرة إلى الطرفية
        process = subprocess.Popen(command, stdout=None, stderr=None)
        process.wait()
        
        if process.returncode == 0:
            print_colored(f"[✓] اكتمل سكريبت reset_migrations.py بنجاح! (رمز الخروج: {process.returncode})", GREEN)
            return True
        else:
            print_colored(f"[!] فشل تنفيذ سكريبت reset_migrations.py (رمز الخروج: {process.returncode})", RED)
            return False
    except Exception as e:
        print_colored(f"[!] خطأ أثناء تشغيل سكريبت reset_migrations.py: {str(e)}", RED)
        return False

if __name__ == "__main__":
    try:
        # إنشاء معالج الوسائط
        parser = argparse.ArgumentParser(description='إدارة عمليات Python وتشغيل سكريبت reset_migrations.py')
        parser.add_argument('--reset-only', action='store_true', help='إنهاء عمليات Python دون تشغيل سكريبت reset_migrations.py')
        parser.add_argument('rest', nargs='*', help='وسائط إضافية لتمريرها إلى سكريبت reset_migrations.py')
        
        args = parser.parse_args()
        
        print_colored("=" * 50, BLUE)
        print_colored("MWHEBA ERP - أداة إدارة عمليات Python", GREEN)
        print_colored("=" * 50, BLUE)
        
        # محاولة إنهاء عمليات Python
        print_colored("\n[*] محاولة إنهاء عمليات Python الجارية...", BLUE)
        killed = kill_all_python_processes()
        
        if not killed:
            print_colored("[!] تنبيه: لم يتم إنهاء بعض عمليات Python. قد تواجه مشاكل.", YELLOW)
            choice = input("هل تريد المتابعة على أي حال؟ (y/n): ").strip().lower()
            if choice != 'y':
                print_colored("[*] تم إلغاء العملية بواسطة المستخدم.", BLUE)
                sys.exit(1)
        
        # إذا تم تحديد --reset-only، لا تقم بتشغيل سكريبت reset_migrations.py
        if args.reset_only:
            print_colored("\n[*] تم إنهاء عمليات Python بنجاح. لن يتم تشغيل سكريبت reset_migrations.py.", BLUE)
            print_colored("[*] إذا كنت تريد تشغيل سكريبت reset_migrations.py، قم بإعادة تشغيل بدون --reset-only.", BLUE)
        else:
            # تشغيل سكريبت reset_migrations.py مع الوسائط المحددة
            print_colored("\n[*] تشغيل سكريبت reset_migrations.py...", BLUE)
            success = run_reset_migrations(args.rest)
            
            if success:
                print_colored("\n[✓] تم إكمال العملية بنجاح!", GREEN)
            else:
                print_colored("\n[!] لم تكتمل العملية بنجاح. يرجى مراجعة الأخطاء أعلاه.", RED)
        
        print_colored("\n" + "=" * 50, BLUE)
        
    except KeyboardInterrupt:
        print_colored("\n[!] تم إيقاف العملية بواسطة المستخدم.", YELLOW)
    except Exception as e:
        print_colored(f"\n[!] حدث خطأ غير متوقع: {str(e)}", RED)
        import traceback
        traceback.print_exc() 