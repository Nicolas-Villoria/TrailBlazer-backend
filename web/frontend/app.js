// TrailBlazer - Main Application JavaScript

// Configuration
const API_BASE = 'http://localhost:8000';

// Global state
let map;
let startMarker;
let searchCircle = null;  // Visual circle showing search area
let searchRadius = 10;    // Default 10 km radius
let monumentMarkers = [];
let routeLayer;
let currentJobId = null;
let pollInterval = null;

// Initialize application
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 TrailBlazer initializing...');
    initMap();
    await checkAPIConnection();
});

// Toggle control panel
function togglePanel() {
    const panel = document.getElementById('controlPanel');
    const btn = panel.querySelector('.collapse-btn i');
    
    if (panel.classList.contains('collapsed')) {
        panel.classList.remove('collapsed');
        btn.className = 'fas fa-bars';
    } else {
        panel.classList.add('collapsed');
        btn.className = 'fas fa-chevron-right';
    }
}

// Initialize Leaflet map
function initMap() {
    // Center on Catalunya with zoom controls in bottom right
    map = L.map('map', {
        zoomControl: false  // Disable default zoom control
    }).setView([41.5, 1.5], 8);
    
    // Add zoom control to bottom right
    L.control.zoom({
        position: 'bottomright'
    }).addTo(map);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Click handler for setting start point
    map.on('click', function(e) {
        setStartPoint(e.latlng.lat, e.latlng.lng);
    });
    
    // Set initial start point (Barcelona)
    setStartPoint(41.3851, 2.1734);
    
    console.log('✅ Map initialized');
}

// Check API connection
async function checkAPIConnection() {
    const statusEl = document.getElementById('apiStatus');
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            statusEl.className = 'api-status api-connected';
            statusEl.innerHTML = '<i class="fas fa-check-circle"></i> API Connected';
            console.log('✅ API connection successful');
            return true;
        }
    } catch (error) {
        console.error('❌ API connection failed:', error);
    }
    
    statusEl.className = 'api-status api-disconnected';
    statusEl.innerHTML = '<i class="fas fa-times-circle"></i> API Disconnected';
    return false;
}

// Set start point on map
function setStartPoint(lat, lng) {
    if (startMarker) {
        map.removeLayer(startMarker);
    }
    
    startMarker = L.marker([lat, lng], {
        icon: L.icon({
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        })
    }).addTo(map);
    
    startMarker.bindPopup('<b>🚀 Start Point</b>').openPopup();
    
    document.getElementById('startLat').value = lat.toFixed(6);
    document.getElementById('startLon').value = lng.toFixed(6);
    
    // Update search circle
    updateSearchCircle(lat, lng, searchRadius);
    
    console.log(`📍 Start point set: ${lat.toFixed(4)}, ${lng.toFixed(4)}`);
}

// Update search radius
function updateSearchRadius(radius) {
    searchRadius = parseFloat(radius);
    document.getElementById('radiusDisplay').textContent = searchRadius;
    
    const lat = parseFloat(document.getElementById('startLat').value);
    const lon = parseFloat(document.getElementById('startLon').value);
    
    if (lat && lon) {
        updateSearchCircle(lat, lon, searchRadius);
    }
    
    console.log(`📏 Search radius updated: ${searchRadius} km`);
}

// Update search circle on map
function updateSearchCircle(lat, lng, radiusKm) {
    // Remove existing circle
    if (searchCircle) {
        map.removeLayer(searchCircle);
    }
    
    // Add new circle (radius in meters)
    searchCircle = L.circle([lat, lng], {
        color: '#00796B',
        fillColor: '#00796B',
        fillOpacity: 0.1,
        radius: radiusKm * 1000,  // Convert km to meters
        weight: 2,
        dashArray: '5, 10'
    }).addTo(map);
    
    searchCircle.bindPopup(`<b>Search Area</b><br>Radius: ${radiusKm} km`);
}

