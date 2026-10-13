"""
Paste to Postman - Auth Token or cURL Request

Options:
    1. Paste auth token to environment variable
    2. Paste cURL command as a new request to most recent collection

Usage:
    python paste-to-postman.py

Requirements:
    pip install requests pyperclip winrt-Windows.ApplicationModel.DataTransfer
"""

import sys
import os
import json
import re
import shlex
import asyncio
import time

try:
    import requests
    import pyperclip
except ImportError:
    print("Missing dependencies. Run: pip install requests pyperclip")
    sys.exit(1)

# Try to import Windows clipboard history API
CLIPBOARD_HISTORY_AVAILABLE = False
try:
    from winrt.windows.applicationmodel.datatransfer import Clipboard, ClipboardHistoryItemsResultStatus
    CLIPBOARD_HISTORY_AVAILABLE = True
except ImportError:
    pass

# ============================================
# CONFIGURATION
# ============================================
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
GLOBAL_VAR_NAME = 'auth'
BASE_URL = "https://api.getpostman.com"

# Global variable to store selected clipboard content
SELECTED_CLIPBOARD_CONTENT = None
# ============================================


# ============================================
# CLIPBOARD HISTORY
# ============================================
async def get_clipboard_history_async(max_items=5):
    """Get clipboard history items (Windows 10/11)."""
    items = []

    if not CLIPBOARD_HISTORY_AVAILABLE:
        return items

    try:
        # Check if clipboard history is enabled
        if not Clipboard.is_history_enabled():
            return items

        result = Clipboard.get_history_items_async()
        history_result = await result

        if history_result.status == ClipboardHistoryItemsResultStatus.SUCCESS:
            for item in history_result.items:
                if len(items) >= max_items:
                    break
                try:
                    data_package = item.content
                    available_formats = data_package.available_formats

                    # Check for text content
                    if data_package.contains("Text"):
                        text_result = data_package.get_text_async()
                        text = await text_result
                        if text:
                            items.append(text)
                except Exception as inner_e:
                    pass
    except Exception as e:
        pass

    return items


def get_clipboard_history(max_items=5):
    """Synchronous wrapper for clipboard history."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        items = loop.run_until_complete(get_clipboard_history_async(max_items))
        loop.close()
        return items
    except:
        return []


def select_from_clipboard_history():
    """Let user select from clipboard history or current clipboard."""
    global SELECTED_CLIPBOARD_CONTENT

    print(f"\n  Loading clipboard history...")

    # Try to get clipboard history
    history_items = get_clipboard_history(5)

    # Fallback to current clipboard if no history
    if not history_items:
        current = pyperclip.paste()
        if current:
            history_items = [current]
            print(f"  (Clipboard history not available)")
            print(f"  Tip: Press Win+V to enable Windows Clipboard History")

    if not history_items:
        print(f"\n❌ Clipboard is empty!")
        return False

    # Show clipboard items
    print(f"\n  Recent clipboard items:")
    print(f"  {'-'*50}")

    for i, item in enumerate(history_items, 1):
        # Truncate for display
        preview = item[:80].replace('\n', ' ').replace('\r', '')
        if len(item) > 80:
            preview += "..."

        # Detect type and color
        item_type = "?"
        color = "\033[97m"  # white
        if item.lower().strip().startswith('curl '):
            item_type = "cURL"
            color = "\033[92m"  # green
        elif item.startswith('Bearer ') or re.match(r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$', item.strip()):
            item_type = "Token"
            color = "\033[93m"  # light yellow

        print(f"    {i}. [{color}{item_type:5}\033[0m] {preview}")

    print(f"  {'-'*50}")

    # Let user select
    selection = input(f"\n  Select item (1-{len(history_items)}) [1]: ").strip() or "1"

    try:
        idx = int(selection) - 1
        if 0 <= idx < len(history_items):
            SELECTED_CLIPBOARD_CONTENT = history_items[idx]
            print(f"\n  ✓ Selected item {idx + 1}")
            return True
    except ValueError:
        pass

    print(f"\n❌ Invalid selection")
    return False


def get_selected_content():
    """Get the selected clipboard content."""
    global SELECTED_CLIPBOARD_CONTENT
    if SELECTED_CLIPBOARD_CONTENT is not None:
        return SELECTED_CLIPBOARD_CONTENT
    return pyperclip.paste()
# ============================================


def get_headers():
    return {
        "X-API-Key": POSTMAN_API_KEY,
        "Content-Type": "application/json"
    }


# ============================================
# AUTH TOKEN FUNCTIONS
# ============================================
def _postman_ok(response, action):
    """Return True on HTTP 200, otherwise print the API error."""
    if response.status_code == 200:
        return True
    print(f"❌ {action}: {response.status_code}")
    try:
        print(f"  {response.json()}")
    except Exception:
        text = (response.text or "").strip()
        if text:
            print(f"  {text[:500]}")
    return False


def _variable(var_name, var_value, existing=None):
    """Build an environment variable. Value is the cloud initial value."""
    item = {
        'key': var_name,
        'value': var_value,
        'enabled': True,
        'type': 'default',
    }
    if existing and existing.get('description'):
        item['description'] = existing['description']
    return item


def _replace_environment(env_id, env_name, values):
    """Replace an environment's full variable list."""
    url = f"{BASE_URL}/environments/{env_id}"
    payload = {
        'environment': {
            'name': env_name,
            'values': values
        }
    }
    response = requests.put(url, headers=get_headers(), json=payload)
    return _postman_ok(response, "Failed to update environment")


