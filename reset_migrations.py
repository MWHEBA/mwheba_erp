import os
import shutil
import glob
import subprocess
import sys
import time
import datetime
import argparse
import platform
from pathlib import Path
from dotenv import load_dotenv
import re
import fnmatch

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# تحديد مجلد المشروع
BASE_DIR = Path(__file__).resolve().parent
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

# التطبيقات التي تحتوي على ملفات ترحيل
APPS = [
    d for d in os.listdir(BASE_DIR)
    if os.path.isdir(os.path.join(BASE_DIR, d)) and os.path.exists(os.path.join(BASE_DIR, d, "migrations"))
]

# تحديد نوع قاعدة البيانات
def get_db_config():
    """استرجاع إعدادات قاعدة البيانات من متغيرات البيئة."""
    # استخدام SQLite بشكل افتراضي دائمًا
    db_config = {
        'type': 'sqlite',
        'name': os.getenv('DB_NAME', 'mwheba_erp'),
    }
    
    return db_config

def print_colored(text, color="white", style="normal", background=None):
    """طباعة نص ملون في الطرفية."""
    colors = {
        "black": "30", "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "cyan": "36", "white": "37"
    }
    styles = {
        "normal": "0", "bold": "1", "underline": "4", "blink": "5", "invert": "7"
    }
    backgrounds = {
        "black": "40", "red": "41", "green": "42", "yellow": "43",
        "blue": "44", "magenta": "45", "cyan": "46", "white": "47"
    }
    
    color_code = colors.get(color, "37")
    style_code = styles.get(style, "0")
    bg_code = f";{backgrounds.get(background)}" if background in backgrounds else ""
    
    print(f"\033[{style_code};{color_code}{bg_code}m{text}\033[0m")