// Convert circle to bounding box
function getCircleBounds() {
    const lat = parseFloat(document.getElementById('startLat').value);
    const lon = parseFloat(document.getElementById('startLon').value);
    
    if (!lat || !lon) {
        throw new Error('Start point not set');
    }
    
    // Earth's radius in km
    const R = 6371;
    
    // Convert radius from km to degrees (approximate)
    // 1 degree latitude ≈ 111 km
    const latDelta = searchRadius / 111;
    
    // 1 degree longitude varies by latitude
    const lonDelta = searchRadius / (111 * Math.cos(lat * Math.PI / 180));
    
    return {
        bottom_left: {
            lat: lat - latDelta,
            lon: lon - lonDelta
        },
        top_right: {
            lat: lat + latDelta,
            lon: lon + lonDelta
        }
    };
}

// Use current geolocation
function setCurrentLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                setStartPoint(lat, lng);
                map.setView([lat, lng], 12);
            },
            function(error) {
                alert('Error getting location: ' + error.message);
            }
        );
    } else {
        alert('Geolocation is not supported by your browser.');
    }
}

// Preview monuments in current map view
async function previewMonuments() {
    const monumentType = document.getElementById('monumentType').value;
    
    if (!monumentType) {
        alert('Please select a monument type first.');
        return;
    }
    
    try {
        // Get bounding box from search circle
        const bounds = getCircleBounds();
        const url = `${API_BASE}/monuments?monument_type=${monumentType}` +
                   `&bottom_left_lat=${bounds.bottom_left.lat}` +
                   `&bottom_left_lon=${bounds.bottom_left.lon}` +
                   `&top_right_lat=${bounds.top_right.lat}` +
                   `&top_right_lon=${bounds.top_right.lon}`;
        
        console.log('🏰 Fetching monuments within', searchRadius, 'km radius:', url);
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        displayMonuments(data.monuments);
        
    } catch (error) {
        console.error('Error loading monuments:', error);
        alert('Error loading monuments: ' + error.message);
    }
}

// Display monuments on map and in list
function displayMonuments(monuments) {
    // Clear existing markers
    monumentMarkers.forEach(marker => map.removeLayer(marker));
    monumentMarkers = [];
    
    // Add new markers
    monuments.forEach(monument => {
        const marker = L.marker([monument.location.lat, monument.location.lon], {
            icon: L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            })
        }).addTo(map);
        
        marker.bindPopup(`<b>${monument.name}</b>`);
        monumentMarkers.push(marker);
    });
    
    // Display in list
    const monumentsList = document.getElementById('monumentsList');
    monumentsList.innerHTML = '';
    
    monuments.forEach((monument, index) => {
        const card = document.createElement('div');
        card.className = 'monument-card';
        card.innerHTML = `
            <strong>${index + 1}. ${monument.name}</strong><br>
            <small class="text-muted">
                <i class="fas fa-map-marker-alt"></i> 
                ${monument.location.lat.toFixed(4)}, ${monument.location.lon.toFixed(4)}
            </small>
        `;
        monumentsList.appendChild(card);
    });
    
    document.getElementById('monumentCount').textContent = monuments.length;
    document.getElementById('monumentsSection').style.display = 'block';
    
    console.log(`✅ Displayed ${monuments.length} monuments`);
}

