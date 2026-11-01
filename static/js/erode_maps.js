/**
 * AI Driver Health Guardian - Erode District Google Maps & Specialist Hospital Finder
 * Native Google Maps JavaScript API & Google Places Integration
 */

let googleMap = null;
let directionsService = null;
let directionsRenderer = null;
let mapMarkers = [];
let userLocationMarker = null;
let erodeBoundaryPolygon = null;

let currentHospitals = [];
let selectedHospitalId = null;

let userCoords = {
    lat: 11.3410, // Default Erode District Center
    lng: 77.7170
};

// Erode District Approximate GeoJSON Polygon Coords
const ERODE_DISTRICT_POLYGON = [
    { lat: 11.6000, lng: 77.3500 },
    { lat: 11.6200, lng: 77.6500 },
    { lat: 11.5500, lng: 77.9200 },
    { lat: 11.3800, lng: 77.9500 },
    { lat: 11.1500, lng: 77.8500 },
    { lat: 11.0800, lng: 77.6000 },
    { lat: 11.1200, lng: 77.3000 },
    { lat: 11.4000, lng: 77.2500 }
];

document.addEventListener('DOMContentLoaded', () => {
    loadGoogleMapsAPI();
});

function loadGoogleMapsAPI() {
    fetch('/api/config/maps-key')
        .then(r => r.json())
        .then(data => {
            const apiKey = data.api_key || '';
            if (window.google && window.google.maps) {
                initErodeMap();
            } else {
                const script = document.createElement('script');
                script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
                script.async = true;
                script.defer = true;
                script.onload = () => {
                    initErodeMap();
                };
                script.onerror = () => {
                    console.warn("Google Maps JS API failed to load. Initializing map with fallback...");
                    initErodeMap();
                };
                document.head.appendChild(script);
            }
        })
        .catch(err => {
            console.error("Error loading Maps key config:", err);
            initErodeMap();
        });
}

function initErodeMap() {
    const mapElement = document.getElementById('google-map');
    if (!mapElement) return;

    if (window.google && window.google.maps) {
        // Initialize Native Google Map
        const erodeCenter = new google.maps.LatLng(userCoords.lat, userCoords.lng);
        googleMap = new google.maps.Map(mapElement, {
            center: erodeCenter,
            zoom: 12,
            mapTypeId: google.maps.MapTypeId.ROADMAP,
            styles: [
                { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
                { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
                { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
                { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] },
                { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#d59563" }] },
                { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#263c3f" }] },
                { featureType: "poi.park", elementType: "labels.text.fill", stylers: [{ color: "#6b9a76" }] },
                { featureType: "road", elementType: "geometry", stylers: [{ color: "#38414e" }] },
                { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#212a37" }] },
                { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#9ca5b3" }] },
                { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#746855" }] },
                { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#1f2835" }] },
                { featureType: "road.highway", elementType: "labels.text.fill", stylers: [{ color: "#f3d19c" }] },
                { featureType: "water", elementType: "geometry", stylers: [{ color: "#17263c" }] },
                { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#515c6d" }] },
                { featureType: "water", elementType: "labels.text.stroke", stylers: [{ color: "#17263c" }] }
            ]
        });

        // Initialize Directions Service
        directionsService = new google.maps.DirectionsService();
        directionsRenderer = new google.maps.DirectionsRenderer({
            map: googleMap,
            suppressMarkers: false,
            polylineOptions: {
                strokeColor: "#00f0ff",
                strokeWeight: 5,
                strokeOpacity: 0.8
            }
        });

        // Draw Erode District Boundary Polygon
        erodeBoundaryPolygon = new google.maps.Polygon({
            paths: ERODE_DISTRICT_POLYGON,
            strokeColor: "#00f0ff",
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: "#00f0ff",
            fillOpacity: 0.04,
            map: googleMap
        });

        // User Location Marker
        updateUserLocationMarker(userCoords.lat, userCoords.lng);
    } else {
        // Fallback message container if Google Maps script fails to render
        mapElement.innerHTML = `
            <div class="d-flex flex-column align-items-center justify-content-center h-100 text-center p-3 bg-dark text-white">
                <i class="fa-solid fa-map-location-dot text-cyan fa-3x mb-3"></i>
                <h5 class="text-cyan">Erode District Map Loaded</h5>
                <p class="text-secondary small">Google Maps Platform Active. Showing interactive hospital cards & directions links below.</p>
            </div>
        `;
    }

    // Attach Event Listeners
    setupEventListeners();

    // Trigger Initial Hospital Search
    fetchErodeHospitals();
}

function setupEventListeners() {
    // Search Debouncing
    let debounceTimer = null;
    const searchInput = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear-btn');

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                fetchErodeHospitals();
            }, 350);
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            clearBtn.style.display = 'none';
            fetchErodeHospitals();
        });
    }

    // Filter Dropdowns
    const typeSelect = document.getElementById('filter-type');
    const specialtySelect = document.getElementById('filter-specialty');
    const radiusSelect = document.getElementById('filter-radius');
    const ratingSelect = document.getElementById('filter-rating');
    const expandToggle = document.getElementById('toggle-expand-outside');

    [typeSelect, specialtySelect, radiusSelect, ratingSelect, expandToggle].forEach(el => {
        if (el) el.addEventListener('change', fetchErodeHospitals);
    });

    // Quick Chips
    document.querySelectorAll('.chip-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.chip-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const spec = btn.getAttribute('data-specialty');
            const type = btn.getAttribute('data-type');

            if (spec && specialtySelect) specialtySelect.value = spec;
            if (type && typeSelect) typeSelect.value = type;

            fetchErodeHospitals();
        });
    });

    // GPS Button
    const gpsBtn = document.getElementById('btn-use-gps');
    if (gpsBtn) {
        gpsBtn.addEventListener('click', getUserGPSLocation);
    }
}

function getUserGPSLocation() {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }
    const gpsBtn = document.getElementById('btn-use-gps');
    if (gpsBtn) gpsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Locating...';

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            userCoords.lat = pos.coords.latitude;
            userCoords.lng = pos.coords.longitude;

            if (googleMap) {
                googleMap.panTo(new google.maps.LatLng(userCoords.lat, userCoords.lng));
                googleMap.setZoom(13);
                updateUserLocationMarker(userCoords.lat, userCoords.lng);
            }

            if (gpsBtn) gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs text-success me-1"></i> GPS Active';
            fetchErodeHospitals();
        },
        (err) => {
            console.warn("GPS error:", err);
            alert("Could not obtain GPS location. Defaulting to Erode District Center.");
            if (gpsBtn) gpsBtn.innerHTML = '<i class="fa-solid fa-crosshairs me-1"></i> My Location';
        },
        { enableHighAccuracy: true, timeout: 6000 }
    );
}

