import math

class MapsService:
    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance in kilometers between two points 
        on the earth (specified in decimal degrees)
        """
        if None in (lat1, lon1, lat2, lon2):
            return float('inf')
            
        # Convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

        # Haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371 # Radius of earth in kilometers
        return c * r

    @staticmethod
    def calculate_eta(distance_km, speed_kmh=40):
        """Estimate time of arrival based on distance and average speed."""
        if distance_km == float('inf'):
            return "Unknown"
        minutes = (distance_km / speed_kmh) * 60
        return f"{int(minutes)} min"
