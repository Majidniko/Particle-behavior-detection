document.getElementById("capture-btn").addEventListener("click", () => {
    fetch("/capture", { method: "POST" })
        .then(res => res.json())
        .then(data => {
            document.getElementById("message").innerHTML =
                `<span class="text-success">Picture Saved ✅ عکس ذخیره شد \n Locate in: ${data.path} : محل ذخیره</span>`;
        });
});

document.getElementById("record-btn").addEventListener("click", () => {
    fetch("/start_recording", {
        method: "POST",
        body: new URLSearchParams({ "duration": 60 }),
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("message").innerHTML =
            `<span class="text-warning">⏺ در حال ضبط ویدئو...</span>`;
            `<span class="text-warning">⏺ Video is recording...</span>`;
    });
});
