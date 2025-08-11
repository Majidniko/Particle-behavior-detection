from flask import Flask, render_template, Response, jsonify, request
from camera import Camera
# from updater import check_and_update
import threading

app = Flask(__name__)
camera = Camera()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(camera.stream_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    # filepath = camera.capture_image()
    # return jsonify({"status": "success", "path": filepath})
    try:
        temp_path = camera.capture_image()
        if temp_path:
            return jsonify({
                'status': 'processing',
                'message': 'Please wait... file is being transferred to flash',
                'temp_path': temp_path
            })
        else:
            return jsonify({'error': 'Failed to capture image'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/check_transfer/<path:temp_path>')
def check_transfer(temp_path):
    """بررسی وضعیت انتقال فایل"""
    if os.path.exists(temp_path):
        return jsonify({
            'status': 'processing',
            'message': 'Transfer still in progress...'
        })
    else:
        return jsonify({
            'status': 'completed',
            'message': 'File transfer completed successfully'
        })


@app.route('/start_recording', methods=['POST'])
def start_recording():
    duration = int(request.form.get("duration", 60))
    threading.Thread(target=camera.start_recording, args=(duration,), daemon=True).start()
    return jsonify({"status": "recording started", "duration": duration})

if __name__ == '__main__':
    #check_and_update()
    app.run(host='0.0.0.0', port=5000, threaded=True)
