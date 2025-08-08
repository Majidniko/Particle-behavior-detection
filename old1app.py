#! /usr/bin/env python3

from flask import Flask, render_template, Response, request, jsonify
from picamera2 import Picamera2
import time
import os
from libcamera import controls
import cv2
import numpy as np
from threading import Lock
import time
from old1updater import check_and_update

app = Flask(__name__)
picam2 = Picamera2()

# Configure camera
#config = picam2.create_preview_configuration(main={"size": (1920, 1080)})
config = picam2.create_video_configuration(
    main={"size": (3840 , 2160)},  # Reduced resolution for better performance
    lores={"size": (1024, 768)},    # Lower resolution stream
    display="lores",               # Display lower resolution
    encode="main"
)
picam2.set_controls({
    #"AfMode": controls.AfModeEnum.Continuous,
    "FrameRate": 30.0,
    #"AwbMode": controls.AwbModeEnum.Auto
})
picam2.configure(config)
picam2.start()
time.sleep(2)  # Allow camera to stabilize

# Video recording variables
recording = False
recording_lock = Lock()
video_writer = None
media_folder = os.path.join(os.path.dirname(__file__), 'static/images')
os.makedirs(media_folder, exist_ok=True)


# Storage for images
IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'static/images')
os.makedirs(IMAGE_FOLDER, exist_ok=True)

def gen_frames():
    while True:
        try:
            # Capture frame with error handling
            frame = picam2.capture_array("main")  # Use lower resolution stream
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Encode as JPEG with quality adjustment
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue
                
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
        except Exception as e:
            print(f"Frame capture error: {e}")
            time.sleep(0.1)
            continue
#     while True:
#         frame = picam2.capture_array("main")
#         ret, buffer = cv2.imencode('.jpg', frame)
#         frame = buffer.tobytes()
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def start_recording():
    global recording, video_writer
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(media_folder, f"video_{timestamp}.mp4")
    
    # Use MJPG codec which is more reliably supported
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 15
   # frame_size = (1080 , 720)
    frame_size = (3840 , 2160)
    
    with recording_lock:
        video_writer = cv2.VideoWriter(video_path, fourcc, fps, frame_size)
        if not video_writer.isOpened():
            raise RuntimeError("Could not open video writer")
        recording = True
    
    print(f"Recording started: {video_path}")
    start_time = time.time()
    i=0
    try:
        t = time.time()
        while recording and (t - start_time) < 60:
            t = time.time()
            # Capture from main stream
            frame = picam2.capture_array("main")
            # Convert color space from RGB to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            with recording_lock:
                if video_writer is not None:
                    video_writer.write(frame)
            
            time.sleep(1/120)  # Maintain approx 30fps
            i+=1
            
            print("in", t,"i is:",i," ")
            
    finally:
        with recording_lock:
            recording = False
            if video_writer is not None:
                video_writer.release()
                video_writer = None
    
    print(f"Recording saved: {video_path}")
    return video_path

@app.route('/start_recording', methods=['POST'])
def handle_recording():
    try:
        video_path = start_recording()
        return jsonify({"status": "success", "path": video_path})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"image_{timestamp}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)
    picam2.capture_file(filepath)
    return {'status': 'success', 'filename': filename}

def Run():
    print("App is Starting Up...")
    # while True:
    #     print("Working...")
    #     time.sleep(5)
        
if __name__ == '__main__':
        # چک کردن آپدیت در ابتدای اجرا
    check_and_update()
    Run()
    app.run(host='0.0.0.0', port=5000, threaded=True)
