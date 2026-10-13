"""
List and Rename Postman Collections with Creation Date Prefix

Shows all collections and can rename them with YYYY-MM-DD prefix based on creation date.

Usage:
    python list-postman-collections.py              # List collections
    python list-postman-collections.py --rename     # Rename all with date prefix

Requirements:
    pip install requests
"""

import sys
import os
import re
import requests
from datetime import datetime

def get_api_key():
    """Get API key from environment or config file."""
    key = os.environ.get('POSTMAN_API_KEY', '')
    if key:
        return key

    config_file = os.path.join(os.path.dirname(__file__), 'pm-api-key.txt')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            key = f.readline().strip()
            if key:
                return key
    return ''

POSTMAN_API_KEY = get_api_key()
BASE_URL = "https://api.getpostman.com"


def get_headers():
    return {
        "X-API-Key": POSTMAN_API_KEY,
        "Content-Type": "application/json"
    }


def list_collections():
    """List all collections with creation dates."""
    url = f"{BASE_URL}/collections"
    response = requests.get(url, headers=get_headers())

    if response.status_code == 200:
        collections = response.json().get('collections', [])

        # Sort by createdAt (most recent first)
        collections.sort(
            key=lambda x: x.get('createdAt', x.get('updatedAt', '')),
            reverse=True
        )

        return collections
    return []


def get_collection(collection_id):
    """Get full collection details."""
    url = f"{BASE_URL}/collections/{collection_id}"
    response = requests.get(url, headers=get_headers())

    if response.status_code == 200:
        return response.json().get('collection', {})
    return None


def update_collection(collection_id, collection_data):
    """Update a collection."""
    url = f"{BASE_URL}/collections/{collection_id}"
    payload = {"collection": collection_data}

    response = requests.put(url, headers=get_headers(), json=payload)
    return response.status_code == 200


def format_date(date_str):
    """Format ISO date to readable format."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return date_str[:16] if date_str else "N/A"


def get_date_prefix(date_str):
    """Create inverted date prefix so newer dates sort first alphabetically.

    Format: YYMMDD inverted (99-yy, 13-mm, 32-dd)
    So 2024-12-10 becomes 750122 (newer dates = smaller numbers = sort first)
    """
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        inv_year = 99 - (dt.year % 100)
        inv_month = 13 - dt.month
        inv_day = 32 - dt.day
        return f"{inv_year:02d}{inv_month:02d}{inv_day:02d}"
    except:
        return None


def has_date_prefix(name):
    """Check if name already has the new inverted date prefix (6 digits)."""
    return bool(re.match(r'^\d{6}\s', name))


def has_old_date_prefix(name):
    """Check if name has old YYYY-MM-DD format prefix."""
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}\s', name))


def convert_old_date_prefix(name):
    """Convert old YYYY-MM-DD prefix to new YYMMDD inverted format."""
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})\s(.+)$', name)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        rest = match.group(4)

        # Invert the date
        inv_year = 99 - (year % 100)
        inv_month = 13 - month
        inv_day = 32 - day
        new_prefix = f"{inv_year:02d}{inv_month:02d}{inv_day:02d}"

        return f"{new_prefix} {rest}"
    return name


def rename_collection(collection_id, new_name):
    """Rename a collection."""
    # Get full collection data
    collection_data = get_collection(collection_id)
    if not collection_data:
        return False

    # Update name
    collection_data['info']['name'] = new_name

    # Update collection
    return update_collection(collection_id, collection_data)


def show_collections():
    """Display collections sorted by creation date."""
    print("\n  Fetching collections...")
    collections = list_collections()

    if not collections:
        print("  No collections found.")
        return

    print(f"\n  Collections (most recent first):")
    print(f"  {'-'*55}")

    for i, col in enumerate(collections, 1):
        name = col.get('name', 'Unknown')
        created = format_date(col.get('createdAt', ''))

        if has_date_prefix(name):
            status = "✓"  # New format
        elif has_old_date_prefix(name):
            status = "⟳"  # Old format, needs conversion
        else:
            status = "✗"  # No prefix

        print(f"\n  {i:2}. [{status}] {name}")
        print(f"      Created: {created}")

    print(f"\n  {'-'*55}")
    print(f"  [✓] = New format  |  [⟳] = Old format  |  [✗] = No prefix")
    print(f"  Total: {len(collections)} collections")


def rename_all_collections():
    """Rename all collections with their creation date prefix."""
    print("\n  Fetching collections...")
    collections = list_collections()

    if not collections:
        print("  No collections found.")
        return

    # Filter collections that need renaming
    to_rename = []
    for col in collections:
        name = col.get('name', '')

        # Skip if already has new format
        if has_date_prefix(name):
            continue

        # Check if has old YYYY-MM-DD format - convert it
        if has_old_date_prefix(name):
            new_name = convert_old_date_prefix(name)
            to_rename.append({
                'id': col.get('id'),
                'old_name': name,
                'new_name': new_name,
                'created': col.get('createdAt', '')
            })
        else:
            # No prefix - add new one based on creation date
            date_prefix = get_date_prefix(col.get('createdAt', ''))
            if date_prefix:
                to_rename.append({
                    'id': col.get('id'),
                    'old_name': name,
                    'new_name': f"{date_prefix} {name}",
                    'created': col.get('createdAt', '')
                })

    if not to_rename:
        print("\n  ✓ All collections already have date prefixes!")
        return

    print(f"\n  Found {len(to_rename)} collections to rename:")
    print(f"  {'-'*60}")

    for item in to_rename[:10]:  # Show first 10
        print(f"\n    {item['old_name']}")
        print(f"    → {item['new_name']}")

    if len(to_rename) > 10:
        print(f"\n    ... and {len(to_rename) - 10} more")

    print(f"\n  {'-'*60}")

    confirm = input("\n  Proceed with renaming? (y/n): ").strip().lower()

    if confirm != 'y':
        print("\n  Cancelled.")
        return

    print("\n  Renaming collections...")

    success = 0
    failed = 0
    total = len(to_rename)

    for i, item in enumerate(to_rename, 1):
        remaining = total - i
        if rename_collection(item['id'], item['new_name']):
            print(f"    ({i}/{total}) - {remaining} remaining ✓ {item['new_name']}")
            success += 1
        else:
            print(f"    ({i}/{total}) - {remaining} remaining ✗ Failed: {item['old_name']}")
            failed += 1

    print(f"\n  {'-'*60}")
    print(f"  Done! Renamed: {success}  |  Failed: {failed}")


def main():
    print(f"\n{'='*60}")
    print("  📋 Postman Collections")
    print(f"{'='*60}")

    if not POSTMAN_API_KEY:
        print("\n❌ POSTMAN_API_KEY not set!")
        print("\nSet it with:")
        print('  [System.Environment]::SetEnvironmentVariable("POSTMAN_API_KEY", "YOUR_KEY", "User")')
        return

    # Check for --rename flag
    if len(sys.argv) > 1 and sys.argv[1] == '--rename':
        rename_all_collections()
        print(f"\n{'='*60}")
        return

    # Default: show list
    show_collections()
    print(f"\n  To rename collections with date prefix, run:")
    print(f"    python list-postman-collections.py --rename")
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
