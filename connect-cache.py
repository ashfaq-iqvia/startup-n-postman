import subprocess
import shutil
import threading
import msvcrt
import time

from shell_command_log import log_next_shell_command

def flush_stdin():
    """Clear any buffered input from stdin (Windows-specific)"""
    while msvcrt.kbhit():
        msvcrt.getch()


def wait_for_enter(event):
    input()
    event.set()


# File copy mappings: (source_subfolder, destination)
APPSETTINGS_MAPPINGS = [
    ("config", r"C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Configuration\src\PMI.Service.Configuration\appsettings.Development.json"),
    ("migration", r"C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Migration\src\PMI.Service.Migration\appsettings.Development.json"),
    ("dashboard", r"C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Dashboard\src\PMI.Service.Dashboard\appsettings.Development.json"),
    ("export", r"C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Export\src\PMI.Service.Export\appsettings.Development.json"),
    ("mapShapeGen", r"C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_MapShapeGen\src\PMI.Service.Map\appsettings.Development.json"),
    ("widget template editor", r"C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_WidgetTemplateEditor\src\PMI.Service.WidgetTemplateEditor\appsettings.Development.json"),
]

BASE_PATH = r"C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format"


def copy_appsettings(env: str):
    """Copy appsettings files from the specified environment folder."""
    for subfolder, dest in APPSETTINGS_MAPPINGS:
        source = rf"{BASE_PATH}\{env}\{subfolder}\appsettings.Development.json"
        shutil.copy(source, dest)
        print(f"Copied: {subfolder}")


RECONNECT_DELAY = 3  # seconds to wait before reconnecting (allows port release)


def run_port_forward(is_dev: bool):
    """Run kubectl port-forward in a loop with auto-reconnect."""
    env_name = "dev" if is_dev else "predev"
    first_run = True

    while True:
        if not first_run:
            print(f"\033[90mWaiting {RECONNECT_DELAY}s for port release...\033[0m")
            time.sleep(RECONNECT_DELAY)
        first_run = False

        print(f"\033[92mStarting port-forward ({env_name})...\033[0m")

        if is_dev:
            """
            kubectl `
                --context pl-euf-kpi `
                -n commons `
                port-forward pods/core-cache-service-0 27018:27017
            """
            cmd = [
                "kubectl", "--context", "pl-euf-kpi",
                "-n", "commons",
                "port-forward", "pods/core-cache-service-1", "27018:27017"
            ]
            log_next_shell_command(cmd)
            subprocess.run(cmd)
        else:
            """
            kubectl `
                --context pl-euf-kpi `
                --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpidev `
                port-forward pods/core-cache-service-0 30017:27017

            kubectl `
                --context pl-euf-kpi `
                --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpidev `
                port-forward pods/core-cache-service-1 30017:27017

            kubectl `
                --context pl-euf-kpi `
                --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpidev `
                port-forward services/core-cache-service-svc 27018:27017 `
                -n commons

            kubectl `
                --context pl-euf-kpi `
                --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpipredev `
                port-forward pods/core-cache-service-0 27018:27017 `
                -n commons
            """
            cmd = [
                "kubectl", "--context", "pl-euf-kpi",
                "--namespace", "oa-pl-euf-kpideveloper-kpi01-dev01-kpipredev",
                "port-forward", "pods/core-cache-service-1", "27018:27017",
                "-n", "commons"
            ]
            log_next_shell_command(cmd)
            subprocess.run(cmd)

        print("\033[93mDisconnected. Press Enter to reconnect now, or wait 15 minutes...\033[0m")

        flush_stdin()  # Clear any buffered input from the kubectl session
        event = threading.Event()
        input_thread = threading.Thread(target=wait_for_enter, args=(event,), daemon=True)
        input_thread.start()

        # Efficiently waits - no polling! Uses OS-level wait
        pressed = event.wait(timeout=900)  # 15 minutes

        if pressed:
            print("\033[96mReconnecting now!\033[0m")


# Prompt the user for input
inp = input("dev? (y(yes)/(anything - {y})): ")
copy_from_appsettings = input("copy? (y(yes)/(anything - {y})): ")

is_dev = inp == "y"

if copy_from_appsettings == "y":
    env = "dev" if is_dev else "predev"
    copy_appsettings(env)

run_port_forward(is_dev)

"""
Reference command for updating kubeconfig:
aws eks update-kubeconfig `
    --name oa-pl-euf-kpideveloper-kpi01 `
    --region eu-central-1 `
    --role-arn arn:aws:iam::662744937784:role/PL_OA-oa-pl-euf-kpideveloper-kpi01-eks-admin `
    --profile devCluster `
    --alias pl-euf-kpi
"""

