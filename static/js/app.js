// ==============================================================================
// RoadGuard AI - Interactive Studio & Geospatial Dashboard Logic
// ==============================================================================

let map;
let markerLayerGroup;
let audioContext = null;

document.addEventListener("DOMContentLoaded", function () {
    initMap();
    loadMapMarkers();
    setupEventHandlers();
});

// ------------------------------------------------------------------------------
// Web Audio Warning Generator & Controllable Alarm System
// ------------------------------------------------------------------------------
let alarmInterval = null;
let isAudioMuted = false;
let isWarningActive = false;

function toggleAudioMute() {
    isAudioMuted = !isAudioMuted;
    const btn = document.getElementById("muteBtn");
    if (btn) {
        if (isAudioMuted) {
            btn.innerText = "🔇 Sound: MUTED";
            btn.classList.add("btn-danger");
            btn.classList.remove("btn-secondary");
            stopWarningAlarm();
        } else {
            btn.innerText = "🔊 Sound: ON";
            btn.classList.remove("btn-danger");
            btn.classList.add("btn-secondary");
        }
    }
}

function startWarningAlarm(severity) {
    stopWarningAlarm(); // Clear any existing alarm
    isWarningActive = true;

    // Show persistent stop buttons across navbar, form, and telemetry
    const navStopBtn = document.getElementById("navStopAlarmBtn");
    if (navStopBtn) navStopBtn.style.display = "inline-flex";

    const formStopBtn = document.getElementById("formStopWarningBtn");
    if (formStopBtn) formStopBtn.style.display = "inline-flex";

    const teleBox = document.getElementById("telemetryWarningBox");
    if (teleBox) teleBox.style.display = "block";

    if (isAudioMuted) return;

    try {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioContext.state === "suspended") {
            audioContext.resume();
        }

        const playBeep = () => {
            if (!isWarningActive || isAudioMuted || !audioContext) return;
            try {
                const osc = audioContext.createOscillator();
                const gain = audioContext.createGain();
                osc.connect(gain);
                gain.connect(audioContext.destination);

                let freq = (severity === "HIGH") ? 1760 : (severity === "MEDIUM" ? 1200 : 880);
                osc.frequency.setValueAtTime(freq, audioContext.currentTime);
                osc.type = "sine";

                gain.gain.setValueAtTime(0.25, audioContext.currentTime);
                gain.gain.linearRampToValueAtTime(0.001, audioContext.currentTime + 0.22);

                osc.start();
                osc.stop(audioContext.currentTime + 0.23);
            } catch (e) {
                console.warn("Beep audio error:", e);
            }
        };

        // Play initial beep
        playBeep();
        // Repeat pulse every 900ms until user clicks "Stop Warning"
        alarmInterval = setInterval(playBeep, 900);
    } catch (e) {
        console.warn("Alarm start error:", e);
    }
}

function playAudioTone(severity) {
    startWarningAlarm(severity);
}

function stopWarningAlarm() {
    isWarningActive = false;
    if (alarmInterval) {
        clearInterval(alarmInterval);
        alarmInterval = null;
    }
    if (audioContext && audioContext.state === "running") {
        try {
            audioContext.suspend();
        } catch (e) {}
    }
    const navStopBtn = document.getElementById("navStopAlarmBtn");
    if (navStopBtn) navStopBtn.style.display = "none";
}

function stopWarning() {
    // 1. Instantly silence the audio alarm
    stopWarningAlarm();

    // 2. Tell backend to silence any server-side buzzer
    fetch("/api/silence_alarm", { method: "POST" }).catch(() => {});

    // 3. Hide the warning banner and form stop button
    const banner = document.getElementById("hazardAlertBanner");
    if (banner) banner.style.display = "none";

    const formStopBtn = document.getElementById("formStopWarningBtn");
    if (formStopBtn) formStopBtn.style.display = "none";

    const teleBox = document.getElementById("telemetryWarningBox");
    if (teleBox) teleBox.style.display = "none";

    // 4. Keep dashboard active! It does NOT close the dashboard.
    console.log("🛑 Warning silenced and dismissed. Dashboard remains open and fully active.");
}

// ------------------------------------------------------------------------------
// Studio Tab Switching
// ------------------------------------------------------------------------------
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.add("active");

    const activeBtn = Array.from(document.querySelectorAll(".tab-btn")).find(btn =>
        btn.getAttribute("onclick") && btn.getAttribute("onclick").includes(tabId)
    );
    if (activeBtn) activeBtn.classList.add("active");
}