// Calculate routes
async function calculateRoutes() {
    const lat = parseFloat(document.getElementById('startLat').value);
    const lon = parseFloat(document.getElementById('startLon').value);
    const monumentType = document.getElementById('monumentType').value;
    
    if (!lat || !lon) {
        alert('Please set a start point first.');
        return;
    }
    
    if (!monumentType) {
        alert('Please select a monument type.');
        return;
    }
    
    // Get search area from circle bounds
    const bounds = getCircleBounds();
    
    const requestData = {
        start_point: {
            lat: lat,
            lon: lon
        },
        monument_type: monumentType,
        search_box: {
            bottom_left: bounds.bottom_left,
            top_right: bounds.top_right
        }
    };
    
    console.log(`🧮 Calculating routes within ${searchRadius} km radius:`, requestData);
    
    try {
        const response = await fetch(`${API_BASE}/routes/calculate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        currentJobId = data.job_id;
        
        console.log(`✅ Job created: ${currentJobId}`);
        
        // Show progress section
        document.getElementById('jobId').textContent = currentJobId;
        document.getElementById('progressSection').style.display = 'block';
        document.getElementById('resultsSection').style.display = 'none';
        
        // Start polling
        startPolling();
        
    } catch (error) {
        console.error('Error starting route calculation:', error);
        alert('Error starting route calculation: ' + error.message);
    }
}

// Start polling for job status
function startPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    pollInterval = setInterval(checkJobStatus, 2000);
    checkJobStatus(); // Check immediately
}

// Check job status
async function checkJobStatus() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`${API_BASE}/routes/job/${currentJobId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const job = await response.json();
        updateProgress(job);
        
        if (job.status === 'completed') {
            clearInterval(pollInterval);
            displayResults(job.result);
        } else if (job.status === 'failed') {
            clearInterval(pollInterval);
            alert('Route calculation failed: ' + job.error);
            document.getElementById('progressSection').style.display = 'none';
        }
        
    } catch (error) {
        console.error('Error checking job status:', error);
    }
}

// Update progress display
function updateProgress(job) {
    const progress = Math.round(job.progress * 100);
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const statusEl = document.getElementById('progressStatus');
    const jobStatusBadge = document.getElementById('jobStatus');
    
    progressBar.style.width = progress + '%';
    progressText.textContent = progress + '%';
    
    // Update status badge
    jobStatusBadge.className = `status-badge status-${job.status}`;
    jobStatusBadge.textContent = job.status.charAt(0).toUpperCase() + job.status.slice(1);
    
    // Update status message
    let message = '';
    if (progress < 20) {
        message = '<i class="fas fa-rocket"></i> Initializing...';
    } else if (progress < 40) {
        message = '<i class="fas fa-download"></i> Downloading trail segments...';
    } else if (progress < 60) {
        message = '<i class="fas fa-project-diagram"></i> Building graph network...';
    } else if (progress < 80) {
        message = '<i class="fas fa-landmark"></i> Finding monuments...';
    } else if (progress < 100) {
        message = '<i class="fas fa-route"></i> Calculating routes...';
    } else {
        message = '<i class="fas fa-check-circle"></i> Complete!';
    }
    statusEl.innerHTML = message;
}

// Display final results
function displayResults(result) {
    console.log('🎉 Results received:', result);
    
    // Hide progress, show results
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    
    // Update counts
    document.getElementById('reachableCount').textContent = result.reachable_monuments || 0;
    document.getElementById('unreachableCount').textContent = result.unreachable_monuments || 0;
    
    // Update download links
    if (result.png_url) {
        document.getElementById('downloadPNG').href = API_BASE + result.png_url;
    }
    if (result.kml_url) {
        document.getElementById('downloadKML').href = API_BASE + result.kml_url;
    }
    
    // Display route details
    const detailsEl = document.getElementById('routeDetails');
    detailsEl.innerHTML = '';
    
    // Reachable monuments
    if (result.routes && result.routes.length > 0) {
        result.routes.forEach((route, index) => {
            const card = document.createElement('div');
            card.className = 'monument-card';
            card.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong><i class="fas fa-check-circle text-success"></i> ${route.monument}</strong><br>
                        <small class="text-muted">
                            <i class="fas fa-map-marker-alt"></i> 
                            ${route.location.lat.toFixed(4)}, ${route.location.lon.toFixed(4)}
                        </small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-primary" style="font-size: 1em;">
                            ${route.distance_km ? route.distance_km.toFixed(2) + ' km' : 'N/A'}
                        </span>
                    </div>
                </div>
            `;
            detailsEl.appendChild(card);
        });
    }
    
    // Unreachable monuments
    if (result.unreachable && result.unreachable.length > 0) {
        result.unreachable.forEach((monument) => {
            const card = document.createElement('div');
            card.className = 'monument-card';
            card.style.opacity = '0.6';
            card.innerHTML = `
                <div>
                    <strong><i class="fas fa-times-circle text-warning"></i> ${monument.monument}</strong><br>
                    <small class="text-muted">
                        <i class="fas fa-exclamation-triangle"></i> No path available
                    </small>
                </div>
            `;
            detailsEl.appendChild(card);
        });
    }
}
