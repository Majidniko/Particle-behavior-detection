import os
import time
import cv2
from threading import Lock
from picamera2 import Picamera2
from libcamera import controls

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        
        # پیکربندی اولیه دوربین
        self.configure_camera(3840, 2160)  # رزولوشن اولیه 4K
        
        # متغیرهای ضبط
        self.recording = False
        self.recording_lock = Lock()
        self.video_writer = None
        
        # مسیرهای ذخیره‌سازی
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_folder = os.path.join(base_dir, 'static', 'media', 'images')
        self.video_folder = os.path.join(base_dir, 'static', 'media', 'videos')
        os.makedirs(self.image_folder, exist_ok=True)
        os.makedirs(self.video_folder, exist_ok=True)

    def configure_camera(self, width, height):
        """پیکربندی دوربین با اندازه‌های مشخص"""
        config = self.picam2.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"},
            lores={"size": (1024, 768), "format": "YUV420"},
            display="lores"
        )
        self.picam2.configure(config)
        self.picam2.set_controls({"FrameRate": 30.0})
        self.picam2.start()
        time.sleep(2)  # زمان برای پایدار شدن دوربین

    def stream_frames(self):
        """استریم ویدئو با کیفیت پایین برای روانی بیشتر"""
        try:
            while True:
                frame = self.picam2.capture_array("lores")
                frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB)
                frame = cv2.resize(frame, (640, 480))  # کاهش سایز برای استریم روان
                ret, buffer = cv2.imencode('.jpg', frame, [
                    int(cv2.IMWRITE_JPEG_QUALITY), 50
                ])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print(f"[Stream Error]: {e}")
        finally:
            self.picam2.stop()

    def capture_image(self):
        """گرفتن عکس با کیفیت بالا"""
        try:
            # تغییر به حالت عکسبرداری با کیفیت بالا
            self.picam2.stop()
            config = self.picam2.create_still_configuration(
                main={"size": (3840, 2160)},
                lores={"size": (1024, 768)},
                display="lores"
            )
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(1)
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filepath = os.path.join(self.image_folder, f"image_{timestamp}.jpg")
            self.picam2.capture_file(filepath)
            return filepath
        except Exception as e:
            print(f"[Capture Error]: {e}")
            return None
        finally:
            # بازگشت به حالت اولیه
            self.configure_camera(3840, 2160)

    def start_recording(self, duration=30):
        """شروع ضبط ویدئو با کیفیت بالا"""
        try:
            self.picam2.stop()
            config = self.picam2.create_video_configuration(
                main={"size": (1920, 1080)},
                lores={"size": (1024, 768)},
                display="lores"
            )
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(1)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            video_path = os.path.join(self.video_folder, f"video_{timestamp}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 30
            frame_size = (1920, 1080)

            with self.recording_lock:
                self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, frame_size)
                if not self.video_writer.isOpened():
                    raise RuntimeError("Cannot open video writer")
                self.recording = True

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

            return video_path
        except Exception as e:
            print(f"[Recording Error]: {e}")
            return None
        finally:
            self.stop_recording()
            self.configure_camera(3840, 2160)

    def stop_recording(self):
        """توقف ضبط"""
        with self.recording_lock:
            self.recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None