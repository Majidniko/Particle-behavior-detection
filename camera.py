from flask import Flask, render_template, Response, request, jsonify
from picamera2 import Picamera2
import time, os, cv2
from threading import Lock
from libcamera import controls

app = Flask(__name__)
picam2 = Picamera2()

# تنظیم دوربین
config = picam2.create_video_configuration(
    main={"size": (3840, 2160)},
    lores={"size": (1024, 768)},
    display="lores",
    encode="main"
)
picam2.set_controls({"FrameRate": 30.0})
picam2.configure(config)
picam2.start()
time.sleep(2)

# مسیر ذخیره فایل‌ها
IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'static/images')
os.makedirs(IMAGE_FOLDER, exist_ok=True)

recording = False
paused = False
recording_lock = Lock()
video_writer = None
video_path = None

def gen_frames():
    while True:
        frame = picam2.capture_array("lores")
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    sample_id = request.form.get("sampleId", "").strip()
    if not sample_id:
        return {'status': 'error', 'message': 'Sample ID is required'}

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{sample_id}_{timestamp}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)
    picam2.capture_file(filepath)
    return {'status': 'success', 'filename': filename}

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording, video_writer, video_path
    sample_id = request.form.get("sampleId", "").strip()
    duration = int(request.form.get("duration", 10))

    if not sample_id:
        return jsonify({"status": "error", "message": "Sample ID is required"}), 400

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(IMAGE_FOLDER, f"{sample_id}_{timestamp}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(video_path, fourcc, 30, (3840, 2160))

    recording = True
    end_time = time.time() + duration

    def record_loop():
        global recording, paused
        while time.time() < end_time and recording:
            if paused:
                time.sleep(0.1)
                continue
            frame = picam2.capture_array("main")
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            video_writer.write(frame)
            time.sleep(1/30)
        stop_recording()

    from threading import Thread
    Thread(target=record_loop, daemon=True).start()
    return jsonify({"status": "success"})

@app.route('/pause_recording', methods=['POST'])
def pause_recording():
    global paused
    paused = not paused
    return jsonify({"status": "success"})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording, video_writer, video_path
    if recording:
        recording = False
        if video_writer:
            video_writer.release()
            video_writer = None
        return jsonify({"status": "success", "path": video_path})
    return jsonify({"status": "error", "message": "Not recording"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