// ------------------------------------------------------------------------------
// Vehicle Mode Switcher (Car vs Bike)
// ------------------------------------------------------------------------------
function setVehicleMode(mode) {
    fetch("/api/set_vehicle_mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("modeCarBtn").classList.toggle("active", mode === "Car Dashcam");
        document.getElementById("modeBikeBtn").classList.toggle("active", mode !== "Car Dashcam");
        const resMode = document.getElementById("resMode");
        if (resMode) resMode.innerText = mode;
    })
    .catch(err => console.error("Error setting vehicle mode:", err));
}

// ------------------------------------------------------------------------------
// Image Detection (Start Here)
// ------------------------------------------------------------------------------
let selectedUploadFile = null;

function onFileSelected(input) {
    if (input.files && input.files[0]) {
        selectedUploadFile = input.files[0];
        const nameLabel = document.getElementById("selectedFileName");
        if (nameLabel) {
            nameLabel.innerText = "Selected: " + selectedUploadFile.name;
            nameLabel.style.color = "#38bdf8";
        }
    }
}

function submitUploadedImage() {
    if (!selectedUploadFile) {
        alert("Please choose a road image file first, or click 'Test with Road Sample'!");
        return;
    }
    const submitBtn = document.getElementById("submitBtn");
    if (submitBtn) {
        submitBtn.innerText = "⏳ Running YOLO Detection...";
        submitBtn.disabled = true;
    }
    triggerImageDetection(selectedUploadFile, false);
}

function runSampleDetection(sampleType = "mixed") {
    let btn = document.getElementById("sampleBtn");
    if (sampleType === "highway") btn = document.getElementById("highwayBtn");
    if (sampleType === "clean") btn = document.getElementById("cleanBtn");

    if (btn) {
        btn.innerText = "⏳ Running AI...";
        btn.disabled = true;
    }
    triggerImageDetection(null, true, sampleType);
}

function triggerImageDetection(file, useSample, sampleType = "mixed") {
    const formData = new FormData();
    if (useSample) {
        formData.append("use_sample", "true");
        formData.append("sample_type", sampleType);
    } else if (file) {
        formData.append("image", file);
    }

    const emptyState = document.getElementById("emptyImageState");
    const activeResult = document.getElementById("activeImageResult");
    if (emptyState) emptyState.style.display = "none";
    if (activeResult) activeResult.style.display = "grid";

    document.getElementById("resStatus").innerText = "Analyzing Frame via Ultralytics YOLO...";

    fetch("/api/detect_image", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            // Update preview and telemetry
            document.getElementById("resultImagePreview").src = data.result_image + "?t=" + new Date().getTime();
            document.getElementById("resStatus").innerText = "Detection Completed";
            document.getElementById("resCount").innerText = data.count + " Potholes Found";
            
            const sevBadge = document.getElementById("resSeverity");
            sevBadge.innerText = data.max_severity;
            sevBadge.className = "badge badge-" + data.max_severity.toLowerCase();

            document.getElementById("resGPS").innerText = `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`;
            document.getElementById("resMode").innerText = data.vehicle_mode;

            // Trigger visual HUD banner and sound if hazards were detected
            if (data.count > 0 && data.max_severity !== "NONE") {
                const topConf = data.detections && data.detections.length > 0 ? data.detections[0].conf : 96;
                showHazardWarning(data.max_severity, data.count, topConf, data.latitude, data.longitude);
                startWarningAlarm(data.max_severity);
            } else {
                stopWarning();
            }

            // Refresh table and map
            refreshDashboardData();
        } else {
            alert("Detection error: " + data.message);
        }
    })
    .catch(err => {
        console.error("Image detection error:", err);
        alert("Failed to run detection: " + err);
    })
    .finally(() => {
        const submitBtn = document.getElementById("submitBtn");
        const sampleBtn = document.getElementById("sampleBtn");
        const highwayBtn = document.getElementById("highwayBtn");
        const cleanBtn = document.getElementById("cleanBtn");
        if (submitBtn) {
            submitBtn.innerText = "🚀 SUBMIT & RUN AI DETECTION";
            submitBtn.disabled = false;
        }
        if (sampleBtn) {
            sampleBtn.innerText = "⚡ Mixed Craters (Low & High Risk)";
            sampleBtn.disabled = false;
        }
        if (highwayBtn) {
            highwayBtn.innerText = "🛣️ Highway Road (Doc Page 3)";
            highwayBtn.disabled = false;
        }
        if (cleanBtn) {
            cleanBtn.innerText = "✅ Clean Road (Zero Potholes)";
            cleanBtn.disabled = false;
        }
    });
}