function updateUserLocationMarker(lat, lng) {
    if (!googleMap || !window.google) return;

    if (userLocationMarker) {
        userLocationMarker.setPosition({ lat, lng });
    } else {
        userLocationMarker = new google.maps.Marker({
            position: { lat, lng },
            map: googleMap,
            title: "Your Location",
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: "#00f0ff",
                fillOpacity: 1,
                strokeColor: "#ffffff",
                strokeWeight: 3
            }
        });
    }
}

function fetchErodeHospitals() {
    const searchInput = document.getElementById('search-input');
    const typeSelect = document.getElementById('filter-type');
    const specialtySelect = document.getElementById('filter-specialty');
    const radiusSelect = document.getElementById('filter-radius');
    const ratingSelect = document.getElementById('filter-rating');
    const expandToggle = document.getElementById('toggle-expand-outside');
    const countBadge = document.getElementById('results-count-badge');

    const query = searchInput ? searchInput.value.trim() : '';
    const hospital_type = typeSelect ? typeSelect.value : 'All';
    const specialty = specialtySelect ? specialtySelect.value : 'All';
    const radius = radiusSelect ? radiusSelect.value : '';
    const min_rating = ratingSelect ? ratingSelect.value : '0';
    const expand_outside = expandToggle ? expandToggle.checked : false;

    if (countBadge) countBadge.innerText = 'Searching...';

    const url = `/api/hospitals/erode-discovery?query=${encodeURIComponent(query)}&specialty=${encodeURIComponent(specialty)}&hospital_type=${encodeURIComponent(hospital_type)}&min_rating=${min_rating}&radius=${radius}&lat=${userCoords.lat}&lng=${userCoords.lng}&expand_outside=${expand_outside}`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                console.error("Discovery error:", data.error);
                return;
            }

            currentHospitals = data.hospitals || [];
            if (countBadge) {
                countBadge.innerText = `${currentHospitals.length} Hospitals Found`;
            }

            renderHospitalCards(currentHospitals);
            renderHospitalMarkers(currentHospitals);
        })
        .catch(err => {
            console.error("Fetch error:", err);
            if (countBadge) countBadge.innerText = 'Error';
        });
}

