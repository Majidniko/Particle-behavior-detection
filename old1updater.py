import os
import sys
import requests
import zipfile
import shutil
import json
import hashlib
from datetime import datetime

# تنظیمات
REPO_URL = "https://github.com/Majidniko/Particle-behavior-detection"  # آدرس ریپوی شما
VERSION_FILE = "version.txt"  # فایل نسخه در ریپو
HASH_FILE = "file_hashes.json"  # فایل هش فایل‌ها
LOG_FILE = "logs/update.log"  # فایل لاگ
ZIP_URL = f"{REPO_URL}/archive/main.zip"  # دانلود کد به صورت ZIP
BACKUP_DIR = "backup"  # پوشه نسخه پشتیبان

def setup_logging():
    """ایجاد پوشه لاگ اگر وجود نداشته باشد"""
    os.makedirs("logs", exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def log_message(message):
    print("saving message to Log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def get_current_version():
    print("Read corrent program version")
    if not os.path.exists(VERSION_FILE):
        return "0.0.0"
    with open(VERSION_FILE, "r") as f:
        return f.read().strip()

def get_latest_version():
    print("Get last version")
    try:
        version_url = f"{REPO_URL}/raw/main/{VERSION_FILE}"
        response = requests.get(version_url)
        if response.status_code == 200:
            return response.text.strip()
        return None
    except Exception as e:
        log_message(f"Error fetching latest version: {e}")
        return None

def calculate_file_hash(file_path):
    print("Creat Hash file")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()

def verify_file_hashes():
    print("CHecking Hash")
    """بررسی هش فایل‌ها با نسخه اصلی"""
    try:
        hashes_url = f"{REPO_URL}/raw/main/{HASH_FILE}"
        response = requests.get(hashes_url)
        if response.status_code != 200:
            log_message("Failed to download hash file.")
            return False
        
        remote_hashes = json.loads(response.text)
        for file_path, expected_hash in remote_hashes.items():
            if not os.path.exists(file_path):
                log_message(f"File missing: {file_path}")
                return False
            
            actual_hash = calculate_file_hash(file_path)
            if actual_hash != expected_hash:
                log_message(f"Hash mismatch for {file_path}")
                return False
        
        return True
    except Exception as e:
        log_message(f"Error verifying hashes: {e}")
        return False

def backup_files():
    print("Create a backup of current files ")
    try:
        if os.path.exists(BACKUP_DIR):
            shutil.rmtree(BACKUP_DIR)
        os.makedirs(BACKUP_DIR)
        
        for item in os.listdir("."):
            if item in ["backup", "logs"]:  # از پوشه‌های خاص صرف‌نظر می‌کنیم
                continue
            src = os.path.join(".", item)
            dst = os.path.join(BACKUP_DIR, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        log_message("Backup created successfully.")
        return True
    except Exception as e:
        log_message(f"Backup failed: {e}")
        return False

def rollback_update():
    print("Error in update: return to previes version")
    """بازگشت به نسخه قبلی در صورت شکست آپدیت"""
    try:
        if not os.path.exists(BACKUP_DIR):
            log_message("No backup found for rollback.")
            return False
        
        for item in os.listdir(BACKUP_DIR):
            src = os.path.join(BACKUP_DIR, item)
            dst = os.path.join(".", item)
            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        log_message("Rollback successful.")
        return True
    except Exception as e:
        log_message(f"Rollback failed: {e}")
        return False

def download_and_extract_update():
    """دانلود و نصب آپدیت با بررسی امنیتی"""
    try:
        log_message("Starting update process...")
        
        # بررسی هش فایل‌ها قبل از دانلود
        if not verify_file_hashes():
            log_message("Security check failed. Aborting update.")
            return False
        
        # تهیه نسخه پشتیبان
        if not backup_files():
            log_message("Backup failed. Aborting update.")
            return False
        
        # دانلود فایل ZIP
        response = requests.get(ZIP_URL)
        with open("update.zip", "wb") as f:
            f.write(response.content)
        
        # اکسترکت فایل ZIP
        with zipfile.ZipFile("update.zip", 'r') as zip_ref:
            zip_ref.extractall("temp_update")
        
        # جایگزینی فایل‌های قدیمی با فایل‌های جدید
        for item in os.listdir("temp_update/repo-main"):
            src = os.path.join("temp_update/repo-main", item)
            dst = os.path.join(".", item)
            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        # پاک کردن فایل‌های موقت
        shutil.rmtree("temp_update")
        os.remove("update.zip")
        
        log_message("Update applied successfully.")
        return True
    except Exception as e:
        log_message(f"Update failed: {e}")
        rollback_update()  # بازگشت به نسخه قبلی
        return False

def restart_program():
    """ری‌استارت برنامه"""
    python = sys.executable
    os.execl(python, python, *sys.argv)

def check_and_update():
    print("چک کردن آپدیت و نصب آن")
    setup_logging()
    current_version = get_current_version()
    latest_version = get_latest_version()
    
    if latest_version and latest_version != current_version:
        log_message(f"Update available: {current_version} -> {latest_version}")
        if download_and_extract_update():
            log_message("Update successful. Restarting...")
            restart_program()
        else:
            log_message("Update failed.")
    else:
        log_message("No updates available.")

if __name__ == "__main__":
    check_and_update()