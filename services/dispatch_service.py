from extensions import db
from models import Hospital, Ambulance, EmergencyEvent
from services.maps_service import MapsService
from flask_socketio import emit

class DispatchService:
    @staticmethod
    def dispatch_emergency(emergency_id, lat, lon):
        emergency = db.session.get(EmergencyEvent, emergency_id)
        if not emergency:
            return {"status": "error", "message": "Emergency not found"}
            
        # 1. Find nearest Hospital
        hospitals = Hospital.query.filter_by(has_er=True).all()
        best_hospital = None
        min_hosp_dist = float('inf')
        
        for h in hospitals:
            if h.latitude and h.longitude:
                dist = MapsService.haversine_distance(lat, lon, h.latitude, h.longitude)
                if dist < min_hosp_dist:
                    min_hosp_dist = dist
                    best_hospital = h
                    
        # 2. Find nearest Ambulance
        ambulances = Ambulance.query.filter_by(status='AVAILABLE').all()
        best_amb = None
        min_amb_dist = float('inf')
        
        for a in ambulances:
            if a.latitude and a.longitude:
                dist = MapsService.haversine_distance(lat, lon, a.latitude, a.longitude)
                if dist < min_amb_dist:
                    min_amb_dist = dist
                    best_amb = a
                    
        if not best_hospital or not best_amb:
            return {"status": "error", "message": "No resources available"}
            
        # 3. Update records
        emergency.assigned_hospital_id = best_hospital.id
        emergency.assigned_ambulance_id = best_amb.id
        emergency.status = 'DISPATCHED'
        
        best_amb.status = 'DISPATCHED'
        db.session.commit()
        
        eta = MapsService.calculate_eta(min_amb_dist)
        
        # Broadcast via SocketIO (Implementation assumes we have access to socketio context)
        # emit('ambulance_dispatched', {'ambulance_id': best_amb.id, 'eta': eta}, namespace='/')
        
        return {
            "status": "success",
            "hospital": best_hospital.name,
            "hospital_distance": f"{min_hosp_dist:.1f} km",
            "ambulance": best_amb.vehicle_number,
            "ambulance_distance": f"{min_amb_dist:.1f} km",
            "eta": eta
        }