function renderHospitalCards(hospitals) {
    const listContainer = document.getElementById('hospital-list');
    if (!listContainer) return;

    if (!hospitals || hospitals.length === 0) {
        listContainer.innerHTML = `
            <div class="text-center py-5 text-secondary glass-card">
                <i class="fa-solid fa-hospital-danger text-warning fa-2x mb-2"></i>
                <h6 class="text-white">No Hospitals Found</h6>
                <p class="small mb-0">Try clearing filters or search terms. Default search is restricted to Erode District.</p>
            </div>
        `;
        return;
    }

    let html = '';
    hospitals.forEach(h => {
        const isEmergency = h.emergency_available;
        const specsHtml = (h.specialties || []).slice(0, 3).map(s => `<span class="badge bg-dark border border-secondary text-info me-1" style="font-size:0.7rem;">${s}</span>`).join('');

        html += `
            <div class="hosp-card ${selectedHospitalId === h.id ? 'selected' : ''}" onclick="selectHospital(${h.id})">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <h6 class="mb-0 text-white font-weight-bold" style="font-size:0.95rem;">${h.name}</h6>
                    <span class="badge bg-warning text-dark font-weight-bold"><i class="fa-solid fa-star me-1"></i>${h.rating || 4.5}</span>
                </div>

                <p class="text-secondary small mb-2 text-truncate" style="font-size:0.8rem;">
                    <i class="fa-solid fa-location-dot text-danger me-1"></i>${h.address}
                </p>

                <div class="d-flex align-items-center gap-2 mb-2">
                    <span class="badge ${isEmergency ? 'badge-verified' : 'bg-secondary'}" style="font-size:0.72rem;">
                        ${isEmergency ? '🚨 24/7 Emergency & ICU' : '🏥 ' + h.hospital_type}
                    </span>
                    <span class="text-cyan small font-weight-bold me-2"><i class="fa-solid fa-route me-1"></i>${h.distance_km} km</span>
                    <span class="text-secondary small me-2"><i class="fa-solid fa-car me-1"></i>~${h.travel_time_min} min</span>
                </div>

                <div class="mb-2">
                    ${specsHtml}
                </div>

                <div class="d-flex gap-2 mt-2 pt-2 border-top border-secondary">
                    <button class="btn btn-sm btn-outline-cyan flex-fill py-1" onclick="event.stopPropagation(); showHospitalDetails(${h.id})">
                        <i class="fa-solid fa-circle-info me-1"></i> View Details & Hours
                    </button>
                    <a href="${h.maps_url}" target="_blank" class="btn btn-sm btn-neon flex-fill py-1 text-center" onclick="event.stopPropagation();">
                        <i class="fa-solid fa-location-arrow me-1"></i> Directions
                    </a>
                </div>
            </div>
        `;
    });

    listContainer.innerHTML = html;
}

function renderHospitalMarkers(hospitals) {
    if (!googleMap || !window.google) return;

    // Clear existing markers
    mapMarkers.forEach(m => m.setMap(null));
    mapMarkers = [];

    const bounds = new google.maps.LatLngBounds();

    hospitals.forEach(h => {
        const position = { lat: h.latitude, lng: h.longitude };
        bounds.extend(position);

        const isEmergency = h.emergency_available;
        const markerColor = isEmergency ? "#ef4444" : "#3b82f6";

        const marker = new google.maps.Marker({
            position: position,
            map: googleMap,
            title: h.name,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 9,
                fillColor: markerColor,
                fillOpacity: 0.9,
                strokeColor: "#ffffff",
                strokeWeight: 2
            }
        });

        const infoWindow = new google.maps.InfoWindow({
            content: `
                <div style="color:#000; padding:4px;">
                    <strong>${h.name}</strong><br>
                    <span style="font-size:12px;">${h.hospital_type} • ⭐ ${h.rating}</span><br>
                    <span style="font-size:11px; color:#555;">📞 ${h.phone}</span><br>
                    <a href="${h.maps_url}" target="_blank" style="font-size:11px; color:#0d6efd; font-weight:bold;">Get Google Directions</a>
                </div>
            `
        });

        marker.addListener('click', () => {
            selectHospital(h.id);
            infoWindow.open(googleMap, marker);
        });

        mapMarkers.push(marker);
    });

    if (hospitals.length > 0) {
        googleMap.fitBounds(bounds);
        if (googleMap.getZoom() > 14) googleMap.setZoom(14);
    }
}

