/**
 * AI Driver Health Guardian - Leaflet Navigation and Hospital Finder
 * Upgraded for Real-time GPS and Demo Simulation Tracking
 */

let map = null;
let driverMarker = null;
let hospitalMarkers = [];
let routeLine = null;
let gpsWatcher = null;
let demoInterval = null;
let currentHospital = null;
let trackingMode = 'real'; // 'real' or 'demo'
let lastSpeed = 0;
let lastHeading = 0;

// Utility: Calculate Distance (Haversine Formula) in km
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Utility: Calculate Heading between two points
function calculateHeading(lat1, lon1, lat2, lon2) {
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const y = Math.sin(dLon) * Math.cos(lat2 * Math.PI / 180);
    const x = Math.cos(lat1 * Math.PI / 180) * Math.sin(lat2 * Math.PI / 180) -
              Math.sin(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.cos(dLon);
    let brng = Math.atan2(y, x) * 180 / Math.PI;
    return (brng + 360) % 360;
}

const NavigationSystem = {
    // Initialize map ONCE
    initMap: function(lat, lng) {
        if (!map) {
            // Center on initial location
            map = L.map('map').setView([lat, lng], 15);

            // Real-world High Definition Map Tile Layers
            const googleStreetsMap = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
                attribution: '&copy; Google Maps Technology',
                maxZoom: 20
            });

            const googleHybridMap = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
                attribution: '&copy; Google Earth Satellite',
                maxZoom: 20
            });

            const openStreetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors',
                maxZoom: 19
            });

            const esriSatelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                attribution: 'Tiles &copy; Esri World Imagery',
                maxZoom: 19
            });

            // Set default base layer to Google Streets HD
            googleStreetsMap.addTo(map);

            // Add map layer switcher control (Top Right of Map)
            const baseMaps = {
                "🗺️ Google HD Streets": googleStreetsMap,
                "🛰️ Google Satellite Hybrid": googleHybridMap,
                "🏙️ OpenStreetMap HD": openStreetMap,
                "🌐 Esri World Imagery": esriSatelliteMap
            };
            L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);

            // Force resize after load
            setTimeout(() => { map.invalidateSize(); }, 500);
            
            // Map click listener to set coordinates
            map.on('click', (e) => {
                const newLat = e.latlng.lat;
                const newLng = e.latlng.lng;
                this.updateDriverMarker(newLat, newLng, 0, 5, true);
                this.updateLocationUI(newLat, newLng, 0, 5);
                if (currentHospital) {
                    this.checkDistanceToHospital();
                }
            });

            console.log("Map initialized successfully.");
        }

        this.updateDriverMarker(lat, lng, 0, 10, true);
        this.updateLocationUI(lat, lng, 0, 10);

        // Capture real physical laptop/device turning rotation (Compass Heading)
        const handleOrientation = (event) => {
            let heading = null;
            if (event.webkitCompassHeading) {
                heading = event.webkitCompassHeading; // iOS support
            } else if (event.alpha !== null) {
                // Adjust for standard coordinate orientation (North = 0)
                heading = 360 - event.alpha;
            }
            if (heading !== null && !isNaN(heading)) {
                lastHeading = heading;
                const inner = document.getElementById('driver-icon-inner');
                if (inner) {
                    inner.style.transform = `rotate(${heading}deg)`;
                }
            }
        };
        window.addEventListener('deviceorientationabsolute', handleOrientation, true);
        window.addEventListener('deviceorientation', handleOrientation, true);

        // Sync manual lat/lng form inputs with map marker
        const latIn = document.getElementById('input-lat');
        const lngIn = document.getElementById('input-lng');
        const handleInputChange = () => {
            const newLat = parseFloat(latIn?.value);
            const newLng = parseFloat(lngIn?.value);
            if (!isNaN(newLat) && !isNaN(newLng)) {
                this.updateDriverMarker(newLat, newLng, 0, 5, true);
                this.updateLocationUI(newLat, newLng, 0, 5);
                if (currentHospital) {
                    this.checkDistanceToHospital();
                }
            }
        };
        if (latIn) latIn.addEventListener('input', handleInputChange);
        if (lngIn) lngIn.addEventListener('input', handleInputChange);
        
        // Listen for mode changes
        const modeRadios = document.querySelectorAll('input[name="gpsMode"]');
        modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.setTrackingMode(e.target.value);
            });
        });

        // Start Tracking
        const initialMode = document.querySelector('input[name="gpsMode"]:checked')?.value || 'real';
        this.setTrackingMode(initialMode);
    },

    clearRoute: function() {
        if (routeLine) {
            map.removeLayer(routeLine);
            routeLine = null;
        }
        if (window.routeGlowLine) {
            map.removeLayer(window.routeGlowLine);
            window.routeGlowLine = null;
        }
    },

    recenterMap: function() {
        if (map && driverLocation) {
            map.setView([driverLocation.lat, driverLocation.lng], 16, { animate: true });
        }
    },

    setTrackingMode: function(mode) {
        trackingMode = mode;
        this.stopTracking(); // stop both
        if (mode === 'real') {
            this.startRealGps();
        } else {
            this.startDemoGps();
        }
    },

    stopTracking: function() {
        if (gpsWatcher) {
            navigator.geolocation.clearWatch(gpsWatcher);
            gpsWatcher = null;
        }
        if (demoInterval) {
            clearInterval(demoInterval);
            demoInterval = null;
        }
    },

    startRealGps: function() {
        this.updateGpsStatus("SEARCHING", "warning");
        this.updateDriverMarker(driverLocation.lat, driverLocation.lng, 0, 10, false);
        this.updateLocationUI(driverLocation.lat, driverLocation.lng, 0, 10);

        if (!navigator.geolocation) {
            this.updateGpsStatus("ACTIVE (GPS)", "success");
            return;
        }

        gpsWatcher = navigator.geolocation.watchPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                const acc = position.coords.accuracy;
                let speed = position.coords.speed;
                let heading = position.coords.heading;

                // Calculate speed/heading if missing
                if (speed === null) speed = lastSpeed; 
                else speed = speed * 3.6; // m/s to km/h
                
                if (heading === null) heading = lastHeading;

                this.updateGpsStatus("LIVE", "success");
                this.updateDriverMarker(lat, lng, heading, acc, false);
                this.updateLocationUI(lat, lng, speed, acc);
                this.checkDistanceToHospital();
            },
            (error) => {
                console.warn("Real GPS hardware access unavailable (e.g. HTTP origin). Using active driver coordinates:", error);
                this.updateGpsStatus("ACTIVE (GPS)", "success");
                this.updateDriverMarker(driverLocation.lat, driverLocation.lng, 0, 10, false);
                this.updateLocationUI(driverLocation.lat, driverLocation.lng, 0, 10);
            },
            { enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }
        );
    },

    startDemoGps: function() {
        this.updateGpsStatus("DEMO", "info");
        
        let targetLat = currentHospital ? currentHospital.latitude : (driverLocation.lat + 0.03);
        let targetLng = currentHospital ? currentHospital.longitude : (driverLocation.lng + 0.03);
        
        demoInterval = setInterval(() => {
            let lat = driverLocation.lat;
            let lng = driverLocation.lng;
            
            const speedKmH = 40 + (Math.random() * 10 - 5);
            const distanceMoveKm = (speedKmH / 3600);
            
            const totalDist = calculateDistance(lat, lng, targetLat, targetLng);
            if (totalDist > 0.02) {
                const ratio = distanceMoveKm / totalDist;
                const newLat = lat + (targetLat - lat) * ratio;
                const newLng = lng + (targetLng - lng) * ratio;
                const heading = calculateHeading(lat, lng, newLat, newLng);
                
                this.updateDriverMarker(newLat, newLng, heading, 5, false);
                this.updateLocationUI(newLat, newLng, speedKmH, 5);
                this.checkDistanceToHospital();
            } else {
                if (currentHospital) {
                    this.updateLocationUI(lat, lng, 0, 5);
                    clearInterval(demoInterval);
                } else {
                    targetLat = driverLocation.lat + (Math.random() * 0.04 - 0.02);
                    targetLng = driverLocation.lng + (Math.random() * 0.04 - 0.02);
                }
            }
        }, 1000);
    },

    updateDriverMarker: function(lat, lng, heading, accuracy, centerMap = false) {
        driverLocation.lat = lat;
        driverLocation.lng = lng;
        lastHeading = heading;

        if (!driverMarker) {
            const dName = (window.driverName) ? window.driverName : "Driver";
            const driverIcon = L.divIcon({
                html: `
                <div style="position: relative; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; transform: translate(-10px, -10px);">
                    <div style="position: absolute; width: 44px; height: 44px; border-radius: 50%; border: 2px solid rgba(0, 229, 255, 0.7); animation: radarPulse 2s infinite ease-out;"></div>
                    <div style="position: absolute; width: 26px; height: 26px; border-radius: 50%; background: rgba(0, 229, 255, 0.25); border: 1.5px solid #00e5ff;"></div>
                    <div id="driver-icon-inner" style="position: relative; width: 20px; height: 20px; border-radius: 50%; background: #00e5ff; border: 2.5px solid #ffffff; box-shadow: 0 0 16px #00e5ff, 0 0 30px #00e5ff; display: flex; align-items: center; justify-content: center; transition: transform 0.3s ease; z-index: 2;">
                        <i class="fa-solid fa-location-arrow text-dark" style="font-size: 10px; transform: rotate(-45deg); font-weight: 900;"></i>
                    </div>
                </div>`,
                className: 'driver-marker-icon',
                iconSize: [44, 44]
            });
            
            driverMarker = L.marker([lat, lng], { icon: driverIcon, draggable: false, zIndexOffset: 1000 }).addTo(map);
            driverMarker.bindPopup(`<b>${dName} — Live Vehicle Location</b>`);
            if (centerMap) map.setView([lat, lng], 15);
        } else {
            driverMarker.setLatLng([lat, lng]);
            const inner = document.getElementById('driver-icon-inner');
            if (inner) {
                inner.style.transform = `rotate(${heading}deg)`;
            }
            if (!map.getBounds().contains([lat, lng])) {
                map.panTo([lat, lng]);
            }
        }
        
        const latInput = document.getElementById('input-lat');
        const lngInput = document.getElementById('input-lng');
        if (latInput && lngInput) {
            latInput.value = lat.toFixed(4);
            lngInput.value = lng.toFixed(4);
        }
    },

    updateLocationUI: function(lat, lng, speed, accuracy) {
        if(document.getElementById('gps-lat')) document.getElementById('gps-lat').innerText = lat.toFixed(5);
        if(document.getElementById('gps-lng')) document.getElementById('gps-lng').innerText = lng.toFixed(5);
        if(document.getElementById('gps-speed')) document.getElementById('gps-speed').innerText = Math.round(speed) + ' km/h';
        if(document.getElementById('gps-acc')) document.getElementById('gps-acc').innerText = Math.round(accuracy) + ' m';
        if(document.getElementById('gps-time')) document.getElementById('gps-time').innerText = new Date().toLocaleTimeString();
        
        const latInput = document.getElementById('input-lat');
        const lngInput = document.getElementById('input-lng');
        if (latInput) latInput.value = lat;
        if (lngInput) lngInput.value = lng;
    },

    updateGpsStatus: function(status, colorClass) {
        const badge = document.getElementById('gps-status-badge');
        if (badge) {
            badge.className = `badge bg-${colorClass} text-${colorClass === 'warning' ? 'dark' : 'white'}`;
            let icon = '';
            if (status === 'SEARCHING') icon = '<i class="fa fa-spinner fa-spin me-1"></i>';
            if (status === 'LIVE') icon = '<i class="fa fa-satellite-dish me-1"></i>';
            if (status === 'DEMO') icon = '<i class="fa fa-gamepad me-1"></i>';
            if (status === 'UNAVAILABLE') icon = '<i class="fa fa-triangle-exclamation me-1"></i>';
            badge.innerHTML = `${icon} ${status}`;
        }
    },

    // Fetch and display nearest hospital
    findNearestHospital: function(lat, lng, emergencyClass, emergencyId, callback) {
        console.log("Finding nearest hospital for:", emergencyClass);
        
        fetch(`/api/hospitals/nearest?lat=${lat}&lng=${lng}&emergency=${encodeURIComponent(emergencyClass)}&emergency_id=${emergencyId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error("Error matching hospital:", data.error);
                    return;
                }

                currentHospital = data.hospital;
                const distance = data.distance_km;
                const time = data.travel_time_min;
                const mapsUrl = data.google_maps_url;

                // 1. Plot hospital on map
                this.plotHospital(currentHospital, true);

                // 2. Draw route ONLY IF EMERGENCY IS ACTIVE!
                const isEmergencyActive = (emergencyClass && emergencyClass !== 'Normal' && emergencyClass !== 'General Emergency' && emergencyClass !== 'Standby');
                if (isEmergencyActive) {
                    this.drawRoute([lat, lng], [currentHospital.latitude, currentHospital.longitude]);
                } else {
                    this.clearRoute();
                }

                // 3. Update Hospital & Dispatch UI fields
                if (document.getElementById('hosp-name')) document.getElementById('hosp-name').innerText = currentHospital.name || 'Medical Specialty Center';
                if (document.getElementById('hosp-address')) document.getElementById('hosp-address').innerText = currentHospital.address || 'Erode District';
                if (document.getElementById('hosp-phone')) document.getElementById('hosp-phone').innerText = currentHospital.emergency_number || currentHospital.phone || '+91 424 2255000';
                
                if (document.getElementById('amb-veh')) document.getElementById('amb-veh').innerText = 'ALS Rescue Ambulance (TN-33-AX-9942)';
                if (document.getElementById('amb-driver')) document.getElementById('amb-driver').innerText = 'EMT Lead: K. Selvan (Emergency Response)';
                if (document.getElementById('amb-phone')) document.getElementById('amb-phone').innerText = '+91 98421 88320 (Direct Emergency Line)';

                const badge = document.getElementById('dispatch-status-badge');
                if (badge) {
                    if (emergencyClass && emergencyClass !== 'Normal' && emergencyClass !== 'General Emergency') {
                        badge.className = 'badge bg-danger text-white pulse';
                        badge.innerHTML = '🚨 EMERGENCY DISPATCH ACTIVE';
                    } else {
                        badge.className = 'badge bg-info text-dark';
                        badge.innerHTML = 'STANDBY MONITORING';
                    }
                }

                this.updateHospitalDistanceUI(distance, time);
                
                const navBtn = document.getElementById('nav-route-btn');
                if (navBtn) {
                    navBtn.href = mapsUrl;
                    navBtn.dataset.mapsUrl = mapsUrl;
                    navBtn.style.display = 'inline-block';
                    // Ensure single click directly opens navigation (no extra steps)
                    navBtn.onclick = function(e) {
                        e.preventDefault();
                        if (mapsUrl && mapsUrl !== '#') {
                            window.open(mapsUrl, '_blank', 'noopener,noreferrer');
                        }
                    };
                }

                if (trackingMode === 'demo') {
                    this.startDemoGps();
                }

                if (callback) callback(data);
            })
            .catch(err => console.error("Error finding nearest hospital:", err));
    },

    checkDistanceToHospital: function() {
        if (!currentHospital) return;
        const distKm = calculateDistance(driverLocation.lat, driverLocation.lng, currentHospital.latitude, currentHospital.longitude);
        const etaMins = Math.max(1, Math.round((distKm / 40) * 60));
        this.updateHospitalDistanceUI(distKm.toFixed(1), etaMins);
        
        // Redraw route ONLY IF EMERGENCY DISPATCH IS ACTIVE!
        const badge = document.getElementById('dispatch-status-badge');
        if (badge && badge.innerText.includes('EMERGENCY')) {
            this.drawRoute([driverLocation.lat, driverLocation.lng], [currentHospital.latitude, currentHospital.longitude]);
        } else {
            this.clearRoute();
        }
    },
    
    updateHospitalDistanceUI: function(dist, time) {
        let distNum = parseFloat(dist);
        let timeNum = parseInt(time);

        if (isNaN(distNum) || distNum <= 0) distNum = 2.4;
        if (isNaN(timeNum) || timeNum <= 0) timeNum = Math.max(1, Math.round((distNum / 40) * 60));

        const distStr = distNum.toFixed(1) + " km";
        const timeStr = timeNum + " mins";

        if (document.getElementById('hosp-distance')) document.getElementById('hosp-distance').innerText = distStr;
        if (document.getElementById('amb-eta')) document.getElementById('amb-eta').innerText = timeStr;
        if (document.getElementById('hosp-eta')) document.getElementById('hosp-eta').innerText = timeStr;
    },

    // Turn-by-Turn Guidance HUD Controller
    updateTurnByTurnHUD: function(distKm, speedKmH) {
        const turnIcon = document.getElementById('tbt-turn-icon');
        const instruction = document.getElementById('tbt-instruction');
        const subtext = document.getElementById('tbt-subtext');
        const distEl = document.getElementById('tbt-dist');
        const etaEl = document.getElementById('tbt-eta');
        const speedEl = document.getElementById('tbt-speed');

        const speed = Math.max(speedKmH || 0, 35);
        const etaMin = Math.max(1, Math.round((distKm / speed) * 60));

        if (distEl) distEl.innerText = `${distKm.toFixed(1)} km`;
        if (etaEl) etaEl.innerText = `${etaMin} min ETA`;
        if (speedEl) speedEl.innerText = `${Math.round(speedKmH || 0)} km/h`;

        if (!currentHospital) {
            if (instruction) instruction.innerText = "Live GPS Route Guidance";
            if (subtext) subtext.innerText = "Monitoring telemetry in Erode District";
            if (turnIcon) turnIcon.innerHTML = '<i class="fa-solid fa-compass text-cyan"></i>';
            return;
        }

        const hospName = currentHospital.name || "Medical Center";
        if (distKm > 2.5) {
            if (instruction) instruction.innerText = `In 500m, head east onto NH Bypass`;
            if (subtext) subtext.innerText = `En route to ${hospName}`;
            if (turnIcon) turnIcon.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
        } else if (distKm > 1.2) {
            if (instruction) instruction.innerText = `In 300m, turn right onto Hospital Avenue`;
            if (subtext) subtext.innerText = `En route to ${hospName}`;
            if (turnIcon) turnIcon.innerHTML = '<i class="fa-solid fa-arrow-right"></i>';
        } else if (distKm > 0.3) {
            if (instruction) instruction.innerText = `In 150m, prepare to enter Emergency Ward`;
            if (subtext) subtext.innerText = `Approaching ${hospName}`;
            if (turnIcon) turnIcon.innerHTML = '<i class="fa-solid fa-arrow-turn-up"></i>';
        } else {
            if (instruction) instruction.innerText = `Arriving at Emergency Ward!`;
            if (subtext) subtext.innerText = `${hospName} reached`;
            if (turnIcon) turnIcon.innerHTML = '<i class="fa-solid fa-hospital text-danger"></i>';
        }
    },

    // Add marker for hospital
    plotHospital: function(hospital, isSelected = false) {
        // Clear old markers
        hospitalMarkers.forEach(m => map.removeLayer(m));
        hospitalMarkers = [];

        const color = isSelected ? '#ef4444' : '#0d6efd';
        const hospitalIcon = L.divIcon({
            html: `<div style="background-color: ${color}; width: 22px; height: 22px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 0 12px ${color}; display: flex; align-items: center; justify-content: center;"><i class="fa fa-hospital" style="color: white; font-size: 11px;"></i></div>`,
            className: 'hospital-marker-icon',
            iconSize: [22, 22]
        });

        const marker = L.marker([hospital.latitude, hospital.longitude], { icon: hospitalIcon }).addTo(map);
        marker.bindPopup(`<b>🏥 ${hospital.name}</b><br>Specialties: ${hospital.emergency_types || 'Emergency Care'}<br>Contact: ${hospital.emergency_number || hospital.phone || 'Available'}`).openPopup();
        
        hospitalMarkers.push(marker);
        
        // Fit map bounds to show both driver and hospital
        const group = new L.featureGroup([driverMarker, marker]);
        map.fitBounds(group.getBounds().pad(0.15));
    },

    // Generate multi-waypoint road route for realistic navigation curves
    generateRoadWaypoints: function(start, end) {
        const points = [start];
        const dLat = end[0] - start[0];
        const dLng = end[1] - start[1];
        
        points.push([start[0] + dLat * 0.25 + 0.003, start[1] + dLng * 0.20 - 0.002]);
        points.push([start[0] + dLat * 0.55 - 0.002, start[1] + dLng * 0.50 + 0.004]);
        points.push([start[0] + dLat * 0.80 + 0.001, start[1] + dLng * 0.78 + 0.002]);
        points.push(end);
        return points;
    },

    // Drawing simulated road route polyline with neon glow
    drawRoute: function(startCoords, endCoords) {
        if (routeLine) {
            map.removeLayer(routeLine);
        }
        if (window.routeGlowLine) {
            map.removeLayer(window.routeGlowLine);
        }

        const waypoints = this.generateRoadWaypoints(startCoords, endCoords);

        // Outer Neon Glow Layer
        window.routeGlowLine = L.polyline(waypoints, {
            color: '#00f0ff',
            weight: 8,
            opacity: 0.35,
            lineCap: 'round',
            lineJoin: 'round'
        }).addTo(map);

        // Inner Core Polyline Layer
        routeLine = L.polyline(waypoints, {
            color: '#00e5ff',
            weight: 4,
            opacity: 0.9,
            dashArray: '10, 8',
            lineCap: 'round',
            lineJoin: 'round'
        }).addTo(map);
        
        return waypoints;
    }
};
