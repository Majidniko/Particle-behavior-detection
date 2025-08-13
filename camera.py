import os
import time
import cv2
from picamera2 import Picamera2
from libcamera import controls
from threading import Lock
import shutil

# 📌 مسیرهای ذخیره
LOCAL_IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'static/images')
LOCAL_VIDEO_FOLDER = os.path.join(os.path.dirname(__file__), 'static/videos')
os.makedirs(LOCAL_IMAGE_FOLDER, exist_ok=True)
os.makedirs(LOCAL_VIDEO_FOLDER, exist_ok=True)

# 📌 مسیر USB (اینجا فرض می‌کنیم فلش در این مسیر mount شده)
USB_MOUNT_PATH = "/media/pi/USB"

# قفل برای جلوگیری از تداخل ضبط
recording_lock = Lock()
recording = False
video_writer = None

# راه‌اندازی دوربین
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (3840, 2160)},
    capture={"size": (1920, 1080)},
    lores={"size": (1024, 768)},
    display="lores",
    encode="main"
)
picam2.set_controls({
    "FrameRate": 30.0
})
picam2.configure(config)
picam2.start()
time.sleep(2)

def find_usb_mount():
    """
    جستجوی خودکار مسیر فلش USB
    مسیرها معمولاً در /media/<username>/USB_NAME قرار دارند
    """
    media_root = "/media"
    if not os.path.exists(media_root):
        return None

    # بررسی تمام پوشه‌ها در /media
    for root, dirs, files in os.walk(media_root):
        for dir_name in dirs:
            mount_path = os.path.join(root, dir_name)
            # اگر مسیر mount شده باشد و پوشه باشد، به عنوان USB در نظر می‌گیریم
            if os.path.ismount(mount_path):
                return mount_path
    return None

def is_usb_connected():
    """بررسی اتصال فلش USB با جستجوی خودکار"""
    usb_path = find_usb_mount()
    return usb_path is not None

def move_to_usb(local_path):
    """انتقال فایل به USB و حذف نسخه محلی"""
    usb_path = find_usb_mount()
    if not usb_path:
        raise RuntimeError("حافظه خارجی متصل نیست")

    destination_path = os.path.join(usb_path, os.path.basename(local_path))
    shutil.move(local_path, destination_path)  # انتقال و حذف فایل محلی
    return destination_path

def gen_frames():
    """ارسال فریم‌ها برای پیش‌نمایش"""
    while True:
        try:
            frame = picam2.capture_array("lores")
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

def capture_image():
    """گرفتن عکس و ذخیره در USB"""
    if not is_usb_connected():
        raise RuntimeError("حافظه خارجی متصل نیست")

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    local_path = os.path.join(LOCAL_IMAGE_FOLDER, f"image_{timestamp}.jpg")
    
    picam2.capture_file(local_path)

    usb_path = move_to_usb(local_path)
    return usb_path

def start_recording(duration):
    if not is_usb_connected():
        raise RuntimeError("USB not connected")

    global recording, video_writer
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    local_path = os.path.join(LOCAL_VIDEO_FOLDER, f"video_{timestamp}.mp4")
    os.makedirs(LOCAL_VIDEO_FOLDER, exist_ok=True)  # Ensure folder exists


    # Get camera resolution dynamically
    test_frame = picam2.capture_array("capture")
    frame_size = (test_frame.shape[1], test_frame.shape[0])  # (width, height)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 30

    with recording_lock:
        video_writer = cv2.VideoWriter(local_path, fourcc, fps, frame_size)
        if not video_writer.isOpened():  # Critical check!
            raise RuntimeError(f"VideoWriter failed for {local_path}")
        recording = True

    start_time = time.time()
    try:
        while recording and (time.time() - start_time) < duration:
            frame = picam2.capture_array("main")
            if frame is None:  # Check for empty frames
                print("Warning: Empty frame captured")
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with recording_lock:
                if video_writer is not None:
                    video_writer.write(frame)
            time.sleep(1 / fps)
    except Exception as e:
        print("Recording error:", str(e))
        raise
    finally:
        with recording_lock:
            recording = False
            if video_writer is not None:
                video_writer.release()
                video_writer = None

    usb_path = move_to_usb(local_path)
    return usb_path