import os
import subprocess
import sys
import time

from shell_command_log import log_next_shell_command

def kill_edge_processes():
    """Kill all Edge browser processes."""
    print("Closing all Edge processes...")
    # Suppress output and errors
    cmd1 = ["taskkill", "/F", "/IM", "msedge.exe"]
    log_next_shell_command(cmd1)
    subprocess.run(
        cmd1,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    cmd2 = ["taskkill", "/F", "/IM", "msedgewebview2.exe"]
    log_next_shell_command(cmd2)
    subprocess.run(
        cmd2,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def start_edge_with_debugging():
    """Start Edge with remote debugging enabled on port 9222."""
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        # r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    args = ["--remote-debugging-port=9222", "--remote-allow-origins=*"]

    for edge_path in edge_paths:
        if os.path.exists(edge_path):
            print(f"Starting Edge with debugging on port 9222...")
            cmd = [edge_path] + args
            log_next_shell_command(cmd)
            subprocess.Popen(cmd)
            return True

    print("Error: Could not find Edge browser installation.")
    return False


def main():
    print("=" * 44)
    print("  Starting Edge with Remote Debugging")
    print("=" * 44)
    print()

    kill_edge_processes()

    print("Waiting for Edge to fully close...")
    time.sleep(3)

    if not start_edge_with_debugging():
        sys.exit(1)

    print()
    print("Waiting for Edge to start...")
    time.sleep(3)

    print()
    print("=" * 44)
    print("  Edge is ready!")
    print("  Now run: python copy-token.py")
    print("=" * 44)


if __name__ == "__main__":
    main()

