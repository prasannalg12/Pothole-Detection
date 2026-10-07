// ==============================================================================
// RoadGuard AI - Interactive Dashboard Script (Leaflet & Dynamic Updates)
// ==============================================================================

let map;
let markerLayerGroup;

document.addEventListener("DOMContentLoaded", function () {
    initMap();
    loadMapMarkers();
    setupEventHandlers();
});

function initMap() {
    // Default center (e.g., coordinates from config or initial view)
    map = L.map("potholeMap").setView([19.0760, 72.8777], 14);

    // OpenStreetMap dark/standard tile layer
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

                    // Circle Marker with severity-based styling
                    const marker = L.circleMarker(latLng, {
                        radius: item.severity === "HIGH" ? 10 : (item.severity === "MEDIUM" ? 8 : 6),
                        fillColor: color,
                        color: "#ffffff",
                        weight: 2,
                        opacity: 1,
                        fillOpacity: 0.85
                    });

                    // Interactive popup content
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

            // Adjust map view bounds to encompass all pins
            if (validCoords.length > 0) {
                map.fitBounds(validCoords, { padding: [40, 40], maxZoom: 16 });
            }
        })
        .catch(err => console.error("Error loading detection pins:", err));
}

function setupEventHandlers() {
    // Refresh Button
    document.getElementById("refreshBtn").addEventListener("click", function () {
        refreshData();
    });

    // Severity Filter
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

function refreshData() {
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
        .then(data => {
            location.reload();
        })
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
