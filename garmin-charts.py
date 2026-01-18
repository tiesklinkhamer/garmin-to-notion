import os
import datetime
import json
import urllib.parse
from notion_client import Client

# --- CONFIGURATION ---
try:
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
except Exception as e:
    print(f"Auth Error: {e}")
    exit(1)

ACTIVITIES_DB_ID = os.getenv("NOTION_DB_ID")
COACH_DB_ID = os.getenv("NOTION_COACH_DB_ID")

def get_last_30_days_data():
    """Fetch Date, Distance, and Heart Rate for the last 30 days"""
    today = datetime.date.today()
    thirty_days_ago = (today - datetime.timedelta(days=30)).isoformat()
    
    print(f"Fetching data since {thirty_days_ago}...")

    query = notion.databases.query(
        database_id=ACTIVITIES_DB_ID,
        filter={
            "property": "Date",
            "date": {"on_or_after": thirty_days_ago}
        },
        sorts=[{"property": "Date", "direction": "ascending"}]
    )
    
    dates = []
    distances = []
    heart_rates = []

    for page in query['results']:
        props = page['properties']
        try:
            # EXTRACT DATA (Adjust property names if yours differ)
            date_str = props['Date']['date']['start'] # YYYY-MM-DD
            
            dist_key = "Distance" if "Distance" in props else "Distance (km)"
            dist = props[dist_key]['number']
            
            hr_key = "Avg HR" if "Avg HR" in props else "Average Heart Rate"
            # Some entries might not have HR data (e.g. manual entry), so we use 0 or None
            hr = props.get(hr_key, {}).get('number', 0)

            if dist > 0: # Only plot days with activity
                # Format date to be shorter (e.g., "Jan 18")
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                dates.append(dt.strftime("%b %d"))
                distances.append(dist)
                heart_rates.append(hr if hr else 0)

        except Exception as e:
            continue

    return dates, distances, heart_rates

def generate_quickchart_url(dates, distances, heart_rates):
    """Constructs the QuickChart URL for a dual-axis graph"""
    
    # Chart.js configuration
    chart_config = {
        "type": "bar",
        "data": {
            "labels": dates,
            "datasets": [
                {
                    "type": "line",
                    "label": "Avg HR (bpm)",
                    "borderColor": "#ff6384",
                    "borderWidth": 2,
                    "fill": False,
                    "data": heart_rates,
                    "yAxisID": "y1"
                },
                {
                    "type": "bar",
                    "label": "Distance (km)",
                    "backgroundColor": "rgba(54, 162, 235, 0.5)",
                    "data": distances,
                    "yAxisID": "y"
                }
            ]
        },
        "options": {
            "title": {
                "display": True,
                "text": "Training Load: Volume vs Intensity (Last 30 Days)"
            },
            "scales": {
                "y": {
                    "type": "linear",
                    "display": True,
                    "position": "left",
                    "title": {"display": True, "text": "Distance (km)"}
                },
                "y1": {
                    "type": "linear",
                    "display": True,
                    "position": "right",
                    "grid": {"drawOnChartArea": False},
                    "title": {"display": True, "text": "Heart Rate (bpm)"}
                }
            }
        }
    }

    # Convert to JSON string and URL encode it
    json_str = json.dumps(chart_config)
    encoded_config = urllib.parse.quote(json_str)
    
    # QuickChart base URL
    return f"https://quickchart.io/chart?c={encoded_config}&w=600&h=300"

def append_chart_to_latest_report(chart_url):
    print("Finding latest Coach Report...")
    
    # Find the most recent report
    query = notion.databases.query(
        database_id=COACH_DB_ID,
        sorts=[{"property": "Date", "direction": "descending"}],
        page_size=1
    )
    
    if not query['results']:
        print("No Coach Report found to attach chart to.")
        return

    latest_report_id = query['results'][0]['id']
    report_name = query['results'][0]['properties']['Name']['title'][0]['plain_text']
    print(f"Attaching chart to: {report_name}")

    # Append image block to the page
    notion.blocks.children.append(
        block_id=latest_report_id,
        children=[
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "📊 Monthly Visuals"}}]
                }
            },
            {
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": chart_url
                    }
                }
            }
        ]
    )
    print("Chart attached successfully!")

if __name__ == "__main__":
    d, dist, hr = get_last_30_days_data()
    
    if not d:
        print("No data found to chart.")
    else:
        url = generate_quickchart_url(d, dist, hr)
        # Note: QuickChart URLs can be long. If too long, Notion might reject. 
        # But for 30 days of data, it is usually safe.
        append_chart_to_latest_report(url)
