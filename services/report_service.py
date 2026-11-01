import json
from datetime import datetime
import csv
import os

class ReportService:
    @staticmethod
    def generate_json_report(emergency_data):
        report = {
            "report_id": f"REP-{int(datetime.utcnow().timestamp())}",
            "generated_at": datetime.utcnow().isoformat(),
            "patient_info": {
                "name": emergency_data.get('driver_name', 'Unknown'),
                "blood_group": emergency_data.get('blood_group', 'Unknown')
            },
            "emergency_details": {
                "type": emergency_data.get('emergency_type'),
                "risk_level": emergency_data.get('risk_level')
            },
            "vitals_at_time": emergency_data.get('vitals', {}),
            "logistics": {
                "hospital": emergency_data.get('hospital_name'),
                "ambulance": emergency_data.get('ambulance_id')
            }
        }
        
        # Save to file
        os.makedirs('reports', exist_ok=True)
        filename = f"reports/emergency_report_{report['report_id']}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=4)
            
        return filename
