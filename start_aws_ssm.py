import threading
import subprocess

from shell_command_log import log_next_shell_command
import msvcrt
import time

def flush_stdin():
    """Clear any buffered input from stdin (Windows-specific)"""
    while msvcrt.kbhit():
        msvcrt.getch()

def wait_for_enter(event):
    input()
    event.set()


# aws ssm start-session --region eu-central-1 --profile devCluster --target i-081b4614582b0f0b3 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433

# aws ssm start-session --region eu-central-1 --target i-08acabe420a38c420 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host="oa-euf-shared-postgresql-db-aurora-dev-one.cefekb6lills.eu-central-1.rds.amazonaws.com",portNumber="5432",localPortNumber="5432" --profile 133460326175

# aws ssm start-session --region eu-central-1 --target  i-05d95e75dace1dc79 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433 --profile devCluster
def run_ssm_session(timeout=None):
    # CLI equivalent (PowerShell - use backtick ` for line continuation):
    """
    aws ssm start-session `
        --region eu-central-1 `
        --target i-0c37bb3d4ad201e7b `
        --document-name AWS-StartPortForwardingSessionToRemoteHost `
        --parameters "host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433" `
        --profile devCluster
    """
    try:
        cmd = [
            "aws", "ssm", "start-session",
            "--region", "eu-central-1",
            "--target", "i-0c37bb3d4ad201e7b",
            "--document-name", "AWS-StartPortForwardingSessionToRemoteHost",
            "--parameters", "host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433",
            "--profile", "devCluster"
        ]
        log_next_shell_command(cmd)
        subprocess.run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("\033[93mSession timed out after {} seconds (test mode)\033[0m".format(timeout))

TEST_MODE = False  # Set to False for normal operation
TEST_TIMEOUT = 15  # seconds

RECONNECT_DELAY = 3  # seconds to wait before reconnecting (allows port release)

first_run = True
while True:
    if not first_run:
        print(f"\033[90mWaiting {RECONNECT_DELAY}s for port release...\033[0m")
        time.sleep(RECONNECT_DELAY)
    first_run = False

    print("\033[92mStarting SSM session...\033[0m")
    run_ssm_session(timeout=TEST_TIMEOUT if TEST_MODE else None)

    print("\033[93mDisconnected. Press Enter to reconnect now, or wait 5 minutes...\033[0m")

    flush_stdin()  # Clear any buffered input from the SSM session
    event = threading.Event()
    input_thread = threading.Thread(target=wait_for_enter, args=(event,), daemon=True)
    input_thread.start()

    # Efficiently waits - no polling! Uses OS-level wait
    pressed = event.wait(timeout=300)  # 5 minutes

    if pressed:
        print("\033[96mReconnecting now!\033[0m")