function showHazardWarning(severity, count, conf = 96, lat = 17.3850, lon = 78.4867) {
    const banner = document.getElementById("hazardAlertBanner");
    const title = document.getElementById("hazardTitle");
    const subtitle = document.getElementById("hazardSubtitle");
    const badge = document.getElementById("hazardBadge");

    if (title) title.innerText = `POTHOLE AHEAD`;
    if (subtitle) subtitle.innerText = `⚠ ${conf}% | Severity: ${severity} | Location: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    if (badge) {
        badge.innerText = `${severity} SEVERITY`;
        badge.className = `badge badge-${severity.toLowerCase()}`;
    }

    if (banner) {
        banner.style.display = "flex";
        // Stays visible so user can click "🛑 Stop Warning & Silence Alarm" at any time!
    }
}

function stopDashboardServer() {
    if (!confirm("Are you sure you want to stop the RoadGuard AI Dashboard server?")) {
        return;
    }
    fetch("/api/shutdown", { method: "POST" })
        .then(res => res.json())
        .then(data => {
            alert("🛑 Dashboard Server has been shut down successfully!\nYou can now close this browser tab.");
            document.body.innerHTML = `
                <div style="text-align: center; padding: 120px 20px; color: #f8fafc; font-family: 'Inter', sans-serif;">
                    <h1 style="font-size: 2.5rem; margin-bottom: 16px;">🛑 System Stopped</h1>
                    <p style="color: #94a3b8; font-size: 1.1rem;">The RoadGuard AI dashboard server has been safely stopped.</p>
                    <p style="color: #64748b; margin-top: 10px;">You can now close this browser tab.</p>
                </div>
            `;
        })
        .catch(err => {
            alert("Server shutdown signal sent. You can close this tab.");
        });
}

// ------------------------------------------------------------------------------
// Video File Playback Handlers (Recorded Dashcam Footage)
// ------------------------------------------------------------------------------
function startTestVideoPlayback() {
    const videoImg = document.getElementById("videoFileStreamFeed");
    const placeholder = document.getElementById("videoPlaceholder");
    const startBtn = document.getElementById("startTestVideoBtn");
    const stopBtn = document.getElementById("stopVideoBtn");

    fetch("/api/start_video_file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ use_sample: true })
    })
    .then(res => res.json())
    .then(data => {
        videoImg.src = "/video_file_feed?t=" + new Date().getTime();
        videoImg.style.display = "block";
        placeholder.style.display = "none";
        if (startBtn) startBtn.style.display = "none";
        if (stopBtn) stopBtn.style.display = "inline-flex";
    });
}

function uploadAndPlayVideo(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    const nameLabel = document.getElementById("selectedVideoName");
    if (nameLabel) nameLabel.innerText = "Uploaded: " + file.name;

    const formData = new FormData();
    formData.append("video", file);

    const videoImg = document.getElementById("videoFileStreamFeed");
    const placeholder = document.getElementById("videoPlaceholder");
    const startBtn = document.getElementById("startTestVideoBtn");
    const stopBtn = document.getElementById("stopVideoBtn");

    fetch("/api/upload_video", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            videoImg.src = "/video_file_feed?t=" + new Date().getTime();
            videoImg.style.display = "block";
            placeholder.style.display = "none";
            if (startBtn) startBtn.style.display = "none";
            if (stopBtn) stopBtn.style.display = "inline-flex";
        } else {
            alert("Video upload failed: " + data.message);
        }
    })
    .catch(err => alert("Video upload error: " + err));
}

function stopVideoPlayback() {
    const videoImg = document.getElementById("videoFileStreamFeed");
    const placeholder = document.getElementById("videoPlaceholder");
    const startBtn = document.getElementById("startTestVideoBtn");
    const stopBtn = document.getElementById("stopVideoBtn");

    fetch("/api/stop_video_file", { method: "POST" })
        .then(() => {
            videoImg.src = "";
            videoImg.style.display = "none";
            placeholder.style.display = "block";
            if (startBtn) startBtn.style.display = "inline-flex";
            if (stopBtn) stopBtn.style.display = "none";
            refreshDashboardData();
        });
}

// ------------------------------------------------------------------------------
// Live Camera Stream Handlers
// ------------------------------------------------------------------------------
function startCameraStream() {
    const liveImg = document.getElementById("liveStreamFeed");
    const placeholder = document.getElementById("camPlaceholder");
    const startBtn = document.getElementById("startCamBtn");
    const stopBtn = document.getElementById("stopCamBtn");

    liveImg.src = "/video_feed";
    liveImg.style.display = "block";
    placeholder.style.display = "none";
    startBtn.style.display = "none";
    stopBtn.style.display = "inline-flex";
}

function stopCameraStream() {
    const liveImg = document.getElementById("liveStreamFeed");
    const placeholder = document.getElementById("camPlaceholder");
    const startBtn = document.getElementById("startCamBtn");
    const stopBtn = document.getElementById("stopCamBtn");

    fetch("/api/stop_camera", { method: "POST" })
        .then(() => {
            liveImg.src = "";
            liveImg.style.display = "none";
            placeholder.style.display = "block";
            startBtn.style.display = "inline-flex";
            stopBtn.style.display = "none";
            refreshDashboardData();
        });
}

// ------------------------------------------------------------------------------
// Geospatial Map (Leaflet.js)
// ------------------------------------------------------------------------------
function initMap() {
    map = L.map("potholeMap").setView([19.0760, 72.8777], 14);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    markerLayerGroup = L.layerGroup().addTo(map);
}

function getSeverityColor(severity) {
    switch (severity.toUpperCase()) {
        case "HIGH":
            return "#ef4444";
        case "MEDIUM":
            return "#f97316";
        case "LOW":
            return "#eab308";
        default:
            return "#3b82f6";
    }
}

function loadMapMarkers() {
    fetch("/api/detections")
        .then(res => res.json())
        .then(data => {
            markerLayerGroup.clearLayers();
            const validCoords = [];

            data.forEach(item => {
                if (item.latitude && item.longitude) {
                    const latLng = [item.latitude, item.longitude];
                    validCoords.push(latLng);

                    const color = getSeverityColor(item.severity);

                    const marker = L.circleMarker(latLng, {
                        radius: item.severity === "HIGH" ? 10 : (item.severity === "MEDIUM" ? 8 : 6),
                        fillColor: color,
                        color: "#ffffff",
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.85
                    });

                    const popupContent = `
                        <div style="font-family: sans-serif; font-size: 12px; width: 170px;">
                            <strong style="color: ${color}; font-size: 13px;">[!] ${item.severity} SEVERITY</strong><br/>
                            <span style="color: #555;">Confidence: ${(item.confidence * 100).toFixed(1)}%</span><br/>
                            <span style="color: #777;">Time: ${item.timestamp}</span><br/>
                            <div style="margin-top: 6px;">
                                <img src="/detections/${item.image_path}" 
                                     style="width: 100%; height: 85px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc; cursor: pointer;"
                                     onclick="openImageModal('/detections/${item.image_path}')" />
                            </div>
                        </div>
                    `;

                    marker.bindPopup(popupContent);
                    markerLayerGroup.addLayer(marker);
                }
            });

            if (validCoords.length > 0) {
                map.fitBounds(validCoords, { padding: [40, 40], maxZoom: 16 });
            }
        })
        .catch(err => console.error("Error loading map pins:", err));
}

function setupEventHandlers() {
    document.getElementById("severityFilter").addEventListener("change", function (e) {
        const selected = e.target.value;
        const rows = document.querySelectorAll("#detectionTableBody tr[data-severity]");

        rows.forEach(row => {
            const severity = row.getAttribute("data-severity");
            if (selected === "ALL" || severity === selected) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    });
}

function refreshDashboardData() {
    fetch("/api/stats")
        .then(res => res.json())
        .then(stats => {
            document.getElementById("kpiTotal").innerText = stats.total;
            document.getElementById("kpiHigh").innerText = stats.high;
            document.getElementById("kpiMedium").innerText = stats.medium;
            document.getElementById("kpiLow").innerText = stats.low;
        });

    loadMapMarkers();
}

function deleteRecord(id) {
    if (!confirm(`Are you sure you want to delete detection record #${id}?`)) {
        return;
    }

    fetch(`/api/detections/${id}`, { method: "DELETE" })
        .then(res => res.json())
        .then(() => location.reload())
        .catch(err => alert("Error deleting record: " + err));
}

// Modal functions
function openImageModal(imgSrc) {
    const modal = document.getElementById("imageModal");
    const modalImg = document.getElementById("modalImg");
    modal.style.display = "block";
    modalImg.src = imgSrc;
}

function closeImageModal() {
    document.getElementById("imageModal").style.display = "none";
}
