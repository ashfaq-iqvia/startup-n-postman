"""
Create Postman Collection with Pre-request Script

This script creates a new Postman collection with the pre-request script already configured.

Usage:
    python setup-postman-collection.py                     # Interactive mode
    python setup-postman-collection.py "Collection Name"   # Create with name

Requirements:
    pip install requests
"""

import sys
import os
import json
import requests
from datetime import datetime

def get_api_key():
    """Get API key from environment or config file."""
    # Try environment variable first
    key = os.environ.get('POSTMAN_API_KEY', '')
    if key:
        return key

    # Fallback: read from config file
    config_file = os.path.join(os.path.dirname(__file__), 'pm-api-key.txt')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            key = f.readline().strip()
            if key:
                return key

    return ''

POSTMAN_API_KEY = get_api_key()
BASE_URL = "https://api.getpostman.com"

# Your pre-request script
PRE_REQUEST_SCRIPT = '''
let prefix_predev = "https://pl-kpipredev-dev01-kpi01-euf.dev.kpi.oa."
let prefix_dev = "https://pl-kpidev-dev01-kpi01-euf.dev.kpi.oa."
let config_service = "iqvia.com/config"
let dashboard_service = "iqvia.com/dashboard-service"
let migration_service = "iqvia.com/migration-service"
let mapshapegen_service = "iqvia.com/mapshapegen-service"
let wte_service = "iqvia.com/widget-template-editor-service"
let prefix = "localhost";

// Sync environment auth to global
let envAuth = pm.environment.get("auth").trim();
if (envAuth) {
    pm.globals.set("auth", envAuth);
}

if(pm.request.url.toString().includes(prefix_predev)) {
    prefix = prefix_predev
}
else if(pm.request.url.toString().includes(prefix_dev)) {
    prefix = prefix_dev
}

let auth_obj = pm.request.headers.find(x => x.key.toLowerCase() === "authorization")

if(pm.request.url.toString().includes(config_service)) {
    var temp = pm.request.url.toString().replace(prefix + config_service, pm.globals.get("localConfigKPI"))
    pm.request.url = new URL(temp);
    auth_obj.value = pm.globals.get("auth")
}
else if(pm.request.url.toString().includes(dashboard_service)) {
    var temp = pm.request.url.toString().replace(prefix + dashboard_service, pm.globals.get("localDashboardKPI"))
    pm.request.url = new URL(temp);
}
else if(pm.request.url.toString().includes(migration_service)) {
    var temp = pm.request.url.toString().replace(prefix + migration_service, pm.globals.get("localMigrationKPI"))
    pm.request.url = new URL(temp);
}
else if(pm.request.url.toString().includes(mapshapegen_service)) {
    var temp = pm.request.url.toString().replace(prefix + mapshapegen_service, pm.globals.get("localMapKPI"))
    pm.request.url = new URL(temp);
}
else if(pm.request.url.toString().includes(wte_service)) {
    var temp = pm.request.url.toString().replace(prefix + wte_service, pm.globals.get("localWteKPI"))
    pm.request.url = new URL(temp);
}
auth_obj.value = pm.globals.get("auth").trim()
'''.strip()


def get_headers():
    return {
        "X-API-Key": POSTMAN_API_KEY,
        "Content-Type": "application/json"
    }


def create_collection(name):
    """Create a new collection with pre-request script."""
    url = f"{BASE_URL}/collections"

    payload = {
        "collection": {
            "info": {
                "name": name,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "event": [
                {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": PRE_REQUEST_SCRIPT.split('\n')
                    }
                }
            ]
        }
    }

    response = requests.post(url, headers=get_headers(), json=payload)

    if response.status_code == 200:
        data = response.json()
        return data.get('collection', {})
    else:
        print(f"❌ Failed to create collection: {response.status_code}")
        print(response.text)
        return None


def main():
    print(f"\n{'='*50}")
    print("  📮 Create Postman Collection")
    print(f"{'='*50}")

    if not POSTMAN_API_KEY:
        print("\n❌ POSTMAN_API_KEY not set!")
        print("\nSet it with:")
        print('  [System.Environment]::SetEnvironmentVariable("POSTMAN_API_KEY", "YOUR_KEY", "User")')
        return

    # Get collection name
    if len(sys.argv) > 1:
        name = sys.argv[1]
    else:
        print("\n  Enter collection name:")
        name = input("  > ").strip()

    if not name:
        print("\n  ❌ Name cannot be empty!")
        return

    # Add inverted date prefix for sorting (newer dates sort first)
    # Format: YYMMDD inverted (99-yy, 13-mm, 32-dd)
    now = datetime.now()
    inv_year = 99 - (now.year % 100)
    inv_month = 13 - now.month
    inv_day = 32 - now.day
    date_prefix = f"{inv_year:02d}{inv_month:02d}{inv_day:02d}"
    full_name = f"{date_prefix} {name}"

    print(f"\n  Creating collection: {full_name}")
    print(f"  Adding pre-request script...")

    result = create_collection(full_name)

    if result:
        print(f"\n  ✓ Collection '{full_name}' created successfully!")
        print(f"\n  Collection ID: {result.get('id', 'N/A')}")
        print(f"\n  The pre-request script is already configured.")
        print(f"  Open Postman and start adding requests to your collection!")
    else:
        print(f"\n  ❌ Failed to create collection")

    print(f"\n{'='*50}")


if __name__ == "__main__":
    main()
