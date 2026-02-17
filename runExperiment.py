import os
import subprocess
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox


CUR_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CUR_DIR)

ENTER_SCRIPT = os.path.join(CUR_DIR, "experimenter_mode_scripts", "enterExperimentMode.ps1")
EXIT_SCRIPT = os.path.join(CUR_DIR, "experimenter_mode_scripts", "exitExperimentMode.ps1")
EXPERIMENT = os.path.join(CUR_DIR, "main_experimental_flow.py")


# -------------------------
# Admin elevation
# -------------------------

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def relaunch_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        f'"{__file__}"',
        None,
        1
    )
    sys.exit()


# -------------------------
# PowerShell
# -------------------------

def run_powershell(script_path):
    result = subprocess.run([
        "powershell",
        "-ExecutionPolicy", "Bypass",
        "-File", script_path
    ])

    if result.returncode != 0:
        print(f"PowerShell exited with code {result.returncode}", flush = True)

    return result.returncode


# -------------------------
# Popup
# -------------------------

def show_mode_popup():
    root = tk.Tk()
    root.title("Experiment Mode")
    root.geometry("420x200")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    choice = {"value": None}

    def continue_pressed():
        choice["value"] = "continue"
        root.destroy()

    def quit_pressed():
        choice["value"] = "quit"
        root.destroy()

    tk.Label(
        root,
        text="Experimenter mode is ACTIVE.\n\nChoose how to proceed.",
        font=("Segoe UI", 11),
        justify="center"
    ).pack(pady=25)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)

    tk.Button(
        btn_frame,
        text="Continue to Experiment",
        width=20,
        command=continue_pressed
    ).pack(side="left", padx=10)

    tk.Button(
        btn_frame,
        text="Quit",
        width=12,
        command=quit_pressed
    ).pack(side="left", padx=10)

    root.mainloop()
    return choice["value"]


def show_disabled_popup():
    popup = tk.Tk()
    popup.withdraw()
    popup.attributes("-topmost", True)
    messagebox.showinfo(
        "Experiment Mode Disabled",
        "Experimenter mode has been disabled.\n\nSystem restored."
    )
    popup.destroy()


def print_system_state(label):
    if label == "INITIAL SYSTEM STATE":
        print("=" * 60, flush = True)
    else: 
        print("\n" + "=" * 60, flush = True)
    print(f"{label}", flush = True)
    print("=" * 60, flush = True)

    subprocess.run([
        "powershell",
        "-Command",
        "Get-Service SysMain, WSearch, wuauserv | "
        "Select Name, Status, StartType | Format-Table -AutoSize"
    ])

    # subprocess.run([
    #     "powershell",
    #     "-Command",
    #     "Get-MpPreference | Select DisableRealtimeMonitoring"
    # ])

    print("Defender Exclusion Check:", flush = True)

    result = subprocess.run(
        [
            "powershell",
            "-Command",
            "(Get-MpPreference).ExclusionPath"
        ],
        capture_output=True,
        text=True
    )

    exclusions = result.stdout.strip().splitlines()

    normalized_project = os.path.normcase(os.path.normpath(PROJECT_ROOT))
    normalized_exclusions = [
        os.path.normcase(os.path.normpath(e.strip()))
        for e in exclusions if e.strip()
    ]

    if normalized_project in normalized_exclusions:
        print(f"  Project root is EXCLUDED from Defender:\n    {PROJECT_ROOT}\n", flush = True)
    else:
        print(f"  Project root is NOT excluded from Defender:\n    {PROJECT_ROOT}\n", flush = True)

    subprocess.run([
        "powershell",
        "-Command",
        "powercfg -getactivescheme"
    ])
    print("\n" + "=" * 60, flush = True)
    print("=" * 60 + "\n", flush = True)


# -------------------------
# Main Flow
# -------------------------

if __name__ == "__main__":

    if not is_admin():
        relaunch_as_admin()

    print_system_state("INITIAL SYSTEM STATE")

    print("\n" + "=" * 60, flush = True)
    print(f"EXPERIMENT MODE ACTIVATION", flush = True)
    print("=" * 60, flush = True)
    print("Enabling experiment mode...", flush = True)
    run_powershell(ENTER_SCRIPT)
    print("=" * 60, flush = True)
    print("=" * 60 + "\n", flush = True)

    print_system_state("STATE AFTER ENTERING EXPERIMENT MODE")

    decision = show_mode_popup()
    if decision == "quit":
        print("\n\n" + "=" * 60, flush = True)
        print(f"EXPERIMENT MODE DEACTIVATION", flush = True)
        print("=" * 60, flush = True)
        print("Restoring system...", flush = True)
        run_powershell(EXIT_SCRIPT)
        print("=" * 60, flush = True)
        print("=" * 60, flush = True)
        print_system_state("FINAL SYSTEM STATE AFTER RESTORE")
        show_disabled_popup()
        print("\n\nDone.", flush = True)
        input("\n\nPress Enter to close this window...")
        sys.exit()

    try:
        print("\n" + "=" * 60, flush = True)
        print(f"EXPERIMENT LOGS", flush = True)
        print("=" * 60, flush = True)
        subprocess.run([sys.executable, EXPERIMENT])
    finally:
        print("\n\n" + "=" * 60, flush = True)
        print(f"EXPERIMENT MODE DEACTIVATION", flush = True)
        print("=" * 60 + "\n", flush = True)
        print("Restoring system...", flush = True)
        run_powershell(EXIT_SCRIPT)
        print_system_state("FINAL SYSTEM STATE AFTER RESTORE")
        print("\n" + "=" * 60 + "\n", flush = True)
        show_disabled_popup()

    print("\n\nDone.", flush = True)
    input("\n\nPress Enter to close this window...")
