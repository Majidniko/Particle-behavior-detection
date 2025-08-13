#! /usr/bin/env python3
"""
camera.py
مدیریت دوربین Raspberry Pi با Picamera2 برای عکس و ویدئو
"""

from picamera2 import Picamera2
from libcamera import controls
import cv2
import os
import time
from threading import Lock

# -----------------------
# پیکربندی مسیر ذخیره فایل‌ها
# -----------------------
BASE_DIR = os.path.dirname(__file__)
MEDIA_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# -----------------------
# راه‌اندازی Picamera2
# -----------------------
picam2 = Picamera2()

# پیکربندی پیش‌فرض برای عکس (رزولوشن کامل)
fullres_config = picam2.create_video_configuration(
    main={"size": (3840, 2160)},  # رزولوشن کامل 4K
    lores={"size": (1024, 768)},   # برای نمایش پیش‌نمایش
    display="lores",
    encode="main"
)

picam2.set_controls({
    "FrameRate": 30.0,
})

picam2.configure(fullres_config)
picam2.start()
time.sleep(2)  # فرصت برای پایدار شدن

# -----------------------
# متغیرهای ضبط ویدئو
# -----------------------
recording = False
recording_lock = Lock()
video_writer = None


# -----------------------
# تولید فریم برای استریم MJPEG
# -----------------------
def gen_frames():
    """تولید فریم برای نمایش لحظه‌ای در مرورگر"""
    while True:
        try:
            frame = picam2.capture_array("lores")  # استفاده از استریم کم‌حجم برای پیش‌نمایش
            frame = cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB)

            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        except Exception as e:
            print(f"Frame capture error: {e}")
            time.sleep(0.1)
            continue


# -----------------------
# گرفتن عکس
# -----------------------
def capture_image():
    """گرفتن عکس با رزولوشن کامل"""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"image_{timestamp}.jpg"
    filepath = os.path.join(MEDIA_FOLDER, filename)

    picam2.capture_file(filepath)  # با کانفیگ fullres عکس گرفته می‌شود
    return filename


# -----------------------
# ضبط ویدئو
# -----------------------
def start_recording(duration=30):
    """
    ضبط ویدئو با رزولوشن پایین‌تر برای بهبود FPS
    بعد از پایان، دوربین به حالت عکس بازمی‌گردد
    """
    global recording, video_writer

    # --- توقف و تغییر به کانفیگ ویدئو ---
    picam2.stop()
    video_config = picam2.create_video_configuration(
        main={"size": (1920, 1080)},  # رزولوشن پایین‌تر برای ضبط ویدئو
        lores={"size": (640, 480)},
        display="lores",
        encode="main"
    )
    picam2.configure(video_config)
    picam2.start()
    time.sleep(1)

    # --- آماده‌سازی ضبط ---
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(MEDIA_FOLDER, f"video_{timestamp}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 15
    frame_size = (1920, 1080)

    with recording_lock:
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, frame_size)
        if not video_writer.isOpened():
            raise RuntimeError("Could not open video writer")
        recording = True

    print(f"Recording started: {video_path}")

    start_time = time.time()
    try:
        while recording and (time.time() - start_time) < duration:
            frame = picam2.capture_array("main")
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            with recording_lock:
                if video_writer is not None:
                    video_writer.write(frame)

            time.sleep(1 / fps)

    finally:
        with recording_lock:
            recording = False
            if video_writer is not None:
                video_writer.release()
                video_writer = None

        print(f"Recording saved: {video_path}")

        # --- برگرداندن رزولوشن کامل برای عکس ---
        picam2.stop()
        picam2.configure(fullres_config)
        picam2.start()
        time.sleep(1)

    return video_path
