import os
import datetime
import json
from notion_client import Client
from openai import OpenAI

# --- INITIALIZATION ---
try:
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    # FIX: .strip() removes hidden newlines that cause the Protocol Error
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"Auth Error: {e}")
    exit(1)

# Database IDs
ACTIVITIES_DB_ID = os.getenv("NOTION_DB_ID")
HEALTH_DB_ID = os.getenv("NOTION_HEALTH_DB_ID")
COACH_DB_ID = os.getenv("NOTION_COACH_DB_ID")

def get_last_7_days_data():
    today = datetime.date.today()
    seven_days_ago = (today - datetime.timedelta(days=7)).isoformat()
    
    print(f"Fetching data since {seven_days_ago}...")

    # --- 1. Fetch Training Data ---
    activities_query = notion.databases.query(
        database_id=ACTIVITIES_DB_ID,
        filter={
            "property": "Date",
            "date": {"on_or_after": seven_days_ago}
        }
    )
    
    activity_log = []
    for page in activities_query['results']:
        props = page['properties']
        try:
            # ADJUST THESE KEYS if your Notion column names are different!
            name_key = "Name" if "Name" in props else "Activity Name"
            name = props[name_key]['title'][0]['plain_text']
            
            date = props['Date']['date']['start']
            
            dist_key = "Distance" if "Distance" in props else "Distance (km)"
            dist = props[dist_key]['number']
            
            activity_log.append(f"- {date}: {name} ({dist}km)")
        except Exception as e:
            # Silently skip missing data rows to prevent crashes
            pass

    # --- 2. Fetch Health Data ---
    health_log = []
    if HEALTH_DB_ID:
        health_query = notion.databases.query(
            database_id=HEALTH_DB_ID,
            filter={
                "property": "Date",
                "date": {"on_or_after": seven_days_ago}
            }
        )
        for page in health_query['results']:
            props = page['properties']
            try:
                date = props['Date']['date']['start']
                hrv = props.get('HRV (ms)', {}).get('number', 'N/A')
                bb_max = props.get('Body Battery Max', {}).get('number', 'N/A')
                stress = props.get('Stress Avg', {}).get('number', 'N/A')
                health_log.append(f"- {date}: HRV {hrv}, Body Batt Max {bb_max}, Stress {stress}")
            except:
                pass

    return "\n".join(activity_log), "\n".join(health_log)

def generate_coaching_insight(activity_text, health_text):
    print("Asking the AI Coach...")
    
    if not activity_text and not health_text:
        return None

    prompt = f"""
    You are an elite endurance sports coach. Analyze my last 7 days.
    
    TRAINING LOG:
    {activity_text}
    
    HEALTH/RECOVERY LOG:
    {health_text}
    
    Task:
    1. 'summary': 2 sentences on volume/intensity vs recovery.
    2. 'score': Choose exactly one: 'Good', 'Moderate', or 'Poor'.
    3. 'action': One specific, actionable tip for next week (e.g., "Take Tuesday off," "Increase long run by 2km").
    
    Output purely strictly valid JSON.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return response.choices[0].message.content

def save_report(insight_json):
    if not insight_json:
        print("No data to report.")
        return

    data = json.loads(insight_json)
    today_iso = datetime.date.today().isoformat()
    
    print(f"Saving Report: {data.get('score', 'No Score')}")
    
    notion.pages.create(
        parent={"database_id": COACH_DB_ID},
        properties={
            "Name": {"title": [{"text": {"content": f"Week Analysis: {today_iso}"}}]},
            "Date": {"date": {"start": today_iso}},
            "Summary": {"rich_text": [{"text": {"content": data.get('summary', '')}}]},
            "Recovery Score": {"select": {"name": data.get('score', 'Moderate')}},
            "Action Item": {"rich_text": [{"text": {"content": data.get('action', '')}}]}
        }
    )
    print("Report saved to Notion successfully!")

if __name__ == "__main__":
    act_text, health_text = get_last_7_days_data()
    print(f"Data gathered. {len(act_text)} chars of training data.")
    
    insight = generate_coaching_insight(act_text, health_text)
    save_report(insight)
