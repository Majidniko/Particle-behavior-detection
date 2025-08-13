#! /usr/bin/env python3
"""
app.py
برنامه Flask برای کنترل دوربین Raspberry Pi
"""
from flask import Flask, render_template, Response, jsonify, request
from camera import gen_frames, capture_image, start_recording
# from updater import check_and_update  # اگر آپدیت خودکار داری

app = Flask(__name__)

@app.route('/')
def index():
    """صفحه اصلی"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """استریم ویدئو زنده"""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    """گرفتن عکس"""
    filename = capture_image()
    return jsonify({"status": "success", "filename": filename})

@app.route('/start_recording', methods=['POST'])
def start_rec():
    """شروع ضبط ویدئو"""
    try:
        duration = int(request.form.get("duration", 30))
        path = start_recording(duration=duration)
        return jsonify({"status": "success", "path": path})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # check_and_update()  # اگر لازم داری
    app.run(host='0.0.0.0', port=5000, threaded=True)
