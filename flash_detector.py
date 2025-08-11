import os
import subprocess
from time import sleep

class FlashDetector:
    def __init__(self):
        self.flash_mounted = False
        self.mount_point = None
        self.media_folder = None

    def detect_flash(self):
        """بررسی وجود فلش مموری متصل شده"""
        try:
            # پیدا کردن دستگاه فلش
            result = subprocess.run(
                ['lsblk', '-o', 'NAME,MOUNTPOINT,LABEL', '-J'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                print("Error in run command lsblk")
                return False, "خطا در اجرای دستور lsblk"

            import json
            devices = json.loads(result.stdout)
            
            for device in devices['blockdevices']:
                # بررسی دستگاه‌های USB (معمولاً با sd شروع می‌شوند)
                if device['name'].startswith('sd'):
                    for partition in device.get('children', []):
                        if partition.get('mountpoint'):
                            self.mount_point = partition['mountpoint']
                            self.flash_mounted = True
                            return True, None
            print("No external storage found")            
            return False, "هیچ ذخیره ساز خارجی متصل نشده است"
            
        except Exception as e:
            return False, f"error in found memory: {str(e)}"

    def prepare_storage(self):
        """آماده سازی مسیرهای ذخیره سازی روی فلش"""
        detected, message = self.detect_flash()
        if not detected:
            return False, message
        
        try:
            # ایجاد پوشه‌های مورد نیاز روی فلش
            base_dir = self.mount_point
            self.media_folder = os.path.join(base_dir, 'raspberry_camera_media')
            os.makedirs(os.path.join(self.media_folder, 'images'), exist_ok=True)
            os.makedirs(os.path.join(self.media_folder, 'videos'), exist_ok=True)
            
            return True, self.media_folder
        except Exception as e:
            return False, f"rror in craet folders: {str(e)}"

    def get_storage_path(self):
        """دریافت مسیر ذخیره سازی"""
        if self.flash_mounted and self.media_folder:
            return self.media_folder
        return None

if __name__ == "__main__":
    # تست عملکرد
    detector = FlashDetector()
    success, message = detector.prepare_storage()
    
    if success:
        print(f"External storage found - Location is: {detector.get_storage_path()}")
    else:
        print(f"Error: {message}")