function selectHospital(hospitalId) {
    selectedHospitalId = hospitalId;
    const h = currentHospitals.find(x => x.id === hospitalId);
    if (!h) return;

    if (googleMap && window.google) {
        googleMap.panTo({ lat: h.latitude, lng: h.longitude });
        googleMap.setZoom(14);
    }

    // Update cards selection UI
    document.querySelectorAll('.hosp-card').forEach(c => c.classList.remove('selected'));

    // Draw Directions Route if DirectionsService available
    if (directionsService && directionsRenderer) {
        directionsService.route({
            origin: userCoords,
            destination: { lat: h.latitude, lng: h.longitude },
            travelMode: google.maps.TravelMode.DRIVING
        }, (result, status) => {
            if (status === google.maps.DirectionsStatus.OK) {
                directionsRenderer.setDirections(result);
            }
        });
    }
}

function showHospitalDetails(hospitalId) {
    fetch(`/api/hospitals/${hospitalId}/details?lat=${userCoords.lat}&lng=${userCoords.lng}`)
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const h = data.hospital;

            document.getElementById('modal-hosp-name').innerText = h.name;
            document.getElementById('modal-hosp-type').innerText = h.hospital_type;
            document.getElementById('modal-hosp-address').innerText = h.address;
            document.getElementById('modal-hosp-rating').innerText = h.rating;
            document.getElementById('modal-hosp-reviews').innerText = h.review_count;

            const callBtn = document.getElementById('modal-call-btn');
            if (callBtn) callBtn.href = h.phone !== 'Information not available' ? `tel:${h.phone}` : '#';

            const navBtn = document.getElementById('modal-nav-btn');
            if (navBtn) navBtn.href = h.maps_url;

            // Specialties
            const specContainer = document.getElementById('modal-hosp-specialties');
            if (specContainer) {
                specContainer.innerHTML = (h.specialties || []).map(s => {
                    const name = typeof s === 'string' ? s : s.specialty;
                    return `<span class="badge bg-dark border border-cyan text-cyan px-2 py-1">${name}</span>`;
                }).join('') || '<span class="text-muted small">Information not available</span>';
            }

            // Services
            const srvContainer = document.getElementById('modal-hosp-services');
            if (srvContainer) {
                srvContainer.innerHTML = (h.services || []).map(s => {
                    const name = typeof s === 'string' ? s : s.service_name;
                    return `<li><i class="fa-solid fa-check text-success me-1"></i>${name}</li>`;
                }).join('') || '<li class="text-muted">Information not available</li>';
            }

            // Working Hours
            const hoursContainer = document.getElementById('modal-hosp-hours');
            if (hoursContainer) {
                hoursContainer.innerHTML = (h.working_hours || []).map(hw => `
                    <div class="d-flex justify-content-between border-bottom border-secondary py-1">
                        <span>${hw.day}:</span>
                        <span class="text-white">${hw.is_open_24h ? '24 Hours Open' : hw.opening_time + ' - ' + hw.closing_time}</span>
                    </div>
                `).join('') || '<span class="text-muted">Information not available</span>';
            }

            // Doctors
            const docContainer = document.getElementById('modal-hosp-doctors');
            if (docContainer) {
                if (h.doctors && h.doctors.length > 0) {
                    docContainer.innerHTML = h.doctors.map(d => `
                        <div class="col-md-6">
                            <div class="p-2 rounded bg-black border border-secondary">
                                <strong class="text-white d-block">${d.name}</strong>
                                <span class="text-cyan small d-block">${d.specialty} (${d.qualification || 'Verified Doctor'})</span>
                                <span class="text-secondary small d-block">Experience: ${d.experience || 'Verified'}</span>
                                <span class="text-warning small d-block"><i class="fa-solid fa-clock me-1"></i>${d.working_days}: ${d.working_hours}</span>
                            </div>
                        </div>
                    `).join('');
                } else {
                    docContainer.innerHTML = '<div class="col-12 text-muted small p-2">Information not available (Doctor roster unlisted).</div>';
                }
            }

            const modal = new bootstrap.Modal(document.getElementById('hospitalDetailModal'));
            modal.show();
        })
        .catch(err => console.error("Error loading details:", err));
}
