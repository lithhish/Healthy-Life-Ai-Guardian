import os
import requests

_GEOCODE_SVC_CACHE = {}

class GeocodingService:
    @staticmethod
    def geocode_address(address_dict):
        """
        Expects a dictionary with: line1, line2, area, city, district, state, pincode, country
        """
        address_string = f"{address_dict.get('line1', '')}, {address_dict.get('area', '')}, {address_dict.get('city', '')}, {address_dict.get('state', '')}, {address_dict.get('country', '')}".strip()
        
        if address_string in _GEOCODE_SVC_CACHE:
            return _GEOCODE_SVC_CACHE[address_string]

        # Try Google Maps API first
        api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
        if api_key and api_key != 'your_google_maps_api_key_here':
            res = GeocodingService._geocode_google(address_string, api_key)
            if res.get('status') == 'success':
                _GEOCODE_SVC_CACHE[address_string] = res
                return res

        # Fallback to OpenStreetMap Nominatim
        res = GeocodingService._geocode_nominatim(address_string)
        if res.get('status') == 'success':
            _GEOCODE_SVC_CACHE[address_string] = res
        return res

    @staticmethod
    def _geocode_google(address_string, api_key):
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address_string}&key={api_key}"
            response = requests.get(url).json()
            if response['status'] == 'OK':
                loc = response['results'][0]['geometry']['location']
                return {"status": "success", "lat": loc['lat'], "lng": loc['lng'], "source": "Google"}
            return {"status": "error", "message": "Geocoding failed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _geocode_nominatim(address_string):
        try:
            headers = {'User-Agent': 'AIGuardian/1.0'}
            url = f"https://nominatim.openstreetmap.org/search?q={address_string}&format=json&limit=1"
            response = requests.get(url, headers=headers).json()
            if len(response) > 0:
                return {"status": "success", "lat": float(response[0]['lat']), "lng": float(response[0]['lon']), "source": "OSM Nominatim"}
            return {"status": "error", "message": "Location not found via Nominatim"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
