import os
import time
import cv2
from threading import Lock
from picamera2 import Picamera2
from libcamera import controls

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()

        # پیکربندی دوربین: main برای ضبط با کیفیت بالا، lores برای استریم سریع
        # config = self.picam2.create_video_configuration(
        #     main={"size": (3840, 2160)},
        #     # lores={"size": (800, 600)},  # RGB مستقیم
        #     # lores={"size": (800, 600), "format": "RGB888"},  # RGB مستقیم
        #     display="main",
        #     encode="main"
        # )
        config = self.picam2.create_video_configuration(
            main={"size": (800, 600)},
            encode="main"
        )
        self.picam2.set_controls({"FrameRate": 15.0})
        self.picam2.configure(config)
        self.picam2.start()
        time.sleep(2)  # منتظر ماندن برای پایدار شدن دوربین

        # متغیرهای ضبط
        self.recording = False
        self.recording_lock = Lock()
        self.video_writer = None

        # مسیرهای ذخیره‌سازی
        base_dir = os.path.dirname(__file__)
        self.image_folder = os.path.join(base_dir, 'static', 'media', 'images')
        self.video_folder = os.path.join(base_dir, 'static', 'media', 'videos')
        os.makedirs(self.image_folder, exist_ok=True)
        os.makedirs(self.video_folder, exist_ok=True)

    def stream_frames(self):
        """استریم ویدئو با کیفیت پایین برای روانی بیشتر"""
                # پیکربندی دوربین: main برای ضبط با کیفیت بالا، lores برای استریم سریع

        while True:
            try:
                # frame = self.picam2.capture_array("lores")
                # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                # frame = self.picam2.capture_array("lores")
                # if len(frame.shape) == 2 or frame.shape[2] == 1:
                #     # خاکستری
                #     frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                # elif frame.shape[2] == 2:  # YUV422
                #      frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUY2)
                # elif frame.shape[2] == 3:
                # # اگر مطمئن نیستی BGR یا RGB هست، بهتره تست کنی
                #     frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except Exception as e:
                print(f"[Stream Error]: {e}")
                time.sleep(0.1)

    def capture_image(self):
        config = self.picam2.create_video_configuration(
            main={"size": (3840, 2160)},
            encode="main"
        )
        self.picam2.set_controls({"FrameRate": 30.0})
        self.picam2.configure(config)
        self.picam2.start()
        """گرفتن عکس با کیفیت بالا"""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filepath = os.path.join(self.image_folder, f"image_{timestamp}.jpg")
        self.picam2.capture_file(filepath)
        return filepath

    def start_recording(self, duration=60):
        config = self.picam2.create_video_configuration(
            main={"size": (3840, 2160)},
            encode="main"
        )
        self.picam2.set_controls({"FrameRate": 30.0})
        self.picam2.configure(config)
        self.picam2.start()
        """شروع ضبط ویدئو با کیفیت بالا"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        video_path = os.path.join(self.video_folder, f"video_{timestamp}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 15
        frame_size = (3840, 2160)

        with self.recording_lock:
            self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, frame_size)
            if not self.video_writer.isOpened():
                raise RuntimeError("Cannot open video writer")
            self.recording = True

        start_time = time.time()
        try:
            while self.recording and (time.time() - start_time) < duration:
                frame = self.picam2.capture_array("main")
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                with self.recording_lock:
                    self.video_writer.write(frame)
                time.sleep(1 / 30)
        finally:
            self.stop_recording()
        return video_path

    def stop_recording(self):
        """توقف ضبط"""
        with self.recording_lock:
            self.recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
