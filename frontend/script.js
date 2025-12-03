const dropZone = document.getElementById("dropZone");
const imageInput = document.getElementById("imageInput");
const preview = document.getElementById("preview");
const predictBtn = document.getElementById("predictBtn");
const loading = document.getElementById("loading");
const resultCard = document.getElementById("resultCard");
const resultLabel = document.getElementById("resultLabel");
const confidenceLabel = document.getElementById("confidence");
const browseBtn = document.getElementById("browseBtn");
const clearBtn = document.getElementById("clearBtn");
const heatmapWrap = document.getElementById("heatmapWrap");

// CLICK to upload
dropZone.addEventListener("click", () => imageInput.click());
if (browseBtn) browseBtn.addEventListener("click", () => imageInput.click());
if (clearBtn) clearBtn.addEventListener("click", () => {
    // reset UI
    imageInput.value = null;
    preview.src = "";
    preview.classList.add("hidden");
    resultCard.classList.add("hidden");
    const err = document.getElementById("errorMsg"); if (err) { err.classList.add("hidden"); err.textContent = ""; }
    heatmapWrap.innerHTML = "";
    heatmapWrap.classList.add("hidden");
});
// explainBtn removed from UI — heatmapWrap retained for future use

// DRAG & DROP functionality
dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.background = "rgba(255,255,255,0.15)";
});

dropZone.addEventListener("dragleave", () => {
    dropZone.style.background = "rgba(255,255,255,0.05)";
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    imageInput.files = e.dataTransfer.files;
    showPreview();
});

// Show image preview
imageInput.addEventListener("change", showPreview);

function showPreview() {
    const file = imageInput.files[0];
    if (file) {
        preview.src = URL.createObjectURL(file);
        preview.classList.remove("hidden");
    }
}

// Predict button with improved loading animation and button locking
predictBtn.addEventListener("click", async () => {
    if (!imageInput.files[0]) {
        alert("Please upload an image first.");
        return;
    }

    // UI prep
    resultCard.classList.add("hidden");
    const errorMsg = document.getElementById("errorMsg");
    if (errorMsg) { errorMsg.classList.add("hidden"); errorMsg.textContent = ""; }

    // set loading state on button
    predictBtn.classList.add("loading");
    const spinner = predictBtn.querySelector('.btn-spinner');
    const label = predictBtn.querySelector('.btn-label');
    if (spinner) spinner.classList.remove('hidden');
    if (label) label.textContent = 'Analyzing...';
    // disable other controls while running
    browseBtn.disabled = true;
    clearBtn.disabled = true;

    const formData = new FormData();
    formData.append("image", imageInput.files[0]);

    try {
        const res = await fetch("http://localhost:5000/predict", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            let bodyText = `HTTP ${res.status} ${res.statusText}`;
            try {
                const errBody = await res.json();
                if (errBody && errBody.detail) bodyText = `${errBody.detail}`;
                else if (errBody && errBody.error) bodyText = `${errBody.error}`;
            } catch (e) {}
            throw new Error(bodyText);
        }

        const data = await res.json();

        // show results
        resultCard.classList.remove("hidden");
        resultLabel.textContent = data.prediction ? data.prediction : 'Unknown';
        confidenceLabel.textContent = data.confidence !== undefined ? (data.confidence * 100).toFixed(2) + "%" : 'N/A';

        const badge = document.getElementById("resultBadge");
        if (badge) {
            const c = data.confidence || 0;
            badge.classList.remove("hidden");
            if (c > 0.8) { badge.textContent = "High confidence"; }
            else if (c > 0.5) { badge.textContent = "Medium"; }
            else { badge.textContent = "Low"; }
        }
    } catch (err) {
        console.error("Error fetching prediction:", err);
        if (errorMsg) {
            errorMsg.textContent = "Could not contact the backend or the server returned an error: " + err.message;
            errorMsg.classList.remove("hidden");
        } else {
            alert("Could not contact the backend. Check DevTools console.\n" + err.message);
        }
    } finally {
        // restore button state
        predictBtn.classList.remove("loading");
        if (spinner) spinner.classList.add('hidden');
        if (label) label.textContent = 'Scan & Analyze';
        browseBtn.disabled = false;
        clearBtn.disabled = false;
    }
});
