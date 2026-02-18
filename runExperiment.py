import os
import subprocess
import sys
import ctypes
from ctypes import wintypes
import atexit
import platform
import tkinter as tk
from tkinter import messagebox

# Turns off various windows things so experiment is not interrupted or slowed
EXPERIMENTER_MODE = True

CUR_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CUR_DIR)

ENTER_SCRIPT = os.path.join(CUR_DIR, "experimenter_mode_scripts", "enterExperimentMode.ps1")
EXIT_SCRIPT = os.path.join(CUR_DIR, "experimenter_mode_scripts", "exitExperimentMode.ps1")
EXPERIMENT = os.path.join(CUR_DIR, "main_experimental_flow.py")

NUM_EQUALS = 75

# -------------------------
# Cleanup state tracking
# -------------------------
_experiment_mode_active = False
_cleanup_done = False

# -------------------------
# Console Control Handler (catches terminal close, Ctrl+C, etc.)
# -------------------------
CTRL_C_EVENT = 0
CTRL_BREAK_EVENT = 1
CTRL_CLOSE_EVENT = 2
CTRL_LOGOFF_EVENT = 5
CTRL_SHUTDOWN_EVENT = 6

HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
kernel32 = ctypes.windll.kernel32

def _emergency_cleanup():
    """Restore system state - called on abnormal exit."""
    global _cleanup_done
    if _cleanup_done or not _experiment_mode_active:
        return
    _cleanup_done = True
    print("\n[EMERGENCY] Restoring system state...", flush=True)
    run_powershell(EXIT_SCRIPT)

def _console_ctrl_handler(ctrl_type):
    """Handle console control events (close button, Ctrl+C, etc.)."""
    if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT, 
                     CTRL_C_EVENT, CTRL_BREAK_EVENT):
        _emergency_cleanup()
        return True  # Signal handled
    return False

# Create handler reference (must keep alive to prevent garbage collection)
_handler = HANDLER_ROUTINE(_console_ctrl_handler)

def _register_cleanup_handlers():
    """Register handlers to restore system on abnormal termination."""
    # Register console control handler for terminal close, Ctrl+C, etc.
    kernel32.SetConsoleCtrlHandler(_handler, True)
    # Register atexit as backup
    atexit.register(_emergency_cleanup)

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
        print("=" * NUM_EQUALS, flush = True)
    else: 
        print("\n" + "=" * NUM_EQUALS, flush = True)
    print(f"{label}", flush = True)
    print("=" * NUM_EQUALS, flush = True)

    subprocess.run([
        "powershell",
        "-Command",
        "Get-Service SysMain, WSearch, wuauserv | "
        "Select Name, Status, StartType | Format-Table -AutoSize"
    ])

    # Disable realtime monitoring for duration of the experiment
    # I don't know what is wrong but computer seems to ignore it
    # subprocess.run([
    #     "powershell",
    #     "-Command",
    #     "Get-MpPreference | Select DisableRealtimeMonitoring"
    # ])


    #  Add folder to windows defender exclusions
    # I don't know what is wrong but computer seems to ignore it
    # print("Defender Exclusion Check:", flush = True)
    # 
    # result = subprocess.run(
    #     [
    #         "powershell",
    #         "-Command",
    #         "(Get-MpPreference).ExclusionPath"
    #     ],
    #     capture_output=True,
    #     text=True
    # )

    # exclusions = result.stdout.strip().splitlines()

    # normalized_project = os.path.normcase(os.path.normpath(PROJECT_ROOT))
    # normalized_exclusions = [
    #     os.path.normcase(os.path.normpath(e.strip()))
    #     for e in exclusions if e.strip()
    # ]
    # 
    # if normalized_project in normalized_exclusions:
    #     print(f"  Project root is EXCLUDED from Defender:\n    {PROJECT_ROOT}\n", flush = True)
    # else:
    #     print(f"  Project root is NOT excluded from Defender:\n    {PROJECT_ROOT}\n", flush = True)

    subprocess.run([
        "powershell",
        "-Command",
        "powercfg -getactivescheme"
    ])
    print("\n" + "=" * NUM_EQUALS, flush = True)
    print("=" * NUM_EQUALS + "\n\n", flush = True)


# -------------------------
# Main Flow
# -------------------------

if __name__ == "__main__":
    
    if EXPERIMENTER_MODE and platform.system() == "Windows":
        if not is_admin():
            relaunch_as_admin()

        # Register cleanup handlers BEFORE entering experiment mode
        _register_cleanup_handlers()

        print_system_state("INITIAL SYSTEM STATE")

        print("\n" + "=" * NUM_EQUALS, flush = True)
        print(f"EXPERIMENT MODE ACTIVATION", flush = True)
        print("=" * NUM_EQUALS + "\n", flush = True)
        print("Enabling experiment mode...", flush = True)
        run_powershell(ENTER_SCRIPT)
        _experiment_mode_active = True  # Mark that we need cleanup on exit
        print("=" * NUM_EQUALS, flush = True)
        print("=" * NUM_EQUALS + "\n\n", flush = True)

        print_system_state("STATE AFTER ENTERING EXPERIMENT MODE")

        decision = show_mode_popup()

        if decision == "quit":
            print("\n" + "=" * NUM_EQUALS, flush = True)
            print(f"EXPERIMENT MODE DEACTIVATION", flush = True)
            print("=" * NUM_EQUALS + "\n", flush = True)
            print("Restoring system...", flush = True)
            run_powershell(EXIT_SCRIPT)
            _cleanup_done = True  # Mark cleanup as done
            _experiment_mode_active = False
            print("=" * NUM_EQUALS, flush = True)
            print("=" * NUM_EQUALS + "\n\n", flush = True)
            print_system_state("FINAL SYSTEM STATE AFTER RESTORE")
            show_disabled_popup()
            print("Done.", flush = True)
            input("\nPress Enter to close this window...\n\n")
            sys.exit()

        try:
            print("\n" + "=" * NUM_EQUALS, flush = True)
            print(f"EXPERIMENT LOGS", flush = True)
            print("=" * NUM_EQUALS + "\n", flush = True)

            # Runs the actual experiment
            subprocess.run([sys.executable, EXPERIMENT])

            print("=" * NUM_EQUALS, flush = True)
            print("=" * NUM_EQUALS + "\n", flush = True)
        finally:
            if not _cleanup_done:
                print("\n\n" + "=" * NUM_EQUALS, flush = True)
                print(f"EXPERIMENT MODE DEACTIVATION", flush = True)
                print("=" * NUM_EQUALS + "\n", flush = True)
                print("Restoring system...", flush = True)
                run_powershell(EXIT_SCRIPT)
                _cleanup_done = True
                _experiment_mode_active = False
                print("=" * NUM_EQUALS, flush = True)
                print("=" * NUM_EQUALS + "\n\n", flush = True)
                print_system_state("FINAL SYSTEM STATE AFTER RESTORE")
                show_disabled_popup()

        print("Done.", flush = True)
        input("\nPress Enter to close this window...\n\n")
    else:
        # Lazy import to avoid GUI side effects at module load time
        from main_experimental_flow import main as run_experiment
        run_experiment()
