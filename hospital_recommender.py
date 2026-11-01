"""
AI Driver Health Guardian — Hospital Recommendation Engine

Ranks available hospitals using a multi-factor scoring model based on:
1. Specialty Match (Cardiology, ICU, Neurology, Pulmonology, Emergency)
2. Haversine Distance & Estimated Travel Time (ETA)
3. Available Emergency Beds & ICU Capacity
4. Hospital Capability & Service Availability
"""

import math
from database import get_db_connection

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance in km between two lat/lng coordinates."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def rank_hospitals_for_emergency(driver_lat: float, driver_lng: float,
                                emergency_type: str, required_specialty: str = "General") -> list:
    """
    Ranks all active hospitals for a given emergency scenario.
    Returns a sorted list of dictionaries with hospital details, match score (0-100), distance, and ETA.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hospitals WHERE availability = 1")
    hospitals = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not hospitals:
        return []

    ranked_results = []

    req_spec_lower = required_specialty.lower()
    req_type_lower = emergency_type.lower()

    for h in hospitals:
        h_lat = h.get('latitude') or 11.2720
        h_lng = h.get('longitude') or 77.5920
        
        dist_km = haversine_distance(driver_lat, driver_lng, h_lat, h_lng)
        eta_min = max(3, int((dist_km / 45.0) * 60))

        # 1. Specialty & Capability Score (max 40 pts)
        spec_score = 15.0
        h_types = [t.strip().lower() for t in (h.get('emergency_types') or '').split(',')]
        
        if req_spec_lower in h_types or any(s in req_type_lower for s in h_types):
            spec_score += 20.0
        if h.get('icu_availability') == 1:
            spec_score += 5.0

        # 2. Proximity Score (max 35 pts)
        # 100% score at 0km, decreasing as distance increases
        prox_score = max(0.0, 35.0 - (dist_km * 1.5))

        # 3. Capacity & Bed Availability Score (max 25 pts)
        avail_beds = h.get('available_beds') or 0
        icu_beds = h.get('icu_beds') or 0
        bed_score = min(15.0, avail_beds * 1.5) + min(10.0, icu_beds * 2.0)

        total_score = round(min(100.0, spec_score + prox_score + bed_score), 1)

        maps_url = (f"https://www.google.com/maps/dir/?api=1"
                    f"&origin={driver_lat},{driver_lng}"
                    f"&destination={h_lat},{h_lng}&travelmode=driving")

        ranked_results.append({
            'id': h['id'],
            'hospital_id_code': h.get('hospital_id_code', f"HOS-{h['id']:06d}"),
            'name': h['name'],
            'phone': h.get('phone', ''),
            'emergency_number': h.get('emergency_number', h.get('phone', '')),
            'address': h.get('address', ''),
            'city': h.get('city', ''),
            'district': h.get('district', ''),
            'state': h.get('state', ''),
            'latitude': h_lat,
            'longitude': h_lng,
            'emergency_types': h.get('emergency_types', 'General, ICU'),
            'icu_availability': h.get('icu_availability', 1),
            'available_beds': avail_beds,
            'icu_beds': icu_beds,
            'distance_km': round(dist_km, 2),
            'eta_minutes': eta_min,
            'score': total_score,
            'maps_url': maps_url
        })

    # Sort descending by score (highest match score first)
    ranked_results.sort(key=lambda x: x['score'], reverse=True)
    return ranked_results

def get_best_hospital_for_emergency(driver_lat: float, driver_lng: float,
                                    emergency_type: str, required_specialty: str = "General") -> dict:
    """Return top ranked hospital or default fallback."""
    ranked = rank_hospitals_for_emergency(driver_lat, driver_lng, emergency_type, required_specialty)
    if ranked:
        return ranked[0]
    return {
        'id': 1,
        'hospital_id_code': 'HOS-000001',
        'name': 'City General Hospital',
        'phone': '108',
        'emergency_number': '108',
        'address': 'Main Road',
        'latitude': driver_lat,
        'longitude': driver_lng,
        'distance_km': 0.0,
        'eta_minutes': 5,
        'score': 100.0,
        'maps_url': ''
    }

if __name__ == '__main__':
    # Smoke test
    res = rank_hospitals_for_emergency(11.2720, 77.5920, "Heart Attack Risk", "Cardiac")
    print(f"Top Recommended Hospital: {res[0]['name']} (Score: {res[0]['score']}, Distance: {res[0]['distance_km']} km, ETA: {res[0]['eta_minutes']} min)")