def create_or_update_environment(api_key, env_name, var_name, var_value):
    """Create or update an environment with the variable."""
    headers = get_headers()

    # List environments
    url = f"{BASE_URL}/environments"
    response = requests.get(url, headers=headers)

    if not _postman_ok(response, "Failed to list environments"):
        return False

    environments = response.json().get('environments', [])

    # Find our environment. Prefer uid; the single-environment routes accept it.
    env_id = None
    for env in environments:
        if env.get('name') == env_name:
            env_id = env.get('uid') or env.get('id')
            break

    if env_id:
        # Update existing environment
        url = f"{BASE_URL}/environments/{env_id}"
        response = requests.get(url, headers=headers)

        if not _postman_ok(response, "Failed to read environment"):
            return False

        env_data = response.json().get('environment', {})
        values = env_data.get('values', [])
        existing = next((v for v in values if v.get('key') == var_name), None)
        kept = [v for v in values if v.get('key') != var_name]
        updated = _variable(var_name, var_value, existing)

        # The API only writes the shared initial value. The desktop app sends
        # requests with the local current value, and a plain edit leaves that
        # current value in place. Removing the key and adding it back makes
        # the app copy the new initial value into the current value on sync.
        if existing is not None:
            if not _replace_environment(env_id, env_name, kept):
                return False
            time.sleep(0.5)

        return _replace_environment(env_id, env_name, kept + [updated])
    else:
        # Create new environment
        url = f"{BASE_URL}/environments"
        payload = {
            'environment': {
                'name': env_name,
                'values': [_variable(var_name, var_value)]
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        return _postman_ok(response, "Failed to create environment")


def paste_auth_token():
    """Paste auth token from clipboard to Postman environment."""
    token = get_selected_content()

    if not token:
        print("\n❌ No token found in clipboard!")
        return

    # Strip whitespace and newlines
    token = token.strip()

    print(f"\n  Token: {token[:30]}...{token[-30:]}")

    env_name = "Auth Token"
    print(f"\n  Updating Postman environment '{env_name}'...")

    if create_or_update_environment(POSTMAN_API_KEY, env_name, GLOBAL_VAR_NAME, token):
        print(f"\n  ✓ Environment '{env_name}' updated!")
        print(f"  ✓ Variable '{GLOBAL_VAR_NAME}' is set!")
    else:
        print(f"\n  ❌ Failed to update Postman")


# ============================================
# CURL TO REQUEST FUNCTIONS
# ============================================
def parse_curl(curl_command):
    """Parse a cURL command into request components."""
    # Clean up the curl command - handle line continuations
    curl_command = curl_command.replace('\\\n', ' ').replace('\\\r\n', ' ')
    curl_command = ' '.join(curl_command.split())

    # Default values
    method = 'GET'
    url = ''
    headers = {}
    body = ''

    try:
        # Use shlex to properly parse the command
        parts = shlex.split(curl_command)
    except Exception as e:
        print(f"  Warning: shlex parse failed ({e}), using simple split")
        parts = curl_command.split()

    i = 0
    while i < len(parts):
        part = parts[i]

        if part.lower() == 'curl':
            i += 1
            continue
        elif part == '-X' and i + 1 < len(parts):
            method = parts[i + 1].upper()
            i += 2
        elif part in ('-H', '--header') and i + 1 < len(parts):
            header = parts[i + 1]
            if ':' in header:
                key, value = header.split(':', 1)
                headers[key.strip()] = value.strip()
            i += 2
        elif part in ('-d', '--data', '--data-raw') and i + 1 < len(parts):
            body = parts[i + 1]
            if not method or method == 'GET':
                method = 'POST'  # Default to POST when body is present
            i += 2
        elif part in ('-b', '--cookie') and i + 1 < len(parts):
            # Skip cookies - Postman handles them differently
            i += 2
        elif part.startswith('http'):
            url = part.strip("'\"")
            i += 1
        else:
            # Check if it's a URL
            if not url and (part.startswith("'http") or part.startswith('"http')):
                url = part.strip("'\"")
            i += 1

    return {
        'method': method,
        'url': url,
        'headers': headers,
        'body': body
    }


def extract_request_name(url, method):
    """Extract a suitable name from URL and method."""
    try:
        # Parse URL path
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]

        # Get last meaningful path parts
        name_parts = []
        for part in path_parts[-3:]:
            # Skip UUIDs and pure numbers
            if re.match(r'^[a-fA-F0-9-]{36}$', part):
                continue
            if part.isdigit():
                continue
            name_parts.append(part)

        if name_parts:
            name = ' / '.join(name_parts)
        else:
            name = path_parts[-1] if path_parts else 'request'

        return f"{method} {name}"
    except:
        return f"{method} request"


def infer_kpi_env_folder(url):
    """Map KPI-style host to a collection folder name: predev or dev."""
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower()
    if ':' in host:
        host = host.split(':')[0]
    # Order matters: kpipredev must be checked before kpidev substring rules
    if 'kpipredev' in host:
        return 'predev'
    if 'kpidev' in host:
        return 'dev'
    return None


def is_folder_node(node):
    """True if this collection item is a folder (not a request)."""
    return (
        isinstance(node, dict)
        and 'request' not in node
        and isinstance(node.get('item'), list)
    )


def find_or_create_folder(collection_data, folder_name):
    """Return folder item dict with an 'item' list, creating it at the top if missing."""
    items = collection_data.setdefault('item', [])
    target_lower = folder_name.lower()
    for node in items:
        if is_folder_node(node) and node.get('name', '').lower() == target_lower:
            return node
    folder = {'name': folder_name, 'item': []}
    items.insert(0, folder)
    print(f"  Created folder '{folder_name}'")
    return folder


def get_all_collections():
    """Get all collections sorted by creation date (most recent first)."""
    url = f"{BASE_URL}/collections"
    response = requests.get(url, headers=get_headers())

    if response.status_code != 200:
        return []

    collections = response.json().get('collections', [])

    # Sort by createdAt (most recent first)
    collections.sort(
        key=lambda x: x.get('createdAt', x.get('updatedAt', '')),
        reverse=True
    )

    # Use uid instead of id for API calls
    for col in collections:
        col['id'] = col.get('uid', col.get('id'))

    return collections


def get_most_recent_collection():
    """Get the most recently created collection."""
    collections = get_all_collections()
    return collections[0] if collections else None


def find_collection_by_name(substring):
    """Find collections matching a substring (case-insensitive)."""
    collections = get_all_collections()
    substring_lower = substring.lower()

    matches = [
        col for col in collections
        if substring_lower in col.get('name', '').lower()
    ]

    return matches


def get_collection(collection_id):
    """Get full collection data."""
    url = f"{BASE_URL}/collections/{collection_id}"
    response = requests.get(url, headers=get_headers())

    if response.status_code == 200:
        return response.json().get('collection', {})
    return None


def get_unique_request_name(collection_data, base_name):
    """Generate a unique request name by adding suffix if needed."""
    existing_names = set()

    # Recursively collect all request names from collection
    def collect_names(items):
        for item in items:
            if 'name' in item:
                existing_names.add(item['name'])
            # Check nested folders
            if 'item' in item:
                collect_names(item['item'])

    collect_names(collection_data.get('item', []))

    # If base name doesn't exist, use it
    if base_name not in existing_names:
        return base_name

    # Find the next available suffix
    suffix = 1
    while f"{base_name} {suffix}" in existing_names:
        suffix += 1

    return f"{base_name} {suffix}"


def add_request_to_collection(collection_id, collection_data, request_data, folder_name):
    """Add a new request inside a named folder (folder is created if absent)."""
    # Get unique name
    unique_name = get_unique_request_name(collection_data, request_data['name'])
    if unique_name != request_data['name']:
        print(f"  Name exists, using: {unique_name}")
    request_data['name'] = unique_name

    # Parse URL into Postman format
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(request_data['url'])

    # Build host array (e.g., ["pl-kpidev-dev01-kpi01-euf", "dev", "kpi", "oa", "iqvia", "com"])
    host_parts = parsed_url.netloc.split('.')

    # Build path array (e.g., ["config", "api", "v2", "modules"])
    path_parts = [p for p in parsed_url.path.split('/') if p]

    # Build query array
    query_params = []
    if parsed_url.query:
        for key, values in parse_qs(parsed_url.query, keep_blank_values=True).items():
            for value in values:
                query_params.append({'key': key, 'value': value})

    # Build the request item
    request_item = {
        'name': request_data['name'],
        'request': {
            'method': request_data['method'],
            'header': [
                {'key': k, 'value': v, 'type': 'text'}
                for k, v in request_data['headers'].items()
            ],
            'url': {
                'raw': request_data['url'],
                'protocol': parsed_url.scheme or 'https',
                'host': host_parts,
                'path': path_parts,
                'query': query_params
            }
        }
    }

    # Add body if present
    if request_data['body']:
        request_item['request']['body'] = {
            'mode': 'raw',
            'raw': request_data['body'],
            'options': {
                'raw': {
                    'language': 'json'
                }
            }
        }

    folder = find_or_create_folder(collection_data, folder_name)
    folder['item'].insert(0, request_item)

    # Update collection
    url = f"{BASE_URL}/collections/{collection_id}"
    payload = {'collection': collection_data}

    response = requests.put(url, headers=get_headers(), json=payload)

    if response.status_code != 200:
        print(f"\n  API Error: {response.status_code}")
        try:
            error_data = response.json()
            print(f"  Details: {error_data}")
        except:
            print(f"  Response: {response.text[:500]}")

    return response.status_code == 200


def select_collection():
    """Let user select from 5 most recent collections."""
    collections = get_all_collections()[:5]

    if not collections:
        print("\n❌ No collections found!")
        return None

    print(f"\n  Recent collections:")
    for i, col in enumerate(collections, 1):
        print(f"    {i}. {col.get('name', 'Unknown')}")

    selection = input(f"\n  Select (1-{len(collections)}) [1]: ").strip() or "1"

    try:
        idx = int(selection) - 1
        if 0 <= idx < len(collections):
            return collections[idx]
    except ValueError:
        pass

    print("\n❌ Invalid selection")
    return None


def extract_bearer_token(headers):
    """Extract bearer token from Authorization header (includes 'Bearer ' prefix)."""
    for key, value in headers.items():
        if key.lower() == 'authorization':
            value = value.strip()
            if value.lower().startswith('bearer '):
                return value  # Keep 'Bearer ' prefix
            return value
    return None


def paste_curl_as_request():
    """Paste cURL command as a new request to a collection."""
    curl_command = get_selected_content()

    if not curl_command or 'curl' not in curl_command.lower():
        print("\n❌ No cURL command found in clipboard!")
        return

    print(f"\n  Parsing cURL command...")

    # Parse curl
    parsed = parse_curl(curl_command)

    if not parsed['url']:
        print("\n❌ Could not extract URL from cURL command!")
        return

    print(f"  Method: {parsed['method']}")
    print(f"  URL: {parsed['url']}")
    print(f"  Headers: {len(parsed['headers'])}")
    if parsed['body']:
        print(f"  Body: {len(parsed['body'])} chars")

    # Extract and set bearer token if present
    bearer_token = extract_bearer_token(parsed['headers'])
    if bearer_token:
        print(f"\n  Bearer token found: {bearer_token[:30]}...{bearer_token[-30:]}")
        env_name = "Auth Token"
        if create_or_update_environment(POSTMAN_API_KEY, env_name, GLOBAL_VAR_NAME, bearer_token):
            print(f"  ✓ Environment '{env_name}' updated with auth token!")
        else:
            print(f"  ⚠ Failed to update auth token in environment")

    # Get request name
    request_name = extract_request_name(parsed['url'], parsed['method'])
    print(f"\n  Request name: {request_name}")

    folder_name = infer_kpi_env_folder(parsed['url'])
    if not folder_name:
        folder_name = 'dev'
        print(f"\n  Host does not match kpidev/kpipredev; using folder '{folder_name}'")

    # Select collection
    selected_collection = select_collection()

    if not selected_collection:
        return

    collection_name = selected_collection.get('name', 'Unknown')
    collection_id = selected_collection.get('id')

    print(f"\n  → Using collection: {collection_name}")
    print(f"  → Target folder: {folder_name}")

    # Get full collection data
    collection_data = get_collection(collection_id)
    if not collection_data:
        print("\n❌ Could not fetch collection data!")
        return

    # Prepare request data
    request_data = {
        'name': request_name,
        'method': parsed['method'],
        'url': parsed['url'],
        'headers': parsed['headers'],
        'body': parsed['body']
    }

    # Add request to collection
    print(f"\n  Adding request to collection...")

    if add_request_to_collection(collection_id, collection_data, request_data, folder_name):
        print(f"\n  ✓ Request '{request_name}' added to '{collection_name}' / '{folder_name}'!")
    else:
        print(f"\n  ❌ Failed to add request to collection")


# ============================================
# MAIN
# ============================================
def detect_clipboard_type():
    """Detect if selected content contains a token or cURL command."""
    try:
        content = get_selected_content()
        if not content:
            return "1"  # Default to token

        content_lower = content.lower().strip()

        # Check for cURL command
        if content_lower.startswith('curl ') or content_lower.startswith("curl'"):
            return "2"

        # Check for token patterns (Bearer token or JWT-like)
        if content.startswith('Bearer ') or content.startswith('bearer '):
            return "1"

        # JWT pattern: xxx.xxx.xxx (three base64 parts separated by dots)
        if re.match(r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$', content.strip()):
            return "1"

        return "1"  # Default to token
    except:
        return "1"


def main():
    print(f"\n{'='*50}")
    print("  📮 Paste to Postman")
    print(f"{'='*50}")

    if not POSTMAN_API_KEY:
        print("\n❌ POSTMAN_API_KEY not set!")
        print("\nMake sure pm-api-key.txt exists with your API key.")
        return

    # Step 1: Select from clipboard history
    if not select_from_clipboard_history():
        return

    # Detect default based on selected content
    default_choice = detect_clipboard_type()
    default_label = "Token" if default_choice == "1" else "cURL"

    # Show menu
    print("\nWhat would you like to do with it?")
    print("  1. Auth Token (to environment)")
    print("  2. cURL Request (to collection)")
    print(f"\n  (Detected: {default_label})")

    choice = input(f"\nSelect (1/2) [{default_choice}]: ").strip() or default_choice

    if choice == "1":
        paste_auth_token()
    elif choice == "2":
        paste_curl_as_request()
    else:
        print("\n❌ Invalid choice")

    print(f"\n{'='*50}")
    print(f"\n   Press Enter to close (or wait 2 minutes)...")

    import threading
    enter_pressed = threading.Event()

    def wait_for_enter():
        try:
            input()
            enter_pressed.set()
        except:
            pass

    input_thread = threading.Thread(target=wait_for_enter, daemon=True)
    input_thread.start()
    enter_pressed.wait(timeout=120)  # 2 minutes


if __name__ == "__main__":
    main()
