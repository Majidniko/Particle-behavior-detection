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
