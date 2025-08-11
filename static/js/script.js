document.getElementById("capture-btn").addEventListener("click", () => {
    fetch("/capture", { method: "POST" })
        .then(res => res.json())
        .then(data => {
            document.getElementById("message").innerHTML =
                 `<span class="text-success">Picture Saved ✅ عکس ذخیره شد \n Locate in: ${data.path} : محل ذخیره</span>`;
        });
});


document.getElementById("record-btn").addEventListener("click", () => {
    let duration = 30; // مدت ضبط به ثانیه (مثلاً 60)
    fetch("/start_recording", {
        method: "POST",
        body: new URLSearchParams({ "duration": duration }),
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
    .then(res => res.json())
    .then(data => {
        let progressBar = document.getElementById("record-progress");
        let message = document.getElementById("message");

        message.innerHTML = `<span class="text-warning">⏺ Video is recording for 30 secound duration ...   در حال ضبط ویدئو برای مدت 30 ثانیه</span>`;
        progressBar.style.width = "0%";
        progressBar.innerText = "0%";

        let elapsed = 0;
        let interval = setInterval(() => {
            elapsed++;
            let percent = Math.min((elapsed / duration) * 100, 100);
            progressBar.style.width = percent + "%";
            progressBar.innerText = Math.floor(percent) + "%";

            if (elapsed >= duration) {
                clearInterval(interval);
                message.innerHTML = `<span class="text-success"> Vide recording is finished ✅ ضبط به پایان رسید</span>`;
            }
        }, 1000);
    });
});

// تابع عکسبرداری با نمایش پیام انتظار
async function takePicture() {
    const processingModal = showProcessingModal();
    
    try {
        // شروع عکسبرداری
        const response = await fetch('/capture', { method: 'POST' });
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // بررسی وضعیت انتقال هر 2 ثانیه
        const checkInterval = setInterval(async () => {
            const statusResponse = await fetch(`/check_transfer/${encodeURIComponent(result.temp_path)}`);
            const status = await statusResponse.json();
            
            if (status.status === 'completed') {
                clearInterval(checkInterval);
                processingModal.hide();
                alert('تصویر با موفقیت ذخیره شد!');
            } else {
                processingModal.updateMessage(status.message);
            }
        }, 2000);
        
    } catch (error) {
        processingModal.hide();
        alert(`خطا: ${error.message}`);
    }
}

// تابع نمایش مودال انتظار
function showProcessingModal() {
    const modal = document.createElement('div');
    modal.innerHTML = `
        <div class="processing-modal" style="...">
            <div class="spinner"></div>
            <p id="processing-message">Please wait... file is being transferred</p>
        </div>
    `;
    document.body.appendChild(modal);
    
    return {
        hide: () => modal.remove(),
        updateMessage: (msg) => {
            document.getElementById('processing-message').textContent = msg;
        }
    };
}
