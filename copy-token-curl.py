"""
Authorization Header Capture via Edge DevTools

Connects to Edge browser (running with debug mode) and captures
Authorization headers from specific service API calls.

Requirements:
    pip install websocket-client pyperclip

Setup:
    1. Run start-edge-debug.cmd to start Edge with debugging
    2. Run: python copy-token.py
    3. Select options and browse - tokens are auto-copied!
"""

import sys
import os
import json
import time
import re
import subprocess
from datetime import datetime

try:
    import websocket
    import pyperclip
except ImportError:
    print("Missing dependencies. Run:")
    print("  pip install websocket-client pyperclip")
    sys.exit(1)

from shell_command_log import log_next_shell_command

import urllib.request
import urllib.error

DEBUG_PORT = 9222

# Service options
SERVICES = {
    '1': 'config',
    '2': 'widget-template-editor-service',
    '3': 'dashboard-service',
}


def check_debug_port(port):
    """Check if Edge debug port is accessible."""
    try:
        url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return 'webSocketDebuggerUrl' in data or 'Browser' in data
    except:
        return False


class TokenCapture:
    def __init__(self, port=DEBUG_PORT):
        self.port = port
        self.ws = None
        self.tokens = []
        self.last_token = None
        self.running = True
        self.msg_id = 1
        self.mode = 'token'  # 'token' or 'curl'
        self.service_name = None
        self.tenant_name = None
        self.curl_pattern = None
        self.curl_pattern_regex = None
        self.curl_method = None  # None = capture all methods
        self.captured_requests = []  # Store captured curl requests by method

    def get_all_tabs(self):
        """Get tabs matching IQVIA URL pattern."""
        try:
            url = f"http://localhost:{self.port}/json"
            with urllib.request.urlopen(url, timeout=3) as resp:
                tabs = json.loads(resp.read().decode())

            valid_tabs = []
            # Pattern: https://pl-{tenant}-dev01-kpi01-euf.dev.kpi.oa.iqvia.com/
            iqvia_pattern = r'https://pl-[^/]+-dev01-kpi01-euf\.dev\.kpi\.oa\.iqvia\.com/'

            for tab in tabs:
                ws_url = tab.get('webSocketDebuggerUrl')
                tab_url = tab.get('url', '')

                # Only include tabs matching IQVIA URL pattern
                if ws_url and re.match(iqvia_pattern, tab_url):
                    valid_tabs.append({
                        'ws_url': ws_url,
                        'title': tab.get('title', 'Unknown'),
                        'url': tab_url
                    })
            return valid_tabs
        except Exception as e:
            return []

    def connect(self):
        """Connect to Edge DevTools - all tabs."""
        tabs = self.get_all_tabs()

        if not tabs:
            return False

        self.connections = []

        for tab in tabs:
            try:
                ws = websocket.create_connection(tab['ws_url'], timeout=5)
                self.connections.append({
                    'ws': ws,
                    'title': tab['title'],
                    'url': tab['url']
                })
                print(f"✓ Connected to: {tab['title'][:40]}...")
            except Exception as e:
                print(f"⚠ Could not connect to: {tab['title'][:30]}... ({e})")

        if not self.connections:
            return False

        print(f"\n✓ Monitoring {len(self.connections)} tab(s)")
        return True

    def send(self, method, params=None):
        """Send CDP command to all connected tabs."""
        msg = {"id": self.msg_id, "method": method, "params": params or {}}
        self.msg_id += 1
        for conn in self.connections:
            try:
                conn['ws'].send(json.dumps(msg))
            except:
                pass

    def extract_tenant_from_url(self, url):
        """Extract tenant name from URL pattern: https://pl-{tenant}-dev01-..."""
        match = re.search(r'https://pl-([^-]+)-dev01-', url)
        if match:
            return match.group(1)
        return None

    def matches_service_url(self, url):
        """Check if URL matches the service pattern."""
        if not self.service_name:
            return True  # No filter, match all

        # Pattern: https://pl-{tenant}-dev01-kpi01-euf.dev.kpi.oa.iqvia.com/{service-name}
        pattern = rf'https://pl-[^/]+-dev01-kpi01-euf\.dev\.kpi\.oa\.iqvia\.com/{re.escape(self.service_name)}'
        return re.match(pattern, url) is not None

    def url_to_pattern(self, url):
        """Convert a URL with variable parts to a regex pattern."""
        # Remove query string for pattern matching on path
        url_path = url.split('?')[0]

        # Escape special regex characters first
        pattern = re.escape(url_path)

        # Replace ONLY the tenant name with wildcard (keep the rest of domain fixed)
        # Pattern: https://pl-{tenant}-dev01-kpi01-euf.dev.kpi.oa.iqvia.com
        pattern = re.sub(
            r'https://pl\\-([^\\]+)\\-dev01\\-kpi01\\-euf\\.dev\\.kpi\\.oa\\.iqvia\\.com',
            r'https://pl-[^-]+-dev01-kpi01-euf\\.dev\\.kpi\\.oa\\.iqvia\\.com',
            pattern
        )

        # Replace UUIDs (e.g., 54e4dc68-8823-44fc-b159-37c8957de041)
        pattern = re.sub(
            r'[a-fA-F0-9]{8}\\-[a-fA-F0-9]{4}\\-[a-fA-F0-9]{4}\\-[a-fA-F0-9]{4}\\-[a-fA-F0-9]{12}',
            r'[a-fA-F0-9-]{36}',
            pattern
        )

        # Replace numbers in path segments (e.g., /66786/)
        pattern = re.sub(r'/\\d+(?=/|$)', r'/[^/]+', pattern)

        # Replace path segments that look like variables (contain underscore or are alphanumeric mix)
        # This handles cases like /tulu_BU/ or /Tulu_module/
        parts = pattern.split('/')
        new_parts = []
        for i, part in enumerate(parts):
            # Skip domain parts and known fixed parts
            if i < 4 or part in ['api', 'v1', 'v2', 'admin', 'config', 'dashboard\\-service', 'widget\\-template\\-editor\\-service']:
                new_parts.append(part)
            # Replace segments with underscores or mixed case that look like variables
            elif '_' in part or (part and not part.replace('\\', '').isalpha()):
                new_parts.append('[^/]+')
            else:
                new_parts.append(part)

        pattern = '/'.join(new_parts)

        return pattern

    def matches_curl_pattern(self, url, method):
        """Check if URL matches the curl pattern (method check only if specified)."""
        if not self.curl_pattern_regex:
            return False

        # Check method only if specified
        if self.curl_method and method.upper() != self.curl_method.upper():
            return False

        # Check URL pattern (ignore query string for matching)
        url_path = url.split('?')[0]
        return re.match(self.curl_pattern_regex, url_path) is not None

    def capture_loop(self):
        """Main loop to capture tokens from all tabs."""
        for conn in self.connections:
            conn['ws'].settimeout(0.01)  # Very short timeout for fast response

        if self.mode == 'curl':
            print("   (Listening... refresh the page now)")

            # For curl mode, collect requests until 5s after first match or Enter
            import threading
            stop_event = threading.Event()
            first_match_time = None
            WAIT_AFTER_MATCH = 5  # seconds to wait after first match

            def wait_for_enter():
                try:
                    input()
                    stop_event.set()
                except:
                    pass

            input_thread = threading.Thread(target=wait_for_enter, daemon=True)
            input_thread.start()

            try:
                while not stop_event.is_set():
                    # Check if 5 seconds passed since first match
                    if first_match_time and (time.time() - first_match_time) >= WAIT_AFTER_MATCH:
                        print(f"   \033[90m(Auto-stopping after {WAIT_AFTER_MATCH}s)\033[0m")
                        break

                    prev_count = len(self.captured_requests)

                    for conn in self.connections[:]:
                        try:
                            msg = conn['ws'].recv()
                            self.process_message(msg)
                        except websocket.WebSocketTimeoutException:
                            continue
                        except websocket.WebSocketConnectionClosedException:
                            self.connections.remove(conn)
                        except:
                            continue

                    # Start timer on first match
                    if not first_match_time and len(self.captured_requests) > prev_count:
                        first_match_time = time.time()

                    if not self.connections:
                        print("\n⚠ All tabs closed")
                        break
            except KeyboardInterrupt:
                pass

            # Finalize - select from captured requests
            self.finalize_curl_capture()
        else:
            # Token mode - original behavior
            print("   (Listening... refresh the page now)")

            try:
                while self.running:
                    for conn in self.connections[:]:
                        try:
                            msg = conn['ws'].recv()
                            self.process_message(msg)

                            # Exit if we got a token
                            if not self.running:
                                return
                        except websocket.WebSocketTimeoutException:
                            continue
                        except websocket.WebSocketConnectionClosedException:
                            self.connections.remove(conn)
                        except KeyboardInterrupt:
                            raise
                        except:
                            continue

                    if not self.connections:
                        print("\n⚠ All tabs closed")
                        break
            except KeyboardInterrupt:
                self.running = False

    def process_message(self, raw_msg):
        """Process WebSocket message and extract tokens."""
        try:
            msg = json.loads(raw_msg)
            cdp_method = msg.get('method', '')

            if cdp_method == 'Network.requestWillBeSent':
                params = msg.get('params', {})
                request = params.get('request', {})
                headers = request.get('headers', {})
                url = request.get('url', '')
                http_method = request.get('method', 'GET')

                # Only process Fetch/XHR requests
                request_type = params.get('type', '')
                if request_type not in ('XHR', 'Fetch'):
                    return

                # For curl mode, check URL and method pattern
                if self.mode == 'curl':
                    if not self.matches_curl_pattern(url, http_method):
                        return
                # For token mode, check service filter
                elif self.service_name and not self.matches_service_url(url):
                    return

                for name, value in headers.items():
                    if name.lower() == 'authorization':
                        if value != self.last_token or self.mode == 'curl':
                            self.last_token = value

                            # Extract tenant name
                            tenant = self.extract_tenant_from_url(url)
                            if tenant and not self.tenant_name:
                                self.tenant_name = tenant

                            self.tokens.append({
                                'token': value,
                                'url': url,
                                'tenant': tenant,
                                'time': datetime.now()
                            })

                            if self.mode == 'token':
                                self.handle_token_capture(value, url, tenant)
                            elif self.mode == 'curl':
                                self.collect_curl_request(value, url, request, tenant)
                        break
        except:
            pass

    def handle_token_capture(self, token, url, tenant):
        """Handle token copy mode."""
        pyperclip.copy(token)

        print(f"\n{'='*80}")
        print(f"🔑 TOKEN COPIED TO CLIPBOARD!")
        print(f"{'='*80}")
        print(f"   Tenant: {tenant or 'unknown'}")
        print(f"   Time:   {datetime.now().strftime('%H:%M:%S')}")
        print(f"\n   API URL:")
        print(f"   {url}")
        print(f"\n   Token (first 20 chars):")
        print(f"   {token[:20]}...")
        print(f"{'='*80}")

        # Offer to run paste-to-postman
        self.prompt_paste_to_postman()

        # Exit after first token
        self.running = False

    def collect_curl_request(self, token, url, request, tenant):
        """Collect curl request for later selection."""
        method = request.get('method', 'GET')

        # Check if we already have this method
        existing_methods = [r['method'] for r in self.captured_requests]
        if method in existing_methods:
            return  # Already have this method

        self.captured_requests.append({
            'method': method,
            'url': url,
            'request': request,
            'tenant': tenant,
            'token': token
        })

        print(f"   \033[92m✓ Captured {method} request\033[0m")

        # If this is the first capture, we'll wait for more
        # The capture loop will handle finalization

    def finalize_curl_capture(self):
        """Finalize curl capture - select from multiple methods if needed."""
        if not self.captured_requests:
            print("\n❌ No matching requests captured!")
            return

        selected = None

        if len(self.captured_requests) == 1:
            # Only one method, use it directly
            selected = self.captured_requests[0]
        else:
            # Multiple methods - let user choose
            print(f"\n{'='*50}")
            print(f"  Multiple methods captured:")
            print(f"{'='*50}")

            for i, req in enumerate(self.captured_requests, 1):
                print(f"    {i}. {req['method']}")

            choice = input(f"\n  Select (1-{len(self.captured_requests)}) [1]: ").strip() or "1"

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.captured_requests):
                    selected = self.captured_requests[idx]
            except ValueError:
                pass

            if not selected:
                print("\n❌ Invalid selection, using first")
                selected = self.captured_requests[0]

        # Now build and copy the curl command
        self.handle_curl_capture(selected)

    def handle_curl_capture(self, captured):
        """Handle curl copy mode - build and copy cURL command."""
        method = captured['request'].get('method', 'GET')
        headers = captured['request'].get('headers', {})
        post_data = captured['request'].get('postData', '')
        url = captured['url']
        tenant = captured['tenant']

        # Build cURL command
        curl_parts = ['curl']

        # Add method if not GET
        if method.upper() != 'GET':
            curl_parts.append(f'-X {method.upper()}')

        # Add URL (quoted)
        curl_parts.append(f"'{url}'")

        # Add headers
        for header_name, header_value in headers.items():
            # Skip some headers that curl handles automatically
            if header_name.lower() in ('content-length', 'host'):
                continue
            # Escape single quotes in header values
            escaped_value = header_value.replace("'", "'\\''")
            curl_parts.append(f"-H '{header_name}: {escaped_value}'")

        # Add request body for POST/PUT/PATCH
        if post_data and method.upper() in ('POST', 'PUT', 'PATCH'):
            # Escape single quotes in body
            escaped_body = post_data.replace("'", "'\\''")
            curl_parts.append(f"-d '{escaped_body}'")

        # Join with line continuation for readability
        curl_command = ' \\\n  '.join(curl_parts)

        # Copy to clipboard
        pyperclip.copy(curl_command)

        print(f"\n{'='*80}")
        print(f"📋 cURL COMMAND COPIED TO CLIPBOARD!")
        print(f"{'='*80}")
        print(f"   Tenant: {tenant or 'unknown'}")
        print(f"   Time:   {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Method: {method}")
        print(f"\n   API URL:")
        print(f"   {url}")
        print(f"\n   cURL Command (first 200 chars):")
        print(f"   {curl_command[:200]}...")
        print(f"{'='*80}")

        # Offer to run paste-to-postman
        self.prompt_paste_to_postman()

    def prompt_paste_to_postman(self):
        """Launch paste-to-postman script."""
        print(f"\n   \033[92mLaunching paste-to-postman...\033[0m")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        paste_script = os.path.join(script_dir, 'paste-to-postman.py')
        cmd = ['python', paste_script]
        log_next_shell_command(cmd)
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def show_menu(self):
        """Show main menu and get user selection."""
        print(f"\n{'='*50}")
        print("  🔐 Edge Authorization Capture")
        print(f"{'='*50}")
        print("\nWhat would you like to copy?")
        print("  1. Authorization Token")
        print("  2. Copy as cURL")

        choice = input("\nSelect (1/2) [1]: ").strip() or "1"

        if choice == "1":
            self.mode = 'token'
            self.select_service()
        elif choice == "2":
            self.mode = 'curl'
            self.setup_curl_mode()
        else:
            print("Invalid choice, defaulting to Token mode")
            self.mode = 'token'
            self.select_service()

    def select_service(self):
        """Let user select which service to monitor."""
        print(f"\n{'='*50}")
        print("  Select Service to Monitor")
        print(f"{'='*50}")
        print("\nWhich service do you want to capture tokens from?")
        print("  1. config")
        print("  2. widget-template-editor-service")
        print("  3. dashboard-service")
        print("  4. All services (no filter)")

        choice = input("\nSelect (1/2/3/4) [4]: ").strip() or "4"

        if choice in SERVICES:
            self.service_name = SERVICES[choice]
            print(f"\n✓ Monitoring: {self.service_name}")
        else:
            self.service_name = None
            print("\n✓ Monitoring: All services")

    def setup_curl_mode(self):
        """Setup curl copy mode."""
        print(f"\n{'='*50}")
        print("  cURL Copy Mode Setup")
        print(f"{'='*50}")

        # Get URL
        print("\nPaste the API URL to match:")
        self.curl_pattern = input("\nURL: ").strip()

        if not self.curl_pattern:
            print("❌ No URL provided, falling back to token mode")
            self.mode = 'token'
            self.select_service()
            return

        # Auto-generate pattern
        self.curl_pattern_regex = self.url_to_pattern(self.curl_pattern)

        print(f"\n{'='*60}")
        print("  Auto-generated Pattern:")
        print(f"{'='*60}")
        print(f"\n  {self.curl_pattern_regex}")
        print(f"\n{'='*60}")
        print("  Press Enter if correct, or 'm' to manually select variable parts")
        print(f"{'='*60}")

        choice = input("\n[Enter/m]: ").strip().lower()

        if choice == 'm':
            # Manual selection
            self.curl_pattern_regex = self.interactive_pattern_builder(self.curl_pattern)

            if not self.curl_pattern_regex:
                print("❌ Pattern creation failed, falling back to token mode")
                self.mode = 'token'
                self.select_service()
                return

        print(f"\n✓ Pattern confirmed")
        print(f"✓ Will capture matching requests (any method)")

        self.curl_method = None  # Capture all methods
        self.service_name = None  # Disable service filter for curl mode

    def interactive_pattern_builder(self, url):
        """Interactively build URL pattern by letting user choose variable parts."""
        from urllib.parse import urlparse, parse_qs

        # Parse URL
        parsed = urlparse(url)

        # Extract path segments (skip empty ones)
        path_segments = [s for s in parsed.path.split('/') if s]

        # Extract query params
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        # Initialize parts with auto-detection
        parts = []

        # Domain (tenant part)
        tenant_match = re.search(r'pl-([^-]+)-dev01', parsed.netloc)
        if tenant_match:
            tenant = tenant_match.group(1)
            parts.append({'type': 'tenant', 'value': tenant, 'variable': True})

        # Path segments
        for seg in path_segments:
            is_var = self.looks_like_variable(seg)
            parts.append({'type': 'path', 'value': seg, 'variable': is_var})

        while True:
            print(f"\n{'='*60}")
            print("  URL Parts - Select which are VARIABLE")
            print(f"{'='*60}")

            idx = 0

            # Domain (tenant part)
            tenant_part = next((p for p in parts if p['type'] == 'tenant'), None)
            if tenant_part:
                print(f"\n  [Domain]")
                var_marker = " [VARIABLE]" if tenant_part['variable'] else " [FIXED]"
                print(f"    {idx}. Tenant: {tenant_part['value']}{var_marker}")
                idx += 1

            # Path segments
            path_parts = [p for p in parts if p['type'] == 'path']
            if path_parts:
                print(f"\n  [Path Segments]")
                for part in path_parts:
                    var_marker = " [VARIABLE]" if part['variable'] else " [FIXED]"
                    print(f"    {idx}. /{part['value']}{var_marker}")
                    idx += 1

            print(f"\n{'='*60}")
            print("  Options:")
            print("    - Press Enter to confirm")
            print("    - Enter numbers to TOGGLE variable status (comma-separated)")
            print(f"{'='*60}")

            choice = input("\nToggle (or Enter to confirm): ").strip()

            if not choice:
                # User confirmed, build the pattern
                return self.build_pattern_from_parts(parsed, parts)

            # Toggle selected parts
            try:
                indices = [int(x.strip()) for x in choice.split(',') if x.strip()]
                for i in indices:
                    if 0 <= i < len(parts):
                        parts[i]['variable'] = not parts[i]['variable']
                        status = "VARIABLE" if parts[i]['variable'] else "FIXED"
                        print(f"    ✓ Part {i} is now {status}")
            except ValueError:
                print("    ⚠ Invalid input, try again")

    def looks_like_variable(self, value):
        """Check if a value looks like a variable (UUID, number, etc.)."""
        if not value:
            return False
        # UUID pattern
        if re.match(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$', value):
            return True
        # Pure number
        if value.isdigit():
            return True
        # Contains underscore (likely a variable like tulu_BU)
        if '_' in value and not value.startswith('api'):
            return True
        # null or similar
        if value.lower() in ('null', 'undefined', 'true', 'false'):
            return True
        return False

    def build_pattern_from_parts(self, parsed, parts):
        """Build regex pattern from the parts configuration."""
        # Build domain pattern - keep fixed except tenant
        # Domain: pl-{tenant}-dev01-kpi01-euf.dev.kpi.oa.iqvia.com
        tenant_part = next((p for p in parts if p['type'] == 'tenant'), None)
        if tenant_part and tenant_part['variable']:
            domain_pattern = r'pl-[^-]+-dev01-kpi01-euf\.dev\.kpi\.oa\.iqvia\.com'
        else:
            domain_pattern = re.escape(parsed.netloc)

        # Build path pattern
        path_parts_list = []
        for part in parts:
            if part['type'] == 'path':
                if part['variable']:
                    path_parts_list.append('[^/]+')
                else:
                    path_parts_list.append(re.escape(part['value']))

        path_pattern = '/' + '/'.join(path_parts_list) if path_parts_list else ''

        # Combine into full pattern (ignoring query string for matching)
        full_pattern = f"https://{domain_pattern}{path_pattern}"

        print(f"\n✓ Final pattern:")
        print(f"  {full_pattern}")

        return full_pattern

    def run(self):
        """Main entry point."""
        # Check if Edge debug port is available
        print(f"\n🔍 Checking Edge debug port {self.port}...")

        if not check_debug_port(self.port):
            print("❌ Edge not running with debugging enabled")
            print("\nPlease run start-edge-debug.cmd first, then run this script again.")
            return

        print("✓ Debug port is accessible")

        # Show menu
        self.show_menu()

        # Connect to IQVIA tabs
        print(f"\n🔗 Looking for IQVIA tabs...")
        if not self.connect():
            print("❌ No IQVIA tabs found!")
            print("   Open a tab with URL: https://pl-{tenant}-dev01-kpi01-euf.dev.kpi.oa.iqvia.com/")
            print("   Then run this script again")
            return

        # Enable network monitoring
        self.send("Network.enable", {})
        print("✓ Network monitoring enabled")

        print(f"\n{'='*50}")
        print("🎯 READY! Navigate to your page manually")
        print("   Tokens will be auto-copied to clipboard")
        print("   Press Ctrl+C to stop")
        print(f"{'='*50}\n")

        try:
            self.capture_loop()
        except KeyboardInterrupt:
            pass

        # Summary
        print(f"\n{'='*50}")
        print(f"📊 Session ended")
        print(f"   Tokens captured: {len(self.tokens)}")
        if self.tenant_name:
            print(f"   Tenant: {self.tenant_name}")
        if self.tokens:
            print(f"   Last token in clipboard ✓")
        print(f"{'='*50}")


def main():
    capture = TokenCapture()
    capture.run()


if __name__ == "__main__":
    main()
