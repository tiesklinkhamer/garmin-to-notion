import os
import datetime
from garminconnect import Garmin
from notion_client import Client

# Initialize Client
try:
    garmin = Garmin(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
    garmin.login()
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
except Exception as e:
    print(f"Auth Error: {e}")
    exit(1)

DATABASE_ID = os.getenv("NOTION_DB_ID")

def activity_exists(activity_id):
    """Checks if activity already exists in Notion to avoid duplicates"""
    query = notion.databases.query(
        database_id=DATABASE_ID,
        filter={
            "property": "Activity ID", # Ensure you have this Text column!
            "rich_text": {"equals": str(activity_id)}
        }
    )
    return len(query['results']) > 0

def sync_activities():
    print("Checking for new activities...")
    # Fetch last 10 activities
    activities = garmin.get_activities(0, 10)

    for activity in activities:
        activity_id = activity['activityId']
        name = activity['activityName']
        start_time = activity['startTimeLocal'] # '2023-01-01 10:00:00'
        
        # Check duplication
        if activity_exists(activity_id):
            print(f"Skipping existing activity: {name}")
            continue

        print(f"Syncing new activity: {name}")

        # --- DATA EXTRACTION ---
        # Metric conversions (Garmin uses meters and seconds)
        distance_km = round(activity['distance'] / 1000, 2)
        duration_sec = activity['duration']
        
        # Heart Rate (The new part!)
        avg_hr = activity.get('averageHR') # Returns None if missing
        
        # Sport Type mapping (Simple version)
        sport_type = activity['activityType']['typeKey'] # e.g., 'running', 'cycling'

        # --- SEND TO NOTION ---
    
        properties = {
            # Change "Name" to "Activity Name" (or whatever yours is called)
            "Activity Name": {"title": [{"text": {"content": name}}]},
            
            "Date": {"date": {"start": start_time}},
            "Distance (km)": {"number": distance_km},
            
            # Change "Time" to "Duration"
            "Duration": {"number": duration_sec},
            
            "Activity ID": {"rich_text": [{"text": {"content": str(activity_id)}}]},
            
            # Change "Type" to "Sport"
            "Sport": {"select": {"name": sport_type}},
            
            "Avg HR": {"number": avg_hr} if avg_hr else None
        }

        # Remove None values to be safe
        properties = {k: v for k, v in properties.items() if v is not None}

        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )
        print("Done!")

if __name__ == "__main__":
    sync_activities()
