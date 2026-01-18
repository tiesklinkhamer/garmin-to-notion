import os
from garminconnect import Garmin
from notion_client import Client

# Initialize Clients
garmin = Garmin(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
garmin.login()
notion = Client(auth=os.getenv("NOTION_TOKEN"))

# Configuration
ACTIVITIES_DB_ID = os.getenv("NOTION_DB_ID") # Your main activities DB
GEAR_DB_ID = os.getenv("NOTION_GEAR_DB_ID") # The new Shoe DB

def get_notion_gear_map():
    """Creates a dictionary mapping Garmin Gear UUIDs to Notion Page IDs"""
    mapping = {}
    query = notion.databases.query(database_id=GEAR_DB_ID)
    for row in query['results']:
        # Assumes property name is 'Garmin Gear ID'
        gear_uuid_list = row['properties']['Garmin Gear ID']['rich_text']
        if gear_uuid_list:
            gear_uuid = gear_uuid_list[0]['plain_text']
            mapping[gear_uuid] = row['id']
    return mapping

def sync_gear():
    print("Fetching recent activities...")
    activities = garmin.get_activities(0, 5) # Check last 5 runs
    gear_map = get_notion_gear_map()

    for activity in activities:
        activity_name = activity['activityName']
        gear_id = activity.get('deviceId') # Sometimes gearID is here, or in 'gear' key
        
        # Garmin API variation: sometimes gear is nested
        if not gear_id and 'gear' in activity:
             gear_id = activity['gear']['gearPk']
        
        if not gear_id:
            print(f"No gear found for: {activity_name}")
            continue

        if gear_id in gear_map:
            print(f"Linking '{activity_name}' to Gear ID {gear_id}...")
            
            # Find the Notion Activity Page for this run
            # (You'll need logic to find the specific run page ID here, 
            # usually by matching the Activity Date/Name)
            
            # This part assumes you have a function to find the Notion Page ID 
            # for the specific activity.
            pass
        else:
            print(f"Gear ID {gear_id} not found in Notion. Add it to your Gear DB!")

if __name__ == "__main__":
    sync_gear()
