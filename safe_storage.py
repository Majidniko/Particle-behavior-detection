import os
import shutil
import tempfile
from time import sleep
from threading import Thread
from flash_detector import FlashDetector

class SafeStorage:
    def __init__(self):
        self.flash_detector = FlashDetector()
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'raspberry_camera_temp')
        os.makedirs(self.temp_dir, exist_ok=True)

    def _check_flash(self):
        """بررسی وجود و وضعیت فلش"""
        success, message = self.flash_detector.prepare_storage()
        if not success:
            raise RuntimeError(message)
        return self.flash_detector.get_storage_path()

    def _copy_to_flash(self, src_path, dest_type, callback=None):
        """کپی ایمن فایل از حافظه موقت به فلش"""
        flash_path = self._check_flash()
        filename = os.path.basename(src_path)
        
        dest_folder = os.path.join(flash_path, dest_type)  # 'images' یا 'videos'
        dest_path = os.path.join(dest_folder, filename)
        
        try:
            # کپی فایل به مقصد نهایی
            shutil.copy2(src_path, dest_path)
            
            # حذف فایل موقت
            os.remove(src_path)
            
            if callback:
                callback(dest_path)
            return dest_path
        except Exception as e:
            # در صورت خطا فایل موقت باقی می‌ماند
            if callback:
                callback(None, str(e))
            raise RuntimeError(f"خطا در انتقال به فلش: {str(e)}")

    def save_file(self, file_type, file_extension, file_data, callback=None):
        """
        ذخیره‌سازی ایمن فایل با نوع مشخص
        :param file_type: 'images' یا 'videos'
        :param file_extension: 'jpg' یا 'mp4'
        :param file_data: داده‌های فایل (باینری)
        :param callback: تابع بازخوانی برای اطلاع از نتیجه
        :return: مسیر موقت فایل
        """
        try:
            # ایجاد نام فایل منحصر به فرد
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{file_type[:-1]}_{timestamp}.{file_extension}"
            temp_path = os.path.join(self.temp_dir, filename)
            
            # ذخیره در حافظه موقت
            with open(temp_path, 'wb') as f:
                f.write(file_data)
            
            # انتقال به فلش در یک رشته جداگانه
            Thread(target=self._copy_to_flash, 
                  args=(temp_path, file_type, callback)).start()
            
            return temp_path
        except Exception as e:
            if callback:
                callback(None, str(e))
            raise RuntimeError(f"خطا در ذخیره‌سازی موقت: {str(e)}")