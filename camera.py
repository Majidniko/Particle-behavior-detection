import os
import time
import cv2
import tempfile
import shutil
from threading import Lock, Thread
from picamera2 import Picamera2
from libcamera import controls

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        
        # پیکربندی دوربین
        config = self.picam2.create_video_configuration(
            main={"size": (3840, 2160)},
            lores={"size": (1024, 768), "format": "RGB888"},
            display="lores",
            encode="main"
        )
        self.picam2.set_controls({"FrameRate": 30.0})
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(2)

        # متغیرهای ضبط
        self.recording = False
        self.recording_lock = Lock()
        self.video_writer = None
        
        # مسیرهای ذخیره‌سازی موقت
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'raspberry_camera_temp')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # فلش دیسک
        self.flash_mounted = False
        self.flash_path = None
        self._check_flash()

    def _check_flash(self):
        """بررسی وجود و وضعیت فلش دیسک"""
        try:
            # این بخش را با کدهای تشخیص فلش از ماژول flash_detector جایگزین کنید
            # برای مثال ساده:
            possible_mounts = ['/media/pi', '/mnt/usb']
            for mount in possible_mounts:
                if os.path.exists(mount) and os.path.ismount(mount):
                    self.flash_path = mount
                    self.flash_mounted = True
                    os.makedirs(os.path.join(self.flash_path, 'images'), exist_ok=True)
                    os.makedirs(os.path.join(self.flash_path, 'videos'), exist_ok=True)
                    return True
            
            self.flash_mounted = False
            return False
        except Exception as e:
            print(f"خطا در بررسی فلش دیسک: {e}")
            self.flash_mounted = False
            return False

    def _transfer_to_flash(self, src_path, file_type, callback=None):
        """انتقال فایل به فلش دیسک"""
        try:
            if not self.flash_mounted and not self._check_flash():
                raise RuntimeError("ذخیره ساز خارجی یافت نشد")
            
            filename = os.path.basename(src_path)
            dest_path = os.path.join(self.flash_path, file_type, filename)
            
            # کپی فایل به فلش
            shutil.copy2(src_path, dest_path)
            
            # حذف فایل موقت
            os.remove(src_path)
            
            if callback:
                callback(dest_path)
            return dest_path
        except Exception as e:
            if callback:
                callback(None, str(e))
            raise RuntimeError(f"خطا در انتقال به فلش: {str(e)}")

    def stream_frames(self):
        """استریم ویدئو (بدون تغییر)"""
        self.picam2.stop()
        stream_config = self.picam2.create_video_configuration(
            main={"size": (800, 600)},  
            lores={"size": (1024, 768)},
            display="lores",
            encode="main"
        )
        self.picam2.configure(stream_config)
        self.picam2.start()
        time.sleep(1)
        
        while True:
            try:
                frame = self.picam2.capture_array("main")
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 10])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except Exception as e:
                print(f"[Stream Error]: {e}")
                time.sleep(0.1)

    def capture_image(self):
        """گرفتن عکس با ذخیره‌سازی موقت و انتقال به فلش"""
        try:
            # تغییر به حالت عکسبرداری با کیفیت بالا
            self.picam2.stop()
            fullres_config = self.picam2.create_video_configuration(
                main={"size": (3840, 2160)},
                lores={"size": (1024, 768)},
                display="lores",
                encode="main"
            )
            self.picam2.configure(fullres_config)
            self.picam2.start()
            time.sleep(1)

            # ذخیره موقت
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            temp_path = os.path.join(self.temp_dir, f"image_{timestamp}.jpg")
            self.picam2.capture_file(temp_path)
            
            # انتقال به فلش در پس‌زمینه
            Thread(target=self._transfer_to_flash, 
                  args=(temp_path, 'images', self._image_transfer_callback)).start()
            
            return temp_path  # مسیر موقت برای پیگیری وضعیت
            
        except Exception as e:
            print(f"[Capture Error]: {e}")
            return None

    def _image_transfer_callback(self, final_path, error=None):
        """تابع بازخوانی برای انتقال عکس"""
        if error:
            print(f"خطا در انتقال عکس: {error}")
        elif final_path:
            print(f"عکس با موفقیت انتقال یافت: {final_path}")

    def start_recording(self, duration=30):
        """شروع ضبط ویدئو با ذخیره‌سازی موقت"""
        try:
            if not self._check_flash():
                raise RuntimeError("ذخیره ساز خارجی یافت نشد")
            
            self.picam2.stop()
            video_config = self.picam2.create_video_configuration(
                main={"size": (1920, 1080)},
                lores={"size": (1024, 768)},
                display="lores",
                encode="main"
            )
            self.picam2.configure(video_config)
            self.picam2.start()
            time.sleep(1)

            # آماده‌سازی ضبط
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            temp_path = os.path.join(self.temp_dir, f"video_{timestamp}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 30
            frame_size = (1920, 1080)

            with self.recording_lock:
                self.video_writer = cv2.VideoWriter(temp_path, fourcc, fps, frame_size)
                if not self.video_writer.isOpened():
                    raise RuntimeError("خطا در باز کردن ذخیره کننده ویدئو")
                self.recording = True

            # ضبط ویدئو
            start_time = time.time()
            max_frames = int(fps * duration)
            frames_captured = 0
            
            while self.recording and frames_captured < max_frames:
                frame = self.picam2.capture_array("main")
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                with self.recording_lock:
                    if self.video_writer:
                        self.video_writer.write(frame)
                
                frames_captured += 1
                time.sleep(1 / fps)

            # انتقال به فلش در پس‌زمینه
            if self.recording:
                Thread(target=self._transfer_to_flash, 
                      args=(temp_path, 'videos', self._video_transfer_callback)).start()
            
            return temp_path  # مسیر موقت برای پیگیری وضعیت
            
        except Exception as e:
            print(f"[Recording Error]: {e}")
            return None
        finally:
            self.stop_recording()

    def _video_transfer_callback(self, final_path, error=None):
        """تابع بازخوانی برای انتقال ویدئو"""
        if error:
            print(f"خطا در انتقال ویدئو: {error}")
        elif final_path:
            print(f"ویدئو با موفقیت انتقال یافت: {final_path}")

    def stop_recording(self):
        """توقف ضبط"""
        with self.recording_lock:
            self.recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None