def backup_project():
    """إنشاء نسخة احتياطية من المشروع كما هو."""
    print_colored("\n🔄 Creating project backup...", color="cyan", style="bold")
    
    source_folder = os.path.abspath(os.getcwd())
    # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجودًا
    backup_root = os.path.join(os.path.dirname(source_folder), "MWHEBA_BACKUPS")
    os.makedirs(backup_root, exist_ok=True)
    
    # إنشاء مجلد خاص بتاريخ اليوم
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_backup_folder = os.path.join(backup_root, today)
    os.makedirs(today_backup_folder, exist_ok=True)
    
    # Ask user for custom label
    custom_label = input("🔒 Backup Name (leave empty for auto-generated): ").strip()
    if not custom_label:
        custom_label = datetime.datetime.now().strftime("%H-%M-%S")
    
    # تنظيف الاسم المدخل من أي أحرف غير صالحة لاسم الملف
    custom_label = re.sub(r'[^\w\-\.]', '_', custom_label)
    
    base_name = "MWHEBA_ERP"
    zip_path = os.path.join(today_backup_folder, f"{base_name}_{custom_label}")
    
    try:
        # Create temporary folder with the files to backup
        # This allows excluding specific directories
        temp_dir = os.path.join(today_backup_folder, f"temp_{custom_label}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Folders to exclude from backup
        exclude_patterns = [
            "__pycache__", "*.pyc",
            ".git", ".github",
            "venv", "env", ".venv", ".env",
            "node_modules", "staticfiles", "media"
        ]
        
        print_colored("📦 Copying files (excluding unnecessary folders)...", color="blue")
        # Copy files to temp directory, excluding unwanted folders
        for item in os.listdir(source_folder):
            # Skip excluded patterns
            if any(fnmatch.fnmatch(item, pattern) for pattern in exclude_patterns):
                continue
                
            source_item = os.path.join(source_folder, item)
            dest_item = os.path.join(temp_dir, item)
            
            if os.path.isdir(source_item):
                # Use shutil.copytree with ignore function
                shutil.copytree(
                    source_item, 
                    dest_item,
                    ignore=shutil.ignore_patterns(*exclude_patterns),
                    dirs_exist_ok=True
                )
            else:
                # Copy files
                shutil.copy2(source_item, dest_item)
        
        # Create backup with built-in shutil function
        print_colored("📦 Creating zip archive...", color="blue")
        shutil.make_archive(zip_path, 'zip', temp_dir)
        
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        print_colored(f"✅ Backup created successfully: {zip_path}.zip", color="green")
        return True
    except Exception as e:
        print_colored(f"❌ Error creating backup: {e}", color="red")
        print_colored("ℹ️ Continuing without backup...", color="blue")
        return False

def clear_migrations():
    """Delete migration files for each app."""
    print_colored("\n🧹 Removing old migration files...", color="cyan", style="bold")
    
    for app in APPS:
        migrations_path = os.path.join(BASE_DIR, app, "migrations")
        if os.path.exists(migrations_path):
            # الاحتفاظ بملف __init__.py فقط
            for file in os.listdir(migrations_path):
                file_path = os.path.join(migrations_path, file)
                if os.path.isfile(file_path) and file != "__init__.py":
                    os.remove(file_path)
                    print_colored(f"  🗑️ Removed: {app}/migrations/{file}", color="yellow")
            
            # حذف مجلد __pycache__ إن وجد
            pycache_dir = os.path.join(migrations_path, '__pycache__')
            if os.path.exists(pycache_dir):
                shutil.rmtree(pycache_dir)
                print_colored(f"  🗑️ Removed: {app}/migrations/__pycache__", color="yellow")
    
    print_colored("✅ All migration files successfully removed.", color="green")
    return True

def provide_manual_instructions():
    """تقديم تعليمات يدوية للمستخدم لحل مشكلة قفل ملف قاعدة البيانات."""
    print_colored("\n📋 MANUAL DATABASE UNLOCK INSTRUCTIONS", color="cyan", style="bold")
    print_colored("Follow these steps to manually unlock the database file:", color="white")
    print_colored("1. Download Process Explorer from Microsoft: https://docs.microsoft.com/en-us/sysinternals/downloads/process-explorer", color="blue")
    print_colored("2. Run Process Explorer as Administrator", color="blue")
    print_colored("3. Press Ctrl+F to open the search dialog", color="blue")
    print_colored(f"4. Search for 'db.sqlite3' to find any process using the database file", color="blue")
    print_colored("5. For each process found, right-click it and select 'Kill Process'", color="blue")
    print_colored("6. Alternatively, you can reboot your computer to release all file locks", color="blue")
    print_colored("7. After killing all processes, try running this script again", color="blue")
    print_colored("\nAlternative Method:", color="white")
    print_colored("1. Close all Python/Django related applications (including any running servers)", color="blue")
    print_colored("2. Manually rename or delete the db.sqlite3 file", color="blue")
    print_colored(f"3. Run this script again with the --no-db-reset flag:", color="blue")
    print_colored("   python reset_migrations.py --no-db-reset", color="green")
    print_colored("\n📢 Press Enter to continue...", color="yellow")
    input()

def rename_database_manually():
    """محاولة إعادة تسمية قاعدة البيانات يدويًا."""
    db_path = os.path.join(BASE_DIR, "db.sqlite3")
    if os.path.exists(db_path):
        # إنشاء مجلد للنسخ الاحتياطية السابقة إذا لم يكن موجودًا
        old_db_dir = os.path.join(BASE_DIR, "old_databases")
        os.makedirs(old_db_dir, exist_ok=True)
        
        # إنشاء اسم جديد بالتاريخ والوقت
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_db_path = os.path.join(old_db_dir, f"db.sqlite3.{now}.bak")
        
        print_colored("\n🔄 MANUAL DATABASE RENAME", color="cyan", style="bold")
        print_colored(f"Current database: {db_path}", color="white")
        print_colored(f"New backup path: {new_db_path}", color="white")
        print_colored("\nPlease close all applications that might be using the database.", color="yellow")
        print_colored("Then follow the instructions:", color="yellow")
        print_colored("1. Press Enter when you're ready to try renaming the file.", color="blue")
        input()
        
        try:
            # محاولة نسخ الملف
            print_colored("🔄 Copying database file to backup location...", color="blue")
            shutil.copy2(db_path, new_db_path)
            print_colored(f"✅ Database copied to: {new_db_path}", color="green")
            
            # محاولة إنشاء ملف فارغ
            print_colored("🔄 Creating empty database file...", color="blue")
            with open(db_path, 'w') as f:
                pass
            print_colored("✅ Empty database file created successfully", color="green")
            return True
        except Exception as e:
            print_colored(f"❌ Error: {e}", color="red")
            print_colored("❓ Would you like to try manual steps to resolve this issue? (y/n): ", color="yellow")
            if input().lower() == 'y':
                provide_manual_instructions()
            return False
    else:
        print_colored("ℹ️ Database file not found. Nothing to rename.", color="blue")
        return True

def reset_database_simple():
    """طريقة مبسطة لإعادة ضبط قاعدة البيانات."""
    print_colored("\n🗄️ Resetting database...", color="cyan", style="bold")
    
    try:
    db_path = os.path.join(os.getcwd(), "db.sqlite3")
        retries = 10  # زيادة عدد المحاولات
        wait_time = 5  # زيادة وقت الانتظار قليلًا
        
        # محاولة إنهاء العمليات في البداية (مرة واحدة فقط)
        if platform.system() == 'Windows' and os.path.exists(db_path):
            try:
                print_colored("⏳ Waiting for existing connections to close...", color="blue")
                time.sleep(3)  # انتظار أولي
                
                # تنفيذ سكريبت kill_python_processes.py بشكل مباشر
                print_colored("🔄 استخدام kill_python_processes.py لإنهاء عمليات Python...", color="blue")
                try:
                    # تنفيذ السكريبت بشكل مباشر بدون معالجة الخرج
                    process = subprocess.Popen(
                        [sys.executable, "kill_python_processes.py", "--reset-only"],
                        stdout=None,  # تمرير المخرجات مباشرة للطرفية
                        stderr=None,  # تمرير أخطاء مباشرة للطرفية
                    )
                    process.wait()  # انتظار انتهاء العملية
                    
                    print_colored("✅ انتهت عملية إنهاء عمليات Python.", color="green")
                except Exception as e:
                    print_colored(f"⚠️ حدث خطأ أثناء محاولة تشغيل kill_python_processes.py: {e}", color="yellow")
                    
                    # إذا فشل استدعاء السكريبت المنفصل، نحاول إنهاء العمليات باستخدام الطريقة البديلة
                    print_colored("🔄 محاولة إنهاء العمليات بالطريقة البديلة...", color="blue")
                    try:
                        result = subprocess.run(
                            "taskkill /F /FI \"IMAGENAME eq python.exe\" /T",
                            shell=True,
                            capture_output=True,
                            check=False
                        )
                        if "SUCCESS" in result.stdout.decode('utf-8', errors='ignore'):
                            print_colored("✅ Successfully terminated Python processes", color="green")
                    except Exception:
                        pass
                
                # مهم: انتظار وقت أطول للتأكد من توقف العمليات
                print_colored("⏳ Waiting for processes to fully terminate (10 seconds)...", color="blue")
                for i in range(10):
                    # عرض نقاط متحركة لإظهار التقدم
                    print_colored(".", color="blue", end='', style="bold")
                    sys.stdout.flush()  # إجبار عرض النقاط فوراً
                    time.sleep(1)
                print()  # سطر جديد بعد النقاط
                
            except Exception as e:
                print_colored(f"⚠️ Error when trying to kill processes: {e}", color="yellow")
                # متابعة العملية حتى لو فشلت محاولة إنهاء العمليات
        
    for attempt in range(retries):
        try:
            if os.path.exists(db_path):
                    # محاولة إلغاء قفل الملف عن طريق فتحه وإغلاقه
                    if platform.system() == 'Windows':
                        try:
                            print_colored("🔄 Attempting to unlock database file...", color="blue")
                            with open(db_path, 'a+b') as f:
                                # قراءة بايت واحد للتأكد من أن المقبض مفتوح بالكامل
                                f.seek(0)
                                f.read(1)
                                # المقبض سيتم إغلاقه تلقائياً عند الخروج من الـ with block
                        except Exception:
                            pass
                    
                    # تأخير قصير قبل محاولة الحذف
                    time.sleep(1)
                    
                    # محاولة حذف الملف
                os.remove(db_path)
                    print_colored("✅ SQLite database deleted successfully.", color="green")
                    return True
                else:
                    print_colored("ℹ️ Database does not exist. Skipping deletion.", color="blue")
                    return True
            except PermissionError:
                print_colored(f"⚠️ Database in use. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{retries})", color="yellow")
                
                # في الوسط، حاول مرة أخرى قتل العمليات
                if attempt == retries // 2:
                    try:
                        print_colored("🔄 Making another attempt to kill processes...", color="blue")
                        subprocess.run(
                            "taskkill /F /FI \"IMAGENAME eq python.exe\" /T",
                            shell=True,
                            capture_output=True,
                            check=False
                        )
                        # انتظار أطول بعد محاولة القتل الثانية
                        time.sleep(wait_time * 2)
                    except Exception:
                        pass
                else:
                    time.sleep(wait_time)
        
        # إذا وصلنا إلى هنا معناه أن كل المحاولات فشلت - نحاول إنشاء ملف جديد فارغ
        print_colored("❌ Failed to delete the database after multiple attempts.", color="red")
        print_colored("🔄 Trying an alternative approach...", color="blue")
        
        # محاولة الحذف باستخدام أمر cmd
        try:
            print_colored("🔄 Attempting to delete using system command...", color="blue")
            if platform.system() == 'Windows':
                subprocess.run(f'del /F "{db_path}"', shell=True, check=False)
            else:
                subprocess.run(f'rm -f "{db_path}"', shell=True, check=False)
            
            # التحقق مما إذا نجح الحذف
            if not os.path.exists(db_path):
                print_colored("✅ Database deleted successfully using system command.", color="green")
                return True
        except Exception:
            pass
        
        # محاولة إنشاء ملف فارغ
        try:
            print_colored("🔄 Trying to create an empty database instead...", color="blue")
            # محاولة إفراغ محتويات الملف
            with open(db_path, 'w') as f:
                pass
            
            print_colored("✅ Created empty database file.", color="green")
            return True
        except Exception as e:
            print_colored(f"❌ Error creating empty database: {e}", color="red")
            
            # خيارات للمستخدم
            print_colored("\nOptions:", color="white")
            print_colored("1. Try running with --no-db-reset flag: python reset_migrations.py --no-db-reset", color="blue")
            print_colored("2. Restart your computer and try again", color="blue")
            print_colored("3. Close all Python processes and try again", color="blue")
            
            # سؤال المستخدم إذا كان يريد المتابعة
            if input("\n❓ Do you want to continue anyway? (y/n): ").lower() == 'y':
                print_colored("⚠️ Continuing despite database issues.", color="yellow")
                return True
            else:
                return False
    except Exception as e:
        print_colored(f"❌ Unexpected error during database reset: {e}", color="red")
        
        # سؤال المستخدم إذا كان يريد المتابعة
        if input("❓ Do you want to continue anyway? (y/n): ").lower() == 'y':
            print_colored("⚠️ Continuing despite errors.", color="yellow")
            return True
        else:
            return False 

def reset_database():
    """Reset the database."""
    print_colored("\n🗄️ Resetting database...", color="cyan", style="bold")
    
    try:
        db_path = os.path.join(os.getcwd(), "db.sqlite3")
        
        if not os.path.exists(db_path):
            print_colored("ℹ️ Database does not exist. Nothing to reset.", color="blue")
            return True
            
        # SQLite - try to delete the file
        try:
            # Try to unlock the file if it's on Windows
            if platform.system() == 'Windows':
                try:
                    with open(db_path, 'a+b') as f:
                        pass  # Just unlock the file by opening it
                except Exception:
                    pass  # Ignore if it fails
                    
            # Try to remove the file
            os.remove(db_path)
            print_colored("✅ SQLite database deleted successfully.", color="green")
            return True
            
        except PermissionError:
            print_colored("⚠️ Database is locked by another process.", color="yellow")
            
            # Ask user if they want to try the simple reset method
            print_colored("❓ Do you want to try simple database reset method? (y/n): ", color="yellow")
            if input().lower() == 'y':
                return reset_database_simple()
                
            print_colored("❓ Do you want to try manual database rename? (y/n): ", color="yellow")
            if input().lower() == 'y':
                return rename_database_manually()
                
            # If both options declined, ask if user wants to continue anyway
            print_colored("❓ Do you want to continue without resetting the database? (y/n): ", color="yellow")
            if input().lower() == 'y':
                print_colored("⚠️ Continuing without database reset.", color="yellow")
                return True
            else:
                return False
                
        except Exception as e:
            print_colored(f"❌ Error deleting database: {e}", color="red")
            
            print_colored("❓ Do you want to continue anyway? (y/n): ", color="yellow")
            if input().lower() == 'y':
                print_colored("⚠️ Continuing despite errors.", color="yellow")
                return True
            else:
                return False
                
    except Exception as e:
        print_colored(f"❌ Unexpected error: {e}", color="red")
        
        print_colored("❓ Do you want to continue anyway? (y/n): ", color="yellow")
        if input().lower() == 'y':
            print_colored("⚠️ Continuing despite errors.", color="yellow")
            return True
        else:
            return False

def make_migrations():
    """Create new migration files."""
    print_colored("\n🔄 Creating new migrations...", color="cyan", style="bold")
    
    try:
        # Create migrations for all apps at once
        print_colored("🔄 Running makemigrations for all apps...", color="blue")
        result = subprocess.run(
            [sys.executable, "manage.py", "makemigrations"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print_colored(f"⚠️ Warning during makemigrations: {result.stderr}", color="yellow")
            
            # If general makemigrations failed, try with individual apps
            print_colored("🔄 Trying individual app migrations...", color="blue")
            for app in APPS:
                print_colored(f"🔄 Creating migrations for {app}...", color="blue")
                result = subprocess.run(
                    [sys.executable, "manage.py", "makemigrations", app],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    print_colored(f"⚠️ Warning during {app} migrations: {result.stderr}", color="yellow")
                else:
                    for line in result.stdout.splitlines():
                        if line.strip():
                            print_colored(f"  {line}", color="green")
        else:
            for line in result.stdout.splitlines():
                if line.strip():
                    print_colored(f"  {line}", color="green")
        
        print_colored("✅ Migrations created successfully.", color="green")
        return True
    
    except Exception as e:
        print_colored(f"❌ Error creating migrations: {e}", color="red")
        
        print_colored("❓ Do you want to continue anyway? (y/n): ", color="yellow")
        if input().lower() == 'y':
            print_colored("⚠️ Continuing despite errors.", color="yellow")
            return True
        else:
            return False

def apply_migrations():
    """Apply migrations to the database."""
    print_colored("\n🔄 Applying migrations...", color="cyan", style="bold")
    
    try:
        result = subprocess.run(
            [sys.executable, "manage.py", "migrate"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print_colored(f"⚠️ Warning during migration: {result.stderr}", color="yellow")
            
            # Check if there's a specific error that needs handling
            if "no such table" in result.stderr.lower() or "already exists" in result.stderr.lower():
                print_colored("🔄 Detected database inconsistency. Trying with --fake-initial...", color="blue")
                
                # Try with --fake-initial flag
                result = subprocess.run(
                    [sys.executable, "manage.py", "migrate", "--fake-initial"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    print_colored(f"⚠️ Warning during fake-initial migration: {result.stderr}", color="yellow")
        
        print_colored("✅ Migrations applied successfully.", color="green")
        return True
    
    except Exception as e:
        print_colored(f"❌ Error applying migrations: {e}", color="red")
        
        print_colored("❓ Do you want to continue anyway? (y/n): ", color="yellow")
        if input().lower() == 'y':
            print_colored("⚠️ Continuing despite errors.", color="yellow")
            return True
        else:
            return False

def create_superuser():
    """Create a superuser account."""
    print_colored("\n👤 Creating superuser...", color="cyan", style="bold")
    
    # Default superuser credentials
    username = os.getenv('DEFAULT_SUPERUSER_USERNAME', 'mwheba')
    email = os.getenv('DEFAULT_SUPERUSER_EMAIL', 'info@mwheba.com')
    password = os.getenv('DEFAULT_SUPERUSER_PASSWORD', 'MedooAlnems2008')
    
    # Check if environment variables are set
    if os.getenv('DEFAULT_SUPERUSER_USERNAME') and os.getenv('DEFAULT_SUPERUSER_PASSWORD'):
        print_colored("ℹ️ Using superuser credentials from environment variables.", color="blue")
    else:
        print_colored("ℹ️ Using default superuser credentials.", color="yellow")
        print_colored(f"   Username: {username}", color="yellow")
    
    try:
        # Using Python code to create superuser non-interactively
        python_code = f"""
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='{username}').exists():
    User.objects.create_superuser('{username}', '{email}', '{password}')
    print('Superuser created successfully.')
else:
    print('Superuser already exists.')
"""
        
        result = subprocess.run(
            [sys.executable, "manage.py", "shell", "-c", python_code],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print_colored(f"⚠️ Warning during superuser creation: {result.stderr}", color="yellow")
        else:
            print_colored(f"✅ {result.stdout.strip()}", color="green")
        
        return True
    except Exception as e:
        print_colored(f"❌ Error creating superuser: {e}", color="red")
        
        print_colored("❓ Do you want to continue anyway? (y/n): ", color="yellow")
        if input().lower() == 'y':
            print_colored("⚠️ Continuing despite errors.", color="yellow")
            return True
        else:
            return False

def load_fixtures():
    """Load initial data from fixtures."""
    print_colored("\n📊 Loading fixtures...", color="cyan", style="bold")
    
    # تحديد ترتيب تحميل البيانات مع الاعتماديات
    apps_order = [
        "users",     # المستخدمين أولاً
        "core",      # إعدادات النظام
        "client",    # العملاء
        "supplier",  # الموردين
        "product",   # المنتجات
        "financial", # المالية
        "purchase",  # المشتريات
        "sale"       # المبيعات
    ]
    
    # ملفات البيانات الأساسية والإضافية لكل تطبيق
    fixtures_to_load = {
        "users": ["initial_data.json", "groups.json", "groups_permissions.json", "user_groups.json"],
        "core": ["initial_data.json"],
        "client": ["initial_data.json"],
        "supplier": ["initial_data.json"],
        "product": ["initial_data.json"],
        "financial": ["initial_data.json"],
        "purchase": ["initial_data.json", "initial_data_extra.json"],
        "sale": ["initial_data.json", "initial_data_extra.json"]
    }
    
    success_count = 0
    total_fixtures = 0
    
    # حساب إجمالي ملفات البيانات التي سيتم تحميلها
    for app in apps_order:
        if app in fixtures_to_load:
            total_fixtures += len(fixtures_to_load[app])
    
    print_colored(f"💽 Found {total_fixtures} potential fixture files to load", color="blue")
    
    # تحميل الملفات حسب الترتيب
    for app in apps_order:
        if app not in fixtures_to_load:
            continue
            
        print_colored(f"\n📂 Loading fixtures for: {app}", color="cyan", style="bold")
        
        for fixture in fixtures_to_load[app]:
            fixture_path = os.path.join(BASE_DIR, app, "fixtures", fixture)
            
            if not os.path.exists(fixture_path):
                print_colored(f"⚠️ File not found: {app}/fixtures/{fixture}", color="yellow")
                continue
                
            print_colored(f"🔄 Loading: {app}/fixtures/{fixture}...", color="blue")
            
            try:
                # محاولة تحميل الملف مع معالجة خاصة لبعض الملفات التي تسبب مشاكل
                load_command = [sys.executable, "manage.py", "loaddata", fixture_path]
                
                # معالجة خاصة لملفات معينة معروفة بأنها تسبب مشاكل
                if fixture == "groups_permissions.json":
                    # استخدام طريقة بديلة لتحميل صلاحيات المجموعات
                    if try_load_group_permissions(fixture_path):
                        print_colored(f"✅ {fixture} loaded using alternative method", color="green")
                        success_count += 1
                        continue
                    else:
                        print_colored(f"ℹ️ Falling back to standard method with --ignorenonexistent flag for {fixture}", color="blue")
                        load_command.append("--ignorenonexistent")
                
                if fixture == "user_groups.json":
                    # محاولة تحديد النموذج الصحيح في حالة خطأ نموذج user_groups 
                    print_colored(f"ℹ️ Attempting special handling for {fixture}", color="blue")
                    # استخدام علم --ignorenonexistent لتجاهل النماذج غير الموجودة
                    load_command.append("--ignorenonexistent")
                
                result = subprocess.run(
                    load_command,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    # فحص أنواع محددة من الأخطاء
                    if "UNIQUE constraint failed" in result.stderr:
                        print_colored(f"⚠️ Unique constraint error in {fixture}. Attempting with --ignorenonexistent...", color="yellow")
                        # محاولة تحميل البيانات مع تجاهل السجلات المكررة
                        result = subprocess.run(
                            [sys.executable, "manage.py", "loaddata", fixture_path, "--ignorenonexistent"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result.returncode == 0:
                            print_colored(f"✅ {fixture} loaded with ignorenonexistent: {result.stdout.strip()}", color="green")
                            success_count += 1
                        else:
                            print_colored(f"⚠️ Error loading {fixture} even with ignorenonexistent: {result.stderr}", color="yellow")
                            
                            # محاولة بديلة أخيرة لتحميل البيانات باستخدام --no-output
                            if "UNIQUE constraint failed" in result.stderr and fixture == "groups_permissions.json":
                                print_colored(f"🔄 Final attempt with --no-output flag...", color="blue")
                                result = subprocess.run(
                                    [sys.executable, "manage.py", "loaddata", fixture_path, "--ignorenonexistent", "--no-output"],
                                    capture_output=True,
                                    text=True,
                                    check=False
                                )
                                if result.returncode == 0:
                                    print_colored(f"✅ {fixture} loaded using final method", color="green")
                                    success_count += 1
                                else:
                                    print_colored(f"❌ All methods failed for {fixture}", color="red")
                    elif "doesn't have a" in result.stderr and "model" in result.stderr:
                        print_colored(f"⚠️ Model error in {fixture}. This might be a naming issue in the fixture.", color="yellow")
                        print_colored(f"   Consider manually checking the model definitions in {fixture}.", color="yellow")
                    else:
                        print_colored(f"⚠️ Error loading {fixture}: {result.stderr}", color="yellow")
                else:
                    print_colored(f"✅ {fixture} loaded successfully: {result.stdout.strip()}", color="green")
                    success_count += 1
            except Exception as e:
                print_colored(f"❌ Error loading {fixture}: {e}", color="red")
                
                print_colored(f"❓ Continue loading remaining fixtures? (y/n): ", color="yellow")
                if input().lower() != 'y':
                    print_colored("⚠️ Fixture loading stopped by user.", color="yellow")
                    return success_count > 0
    
    # إظهار ملخص للعملية
    if success_count == 0:
        print_colored("❌ No fixtures were loaded.", color="red")
        return False
    elif success_count < total_fixtures:
        print_colored(f"⚠️ Loaded {success_count} of {total_fixtures} fixture files.", color="yellow", style="bold")
        # إذا تم تحميل بعض الملفات على الأقل، اعتبر العملية ناجحة
        print_colored("ℹ️ Some fixtures could not be loaded, but enough data was loaded to continue.", color="blue")
        return True
    else:
        print_colored(f"✅ Successfully loaded all {success_count} fixture files!", color="green", style="bold")
        return True

def try_load_group_permissions(fixture_path):
    """
    محاولة تحميل صلاحيات المجموعات باستخدام طريقة SQL مباشرة
    لتفادي مشكلة UNIQUE constraint failed.
    """
    print_colored("🔄 Attempting to load group permissions using alternative method...", color="blue")
    
    try:
        import json
        
        # قراءة ملف البيانات
        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # طريقة بديلة باستخدام كود Python مباشرة
        python_code = """
import json
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# تحميل بيانات الصلاحيات من ملف JSON
fixture_path = '{}'
with open(fixture_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

success_count = 0
total_items = len(data)

# معالجة كل عنصر في البيانات
for item in data:
    if item['model'] == 'auth.group_permissions':
        try:
            group_id = item['fields']['group']
            permission_id = item['fields']['permission']
            
            # الحصول على المجموعة والصلاحية
            group = Group.objects.get(id=group_id)
            permission = Permission.objects.get(id=permission_id)
            
            # إضافة الصلاحية للمجموعة إذا لم تكن موجودة بالفعل
            if permission not in group.permissions.all():
                group.permissions.add(permission)
                success_count += 1
                
        except Group.DoesNotExist:
            print(f"Group with ID {{group_id}} does not exist")
        except Permission.DoesNotExist:
            print(f"Permission with ID {{permission_id}} does not exist")
        except Exception as e:
            print(f"Error: {{e}}")

print(f"Successfully added {{success_count}} of {{total_items}} permissions to groups")
""".format(fixture_path.replace('\\', '\\\\'))

        # تنفيذ الكود Python
        result = subprocess.run(
            [sys.executable, "manage.py", "shell", "-c", python_code],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print_colored(f"✅ Group permissions loaded: {result.stdout.strip()}", color="green")
            return True
        else:
            print_colored(f"⚠️ Alternative loading method failed: {result.stderr}", color="yellow")
            return False
            
    except Exception as e:
        print_colored(f"❌ Error in alternative loading method: {e}", color="red")
        return False

def start_server():
    """Start the development server."""
    print_colored("\n🚀 Starting development server...", color="cyan", style="bold")
    
    try:
        # Run the server command
        print_colored("🌐 Server starting at http://127.0.0.1:8000/", color="green")
        print_colored("🛑 Press CTRL+C to stop the server", color="red", style="bold")
        
        # Using Python's exec to run the server
        os.system(f"{sys.executable} manage.py runserver")
        return True
    except KeyboardInterrupt:
        print_colored("\n⛔ Server stopped by user.", color="yellow")
        return True
    except Exception as e:
        print_colored(f"❌ Error starting development server: {e}", color="red")
        return False

def main():
    """Main function that runs the entire process."""
    print_colored("\n=== MWHEBA ERP Database & Migrations Reset ===", color="cyan", style="bold")
    print_colored("This script will reset all migrations and the database.", color="white")
    print_colored("Make sure to backup your data before proceeding.", color="yellow", style="bold")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Reset database and migrations for MWHEBA ERP")
    parser.add_argument("--no-backup", action="store_true", help="Skip database backup")
    parser.add_argument("--no-migrations", action="store_true", help="Skip creating new migrations")
    parser.add_argument("--no-db-reset", action="store_true", help="Skip database reset")
    parser.add_argument("--no-fixtures", action="store_true", help="Skip loading fixtures")
    parser.add_argument("--no-server", action="store_true", help="Don't start the development server")
    parser.add_argument("--simple-db-reset", action="store_true", help="Use simplified DB reset (better for Windows)")
    parser.add_argument("--kill-python", action="store_true", help="Kill all Python processes before starting (Windows)")
    parser.add_argument("--wait", type=int, default=0, help="Wait N seconds before starting (helps with file locks)")
    
    args = parser.parse_args()
    
    # Display usage tips
    print_colored("\n💡 USAGE TIPS:", color="cyan")
    print_colored("• If you encounter database lock errors on Windows, try:", color="white")
    print_colored("  1. Kill Python processes: --kill-python", color="yellow")
    print_colored("  2. Skip database reset: --no-db-reset", color="yellow")
    print_colored("  3. Use lighter reset: --simple-db-reset", color="yellow")
    print_colored("  4. Add wait time: --wait 30", color="yellow")
    
    if args.kill_python and platform.system() == 'Windows':
        print_colored("\n⚠️ WARNING: This script will kill all running Python processes!", color="red", style="bold")
        print_colored("Make sure to save your work in other Python applications.", color="yellow")
        print_colored("Press Ctrl+C now to cancel, or Enter to continue...", color="yellow")
        try:
            input()
        except KeyboardInterrupt:
            print_colored("\n❌ Operation canceled by user.", color="red")
            return
            
        print_colored("\n🔄 Terminating Python processes before starting...", color="blue")
        try:
            # First try to use our kill_python_processes.py script
            if os.path.exists("kill_python_processes.py"):
                subprocess.run([sys.executable, "kill_python_processes.py"], 
                              check=False)
            else:
                # Fallback to direct command
                if platform.system() == 'Windows':
                    subprocess.run(
                        "taskkill /F /FI \"IMAGENAME eq python.exe\" /T",
                        shell=True,
                        capture_output=True,
                        check=False
                    )
        except Exception as e:
            print_colored(f"⚠️ Error killing processes: {e}", color="yellow")
    
    # Wait if requested
    if args.wait > 0:
        print_colored(f"\n⏱️ Waiting {args.wait} seconds before starting...", color="blue")
        time.sleep(args.wait)
    
    # Start the process
    steps_completed = 0
    total_steps = 6 - sum([args.no_backup, args.no_db_reset, args.no_migrations, args.no_fixtures, args.no_server])
    
    # STEP 1: Backup project
    if not args.no_backup:
        print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Backing up project", color="magenta", style="bold")
        if not backup_project():
            print_colored("❌ Failed to create backup. Do you want to continue? (y/n): ", color="red")
            if input().lower() != 'y':
                print_colored("❌ Operation aborted by user.", color="red")
                return
        steps_completed += 1
    
    # STEP 2: Clear existing migrations
    print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Clearing migrations", color="magenta", style="bold")
    if not clear_migrations():
        print_colored("❌ Failed to clear migrations. Aborting.", color="red")
        return
    steps_completed += 1
    
    # STEP 3: Reset database
    if not args.no_db_reset:
        print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Resetting database", color="magenta", style="bold")
        if args.simple_db_reset:
            success = reset_database_simple()
        else:
            success = reset_database()
            
        if not success:
            print_colored("❌ Failed to reset database. Aborting.", color="red")
            return
        steps_completed += 1
    
    # STEP 4: Make new migrations and apply them
    if not args.no_migrations:
        print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Creating migrations", color="magenta", style="bold")
        if not make_migrations():
            print_colored("❌ Failed to create migrations. Aborting.", color="red")
            return
            
        print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Applying migrations", color="magenta", style="bold")
        if not apply_migrations():
            print_colored("❌ Failed to apply migrations. Aborting.", color="red")
            return
            
        print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Creating superuser", color="magenta", style="bold")
        if not create_superuser():
            print_colored("❌ Failed to create superuser. Aborting.", color="red")
            return
        steps_completed += 1
    
    # STEP 5: Load fixtures
    if not args.no_fixtures:
        print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Loading fixtures", color="magenta", style="bold")
        if not load_fixtures():
            print_colored("❌ Failed to load fixtures. Aborting.", color="red")
            return
        steps_completed += 1
    
    # STEP 6: Start development server
    if not args.no_server:
        print_colored(f"\n[Step {steps_completed+1}/{total_steps}] Starting development server", color="magenta", style="bold")
        if not start_server():
            print_colored("❌ Failed to start server.", color="red")
        steps_completed += 1
    
    # All done!
    print_colored("\n✅ All steps completed successfully!", color="green", style="bold")
    print_colored("🌟 Your Django project has been reset and is ready to use.", color="cyan")

if __name__ == "__main__":
    main() 