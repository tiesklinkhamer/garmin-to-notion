import os
import datetime
from garminconnect import Garmin
from notion_client import Client

# Initialize Notion and Garmin clients
try:
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    print("Notion client initialized")
except Exception as e:
    print(f"Error initializing Notion client: {e}")
    exit(1)

try:
    garmin = Garmin(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
    garmin.login()
    print("Garmin login successful")
except Exception as e:
    print(f"Error logging in to Garmin: {e}")
    exit(1)

# Configuration
health_db_id = os.getenv("NOTION_HEALTH_DB_ID")
today = datetime.date.today()
today_iso = today.isoformat()

def sync_health_metrics():
    print(f"Fetching health data for {today_iso}...")
    
    try:
        # get_user_summary fetches the daily "snapshot" (Stress, BB, HRV, etc.)
        summary = garmin.get_user_summary(today_iso)
        
        # Extract specific metrics (with safety checks if data is missing)
        # HRV is often nested under 'hrvStatus' or top level depending on device
        hrv_value = summary.get('hrvStatus', {}).get('lastNightAvg')
        
        # Body Battery is usually found directly in the summary or stress section
        body_battery_max = summary.get('bodyBatteryHighestValue')
        body_battery_min = summary.get('bodyBatteryLowestValue')
        
        # Stress
        stress_avg = summary.get('averageStressLevel')
        
        # Sleep Score (if available in summary, otherwise usually in sleep data)
        sleep_score = summary.get('sleepScore')

        if not any([hrv_value, body_battery_max, stress_avg]):
            print("No health data found for today yet. Sync later in the day.")
            return

        print(f"Data Found -> HRV: {hrv_value}, BB Max: {body_battery_max}, Stress: {stress_avg}")

        # Check if entry already exists in Notion for today
        query = notion.databases.query(
            **{
                "database_id": health_db_id,
                "filter": {
                    "property": "Date",
                    "date": {
                        "equals": today_iso
                    }
                }
            }
        )

        # Prepare Notion Properties
        properties = {
            "Date": {"date": {"start": today_iso}},
            "HRV (ms)": {"number": hrv_value} if hrv_value else None,
            "Body Battery Max": {"number": body_battery_max} if body_battery_max else None,
            "Body Battery Min": {"number": body_battery_min} if body_battery_min else None,
            "Stress Avg": {"number": stress_avg} if stress_avg else None,
            "Sleep Score": {"number": sleep_score} if sleep_score else None
        }
        
        # Remove None values to avoid API errors
        properties = {k: v for k, v in properties.items() if v is not None}

        if query['results']:
            # Update existing entry
            page_id = query['results'][0]['id']
            notion.pages.update(page_id=page_id, properties=properties)
            print("Updated existing health entry in Notion.")
        else:
            # Create new entry
            notion.pages.create(parent={"database_id": health_db_id}, properties=properties)
            print("Created new health entry in Notion.")

    except Exception as e:
        print(f"Error syncing health metrics: {e}")

if __name__ == "__main__":
    sync_health_metrics()
