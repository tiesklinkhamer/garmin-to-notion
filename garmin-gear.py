import os
import datetime
from garminconnect import Garmin
from notion_client import Client

# --- SETUP ---
try:
    garmin = Garmin(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
    garmin.login()
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
except Exception as e:
    print(f"Auth Error: {e}")
    exit(1)

ACTIVITIES_DB_ID = os.getenv("NOTION_DB_ID")
GEAR_DB_ID = os.getenv("NOTION_GEAR_DB_ID")

# --- HELPERS ---

def get_gear_mapping():
    """
    Returns a dict: {'Garmin_Gear_ID_String': 'Notion_Page_ID'}
    Scans the Gear Garage DB to know which Notion page corresponds to which Garmin gear.
    """
    mapping = {}
    has_more = True
    next_cursor = None

    while has_more:
        resp = notion.databases.query(
            database_id=GEAR_DB_ID,
            start_cursor=next_cursor
        )
        for page in resp['results']:
            # Assumes you have a Text property named 'Garmin ID' in your Gear DB
            try:
                g_id_list = page['properties']['Garmin ID']['rich_text']
                if g_id_list:
                    g_id = g_id_list[0]['plain_text']
                    mapping[g_id] = page['id']
            except KeyError:
                continue # Skip if property missing
        
        has_more = resp['has_more']
        next_cursor = resp['next_cursor']
    
    return mapping

def find_activity_page(activity_date, activity_name):
    """
    Finds the Notion Page ID for a specific run in the Activities DB.
    Matches primarily on Date to avoid duplicates.
    """
    # Format date to match Notion (YYYY-MM-DD) if needed
    # Garmin API returns timestamps, usually we need just the date part for matching
    # Adjust logic here if your Notion 'Date' includes time.
    
    query = notion.databases.query(
        database_id=ACTIVITIES_DB_ID,
        filter={
            "and": [
                {
                    "property": "Date",
                    "date": {"equals": activity_date[:10]} # Match YYYY-MM-DD
                },
                {
                    "property": "Name", # or whatever your Title property is called
                    "title": {"contains": activity_name}
                }
            ]
        }
    )
    
    if query['results']:
        return query['results'][0]['id']
    return None

# --- MAIN SYNC ---

def sync_gear():
    print("Mapping Notion Gear...")
    gear_map = get_gear_mapping()
    print(f"Found {len(gear_map)} shoes/bikes in Notion.")

    # Get last 10 activities
    activities = garmin.get_activities(0, 10)

    for activity in activities:
        name = activity['activityName']
        start_time = activity['startTimeLocal'] # '2023-10-27 18:00:00'
        
        # safely get gear ID
        # Note: Garmin API structure varies by activity type. 
        # Sometimes it is just 'deviceId', sometimes deeper.
        # This approach tries standard locations.
        gear_id = str(activity.get('deviceId')) 
        
        # If deviceId is the watch ID (common confusion), we need the 'gear' dict
        # Check if 'gear' key exists (usually for shoes)
        if 'gear' in activity:
             gear_id = str(activity['gear']['gearPk'])

        if gear_id in gear_map:
            notion_gear_id = gear_map[gear_id]
            
            # Find the activity in Notion
            activity_page_id = find_activity_page(start_time, name)
            
            if activity_page_id:
                print(f"Linking '{name}' to Gear ID {gear_id}...")
                
                # Update the Relation Property in the Activity Row
                # Assumes the relation property in Activities DB is named "Gear"
                notion.pages.update(
                    page_id=activity_page_id,
                    properties={
                        "Gear": {
                            "relation": [{"id": notion_gear_id}]
                        }
                    }
                )
            else:
                print(f"Skipping: Could not find activity '{name}' in Notion.")
        else:
            # Helpful for setup: Prints IDs of gear you haven't added to Notion yet
            if gear_id and gear_id != "None":
                print(f"Unmapped Gear found! ID: {gear_id} (Name: {name})")

if __name__ == "__main__":
    sync_gear()
