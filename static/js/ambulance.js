/**
 * AI Driver Health Guardian - Ambulance Dispatch Tracking Simulation
 */

let ambulanceMarker;
let animationFrameId;

const AmbulanceSimulation = {
    // Start ambulance simulation
    dispatchAmbulance: function(emergencyId, driverLat, driverLng, pathPoints) {
        console.log("Requesting ambulance dispatch...");
        
        // Clear previous ambulance animation if any
        if (ambulanceMarker) {
            map.removeLayer(ambulanceMarker);
        }
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }

        // Trigger dispatch API
        fetch('/api/ambulance/dispatch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                emergency_id: emergencyId,
                driver_lat: driverLat,
                driver_lng: driverLng
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                MainApp.showNotification("Ambulance Alert", data.error, "warning");
                return;
            }

            const amb = data.ambulance;
            const eta = data.eta_minutes;
            const cancelledCount = data.cancelled_nearby_ambulances_count;

            // Show simulation popups
            setTimeout(() => {
                MainApp.showNotification("📞 Dispatch System", "Calling nearest ambulances...", "info");
                this.updateAlertBanner("Calling Ambulance...", "Searching nearby vehicles...");
            }, 500);

            setTimeout(() => {
                MainApp.showNotification("🚨 Emergency Alert", `Ambulance ${amb.vehicle_number} Accepted!`, "success");
                this.updateAlertBanner(`Ambulance Accepted`, `ETA: ${eta} Minutes | Driver: ${amb.driver_name}`);
                
                if (cancelledCount > 0) {
                    MainApp.showNotification("System Rule Triggered", `Cancelled alerts for ${cancelledCount} ambulances within 500m radius.`, "info");
                }
                
                // Update text elements on dashboard
                document.getElementById('amb-veh').innerText = amb.vehicle_number;
                document.getElementById('amb-driver').innerText = amb.driver_name;
                document.getElementById('amb-phone').innerText = amb.driver_phone;
                document.getElementById('amb-eta').innerText = eta + " mins";

                // Initialize ambulance marker at its starting point (amb.latitude, amb.longitude)
                const ambulanceIcon = L.divIcon({
                    html: '<div style="background-color: #ef4444; width: 16px; height: 16px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 0 10px #ef4444; display: flex; align-items: center; justify-content: center;"><i class="fa fa-ambulance" style="color: white; font-size: 8px;"></i></div>',
                    className: 'ambulance-marker-icon',
                    iconSize: [16, 16]
                });

                ambulanceMarker = L.marker([amb.latitude, amb.longitude], { icon: ambulanceIcon }).addTo(map);
                ambulanceMarker.bindPopup(`<b>Ambulance ${amb.vehicle_number}</b><br>Driver: ${amb.driver_name}<br>Status: Dispatched`).openPopup();

                // Animate ambulance moving towards the driver along the path
                // Path points: [Ambulance start -> path points backwards or custom route]
                // Since route is startCoords -> endCoords (driver to hospital), let's create a route from Ambulance to Driver
                const ambulanceStart = [amb.latitude, amb.longitude];
                const driverLocation = [driverLat, driverLng];
                
                // Create custom route points for ambulance to reach driver
                const mid1 = [
                    ambulanceStart[0] + (driverLocation[0] - ambulanceStart[0]) * 0.5,
                    ambulanceStart[1] + (driverLocation[1] - ambulanceStart[1]) * 0.5
                ];
                const ambPath = [ambulanceStart, mid1, driverLocation];
                
                this.animateVehicle(ambulanceMarker, ambPath, eta);

            }, 2500);
        })
        .catch(err => console.error("Error dispatching ambulance:", err));
    },

    // Animate a marker along a set of coordinates
    animateVehicle: function(marker, path, totalEtaMinutes) {
        let currentStep = 0;
        const totalSteps = 250; // Total frames for animation
        const interval = 80; // Speed of animation tick (ms)
        
        let alerted500m = false;
        let alerted100m = false;
        
        // Generate interpolated points along the path
        const interpolatedPoints = [];
        const legsCount = path.length - 1;
        const stepsPerLeg = Math.floor(totalSteps / legsCount);
        
        for (let i = 0; i < legsCount; i++) {
            const start = path[i];
            const end = path[i+1];
            
            for (let j = 0; j < stepsPerLeg; j++) {
                const ratio = j / stepsPerLeg;
                const lat = start[0] + (end[0] - start[0]) * ratio;
                const lng = start[1] + (end[1] - start[1]) * ratio;
                interpolatedPoints.push([lat, lng]);
            }
        }
        // Add final point
        interpolatedPoints.push(path[path.length - 1]);

        function tick() {
            if (currentStep >= interpolatedPoints.length) {
                marker.setLatLng(path[path.length - 1]);
                marker.bindPopup("<b>Ambulance Arrived!</b>").openPopup();
                MainApp.showNotification("🚨 Emergency Logistics", "Ambulance has arrived at your location.", "success");
                AmbulanceSimulation.updateAlertBanner("Ambulance Arrived", "Help has reached the driver.");
                
                // Set timeline step to Arrived
                const finalStep = document.getElementById('step-arrived');
                if (finalStep) finalStep.classList.add('completed');
                return;
            }
            
            const nextPos = interpolatedPoints[currentStep];
            marker.setLatLng(nextPos);
            
            // Calculate distance to driver
            // Assuming driverLocation is globally available (set in dashboard.js/navigation.js)
            if (typeof calculateDistance === 'function' && typeof driverLocation !== 'undefined') {
                const distKm = calculateDistance(nextPos[0], nextPos[1], driverLocation.lat, driverLocation.lng);
                
                if (distKm <= 0.5 && !alerted500m) {
                    alerted500m = true;
                    MainApp.showNotification("🚑 AMBULANCE NEARBY", "Distance: " + distKm.toFixed(2) + " km", "warning");
                    if (window.VoiceAssistant) window.VoiceAssistant.speak("Your assigned ambulance is approximately 500 meters away.");
                } else if (distKm <= 0.1 && !alerted100m) {
                    alerted100m = true;
                    if (window.VoiceAssistant) window.VoiceAssistant.speak("Your ambulance is very close.");
                }
            }
            
            // Adjust map bounds slightly to keep ambulance in view
            // Calculate remaining ETA dynamically
            const percentComplete = currentStep / interpolatedPoints.length;
            const remainingEta = Math.max(1, Math.ceil(totalEtaMinutes * (1 - percentComplete)));
            
            document.getElementById('amb-eta').innerText = remainingEta + " mins";
            AmbulanceSimulation.updateAlertBanner(`Ambulance Arriving`, `Arriving in ${remainingEta} mins...`);
            
            currentStep++;
            animationFrameId = setTimeout(tick, interval);
        }
        
        tick();
    },

    updateAlertBanner: function(status, message) {
        const banner = document.getElementById('emergency-banner');
        if (banner) {
            banner.style.display = 'block';
            document.getElementById('banner-status').innerText = status;
            document.getElementById('banner-msg').innerText = message;
        }
    }
};
