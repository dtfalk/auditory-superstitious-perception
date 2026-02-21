import os
import subprocess
import sys
import json
import ctypes
if sys.platform == "win32":
    from ctypes import wintypes
import atexit
import platform
import threading
import time
import tkinter as tk
from tkinter import messagebox
import psutil
import csv
import shutil
import io

# Turns off various windows things so experiment is not interrupted or slowed
EXPERIMENTER_MODE = True

CUR_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(CUR_DIR)

ENTER_SCRIPT = os.path.join(CUR_DIR, "experimenter_mode_scripts", "enterExperimentMode.ps1")
EXIT_SCRIPT = os.path.join(CUR_DIR, "experimenter_mode_scripts", "exitExperimentMode.ps1")
EXPERIMENT = os.path.join(CUR_DIR, "main_experimental_flow.py")
LAST_RUN_METADATA = os.path.join(CUR_DIR, ".last_experiment_run.json")

NUM_EQUALS = 75
RESULTS_DIR = os.path.join(CUR_DIR, "results")
DEIDENTIFIED_DIR = os.path.join(CUR_DIR, "results_deidentified")

# -------------------------
# Console Logger (captures all output to file)
# -------------------------

class TeeLogger:
    """Captures stdout/stderr to both console and a buffer for later saving."""
    
    def __init__(self, original_stream):
        self._original = original_stream
        self._buffer = io.StringIO()
        self._encoding = getattr(original_stream, 'encoding', 'utf-8')
    
    def write(self, text):
        self._original.write(text)
        self._buffer.write(text)
    
    def flush(self):
        self._original.flush()
    
    def get_contents(self):
        return self._buffer.getvalue()
    
    def save_to_file(self, filepath):
        """Save captured output to a file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self._buffer.getvalue())

_stdout_logger = None
_stderr_logger = None

def start_logging():
    """Start capturing stdout and stderr."""
    global _stdout_logger, _stderr_logger
    _stdout_logger = TeeLogger(sys.stdout)
    _stderr_logger = TeeLogger(sys.stderr)
    sys.stdout = _stdout_logger
    sys.stderr = _stderr_logger

def save_console_log(filepath):
    """Save captured console output to file."""
    global _stdout_logger
    if _stdout_logger is not None:
        _stdout_logger.save_to_file(filepath)
        return True
    return False


def run_subprocess_logged(cmd, shell=False):
    """
    Run a subprocess and stream its output through our logger.
    Returns the process return code.
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=shell,
        bufsize=1  # Line buffered
    )
    
    # Stream output line by line
    for line in process.stdout:
        print(line, end='', flush=True)
    
    process.wait()
    return process.returncode


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

if sys.platform == "win32":
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
if sys.platform == "win32":
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
    returncode = run_subprocess_logged([
        "powershell",
        "-ExecutionPolicy", "Bypass",
        "-File", script_path
    ])

    if returncode != 0:
        print(f"PowerShell exited with code {returncode}", flush = True)

    return returncode


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

    run_subprocess_logged([
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

    run_subprocess_logged([
        "powershell",
        "-Command",
        "powercfg -getactivescheme"
    ])
    print("\n" + "=" * NUM_EQUALS, flush = True)
    print("=" * NUM_EQUALS + "\n\n", flush = True)


# -------------------------
# System Resource Monitor
# -------------------------

MONITOR_INTERVAL_SEC = 10  # Sample every 10 seconds (very low overhead)

class SystemMonitor:
    """Lightweight background monitor for CPU, RAM, and disk usage."""

    def __init__(self, interval=MONITOR_INTERVAL_SEC):
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = None
        self._end_time = None

        # Sample storage
        self._cpu_samples = []       # percent
        self._ram_samples = []       # (used_bytes, percent)
        self._disk_samples = []      # (busy_pct, read_bytes_per_sec, write_bytes_per_sec)

        # Static info captured at start
        self._ram_total = None

        # Previous disk I/O snapshot for delta computation
        self._prev_disk_io = None
        self._prev_disk_time = None

    def start(self):
        mem = psutil.virtual_memory()
        self._ram_total = mem.total

        # Prime cpu_percent so first real sample is meaningful
        psutil.cpu_percent(interval=None)

        # Prime disk I/O counters so first delta is meaningful
        try:
            self._prev_disk_io = psutil.disk_io_counters()
        except Exception:
            self._prev_disk_io = None
        self._prev_disk_time = time.time()

        self._start_time = time.time()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 2)
        self._end_time = time.time()

    def _sample_loop(self):
        while not self._stop_event.is_set():
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()

                self._cpu_samples.append(cpu)
                self._ram_samples.append((mem.used, mem.percent))

                # Compute disk I/O activity from deltas
                now = time.time()
                cur_io = psutil.disk_io_counters()
                if cur_io is not None and self._prev_disk_io is not None:
                    dt = now - self._prev_disk_time
                    if dt > 0:
                        # Timing-based busy % (read_time + write_time are ms).
                        # On some Windows systems (especially NVMe/SSD) these
                        # fields are always 0.  Fall back to an IOPS-based
                        # heuristic when that happens.
                        io_ms = ((cur_io.read_time - self._prev_disk_io.read_time)
                                 + (cur_io.write_time - self._prev_disk_io.write_time))

                        if io_ms > 0:
                            busy_pct = min(100.0, (io_ms / (dt * 1000)) * 100)
                        else:
                            # Timing data unavailable — estimate from IOPS.
                            # Assume each I/O op takes ~0.1 ms on a fast SSD.
                            delta_ops = ((cur_io.read_count - self._prev_disk_io.read_count)
                                         + (cur_io.write_count - self._prev_disk_io.write_count))
                            estimated_ms = delta_ops * 0.1
                            busy_pct = min(100.0, (estimated_ms / (dt * 1000)) * 100)

                        read_bps = (cur_io.read_bytes - self._prev_disk_io.read_bytes) / dt
                        write_bps = (cur_io.write_bytes - self._prev_disk_io.write_bytes) / dt

                        self._disk_samples.append((busy_pct, read_bps, write_bps))

                if cur_io is not None:
                    self._prev_disk_io = cur_io
                    self._prev_disk_time = now
            except Exception:
                pass  # Never interrupt the experiment

            self._stop_event.wait(self._interval)

    @staticmethod
    def _fmt_bytes(b):
        """Format bytes to a human-readable string with appropriate unit."""
        if b >= 1024 ** 3:
            return f"{b / (1024 ** 3):.2f} GB"
        elif b >= 1024 ** 2:
            return f"{b / (1024 ** 2):.1f} MB"
        elif b >= 1024:
            return f"{b / 1024:.0f} KB"
        return f"{b} B"

    @staticmethod
    def _fmt_rate(bps):
        """Format bytes/sec to a human-readable throughput string."""
        if bps >= 1024 ** 3:
            return f"{bps / (1024 ** 3):.2f} GB/s"
        elif bps >= 1024 ** 2:
            return f"{bps / (1024 ** 2):.1f} MB/s"
        elif bps >= 1024:
            return f"{bps / 1024:.0f} KB/s"
        return f"{bps:.0f} B/s"

    def print_summary(self):
        n = len(self._cpu_samples)
        if n == 0:
            print("No resource samples were collected.", flush=True)
            return

        duration = (self._end_time or time.time()) - self._start_time
        mins, secs = divmod(int(duration), 60)

        cpu_vals = self._cpu_samples
        ram_bytes = [s[0] for s in self._ram_samples]
        ram_pcts  = [s[1] for s in self._ram_samples]

        cpu_min, cpu_max, cpu_avg = min(cpu_vals), max(cpu_vals), sum(cpu_vals) / n
        ram_b_min, ram_b_max, ram_b_avg = min(ram_bytes), max(ram_bytes), sum(ram_bytes) / n
        ram_p_min, ram_p_max, ram_p_avg = min(ram_pcts), max(ram_pcts), sum(ram_pcts) / n

        print(f"  Monitoring Duration:  {mins} min {secs:02d} sec  ({n} samples @ {self._interval}s interval)", flush=True)
        print("", flush=True)

        print(f"  CPU Usage:", flush=True)
        print(f"    Min:  {cpu_min:6.1f}%", flush=True)
        print(f"    Max:  {cpu_max:6.1f}%", flush=True)
        print(f"    Avg:  {cpu_avg:6.1f}%", flush=True)
        print("", flush=True)

        rt = self._fmt_bytes(self._ram_total)
        print(f"  RAM Usage:  (Total: {rt})", flush=True)
        print(f"    Min:  {self._fmt_bytes(ram_b_min):>10s}  ({ram_p_min:5.1f}%)", flush=True)
        print(f"    Max:  {self._fmt_bytes(ram_b_max):>10s}  ({ram_p_max:5.1f}%)", flush=True)
        print(f"    Avg:  {self._fmt_bytes(ram_b_avg):>10s}  ({ram_p_avg:5.1f}%)", flush=True)

        dn = len(self._disk_samples)
        if dn > 0:
            dsk_busy = [s[0] for s in self._disk_samples]
            dsk_read = [s[1] for s in self._disk_samples]
            dsk_write = [s[2] for s in self._disk_samples]

            db_min, db_max, db_avg = min(dsk_busy), max(dsk_busy), sum(dsk_busy) / dn
            dr_min, dr_max, dr_avg = min(dsk_read), max(dsk_read), sum(dsk_read) / dn
            dw_min, dw_max, dw_avg = min(dsk_write), max(dsk_write), sum(dsk_write) / dn

            print("", flush=True)
            print(f"  Disk Activity (I/O Busy %):", flush=True)
            print(f"    Min:  {db_min:6.1f}%", flush=True)
            print(f"    Max:  {db_max:6.1f}%", flush=True)
            print(f"    Avg:  {db_avg:6.1f}%", flush=True)
            print("", flush=True)
            print(f"  Disk Read Throughput:", flush=True)
            print(f"    Min:  {self._fmt_rate(dr_min):>12s}", flush=True)
            print(f"    Max:  {self._fmt_rate(dr_max):>12s}", flush=True)
            print(f"    Avg:  {self._fmt_rate(dr_avg):>12s}", flush=True)
            print("", flush=True)
            print(f"  Disk Write Throughput:", flush=True)
            print(f"    Min:  {self._fmt_rate(dw_min):>12s}", flush=True)
            print(f"    Max:  {self._fmt_rate(dw_max):>12s}", flush=True)
            print(f"    Avg:  {self._fmt_rate(dw_avg):>12s}", flush=True)


# -------------------------
# Summary Statistics Display
# -------------------------

def display_summary_statistics(subject_number):
    """Display summary statistics for the current subject if available."""
    summary_file = os.path.join(RESULTS_DIR, str(subject_number), f"summary_data_{subject_number}.csv")
    
    if not os.path.exists(summary_file):
        print(f"No summary statistics found for subject {subject_number}.", flush=True)
        return False
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if len(rows) < 2:
            print(f"  Summary file exists but contains no data.", flush=True)
            return False
        
        headers = rows[0]
        data = rows[1]
        
        print(f"  Subject: {subject_number}", flush=True)
        print("", flush=True)
        
        # Display each column
        for i, (header, value) in enumerate(zip(headers, data)):
            if header.lower() != "subject number":
                print(f"    {header}: {value}", flush=True)
        
        return True
    except Exception as e:
        print(f"  Error reading summary statistics: {e}", flush=True)
        return False


# -------------------------
# Deidentified Results Folder
# -------------------------

def create_deidentified_results():
    """
    Create a copy of the results folder without consent files.
    Copies all files except consent_{subject_number}.csv for each subject.
    """
    if not os.path.exists(RESULTS_DIR):
        print("  No results folder found to deidentify.", flush=True)
        return False
    
    try:
        # Remove existing deidentified folder if it exists
        if os.path.exists(DEIDENTIFIED_DIR):
            shutil.rmtree(DEIDENTIFIED_DIR)
        
        # Walk through results and copy everything except consent files
        for root, dirs, files in os.walk(RESULTS_DIR):
            # Compute relative path from RESULTS_DIR
            rel_path = os.path.relpath(root, RESULTS_DIR)
            dest_dir = os.path.join(DEIDENTIFIED_DIR, rel_path) if rel_path != "." else DEIDENTIFIED_DIR
            
            # Create destination directory
            os.makedirs(dest_dir, exist_ok=True)
            
            for file in files:
                # Skip consent files (consent_{subject_number}.csv)
                if file.startswith("consent_") and file.endswith(".csv"):
                    continue
                
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, file)
                shutil.copy2(src_file, dst_file)
        
        return True
    except Exception as e:
        print(f"  Error creating deidentified folder: {e}", flush=True)
        return False


# -------------------------
# Main Flow
# -------------------------

if __name__ == "__main__":
    
    if EXPERIMENTER_MODE and platform.system() == "Windows":
        if not is_admin():
            relaunch_as_admin()

        # Start console logging to capture all output
        start_logging()

        # Register cleanup handlers BEFORE entering experiment mode
        _register_cleanup_handlers()

        print_system_state("INITIAL SYSTEM STATE")

        print("\n" + "=" * NUM_EQUALS, flush = True)
        print(f"EXPERIMENT MODE ACTIVATION", flush = True)
        print("=" * NUM_EQUALS + "\n", flush = True)
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
            run_powershell(EXIT_SCRIPT)
            _cleanup_done = True  # Mark cleanup as done
            _experiment_mode_active = False
            print("=" * NUM_EQUALS, flush = True)
            print("=" * NUM_EQUALS + "\n\n", flush = True)
            print_system_state("FINAL SYSTEM STATE AFTER RESTORE")
            show_disabled_popup()
            print("Done.", flush = True)
            input("\nReview logs above or press Enter to complete the experiment...\n\n")
            sys.exit()

        try:
            print("\n" + "=" * NUM_EQUALS, flush = True)
            print(f"EXPERIMENT LOGS", flush = True)
            print("=" * NUM_EQUALS + "\n", flush = True)

            try:
                if os.path.exists(LAST_RUN_METADATA):
                    os.remove(LAST_RUN_METADATA)
            except Exception:
                pass

            # Start lightweight background resource monitor
            monitor = SystemMonitor()
            monitor.start()

            # Runs the actual experiment
            # NOTE: Running as subprocess is fine for priority. The child process
            # inherits the parent's priority class, and the parent is essentially
            # idle (blocked on subprocess.run) so it does not compete for CPU.
            experiment_returncode = run_subprocess_logged([sys.executable, EXPERIMENT])

            # Stop monitor and print summary before closing experiment logs
            monitor.stop()

            print("=" * NUM_EQUALS, flush = True)
            print("=" * NUM_EQUALS + "\n\n", flush = True)

            print("\n" + "=" * NUM_EQUALS, flush = True)
            print(f"SYSTEM RESOURCE USAGE DURING EXPERIMENT", flush = True)
            print("=" * NUM_EQUALS + "\n", flush = True)
            monitor.print_summary()
            print("=" * NUM_EQUALS, flush = True)
            print("=" * NUM_EQUALS + "\n", flush = True)
        finally:
            if not _cleanup_done:
                print("\n\n" + "=" * NUM_EQUALS, flush = True)
                print(f"EXPERIMENT MODE DEACTIVATION", flush = True)
                print("=" * NUM_EQUALS + "\n", flush = True)
                run_powershell(EXIT_SCRIPT)
                _cleanup_done = True
                _experiment_mode_active = False
                print("=" * NUM_EQUALS, flush = True)
                print("=" * NUM_EQUALS + "\n\n", flush = True)
                print_system_state("FINAL SYSTEM STATE AFTER RESTORE")
                show_disabled_popup()

        if experiment_returncode != 0:
            print(f"Experiment process exited with code {experiment_returncode}", flush=True)

        save_folder = None
        subject_number = None
        try:
            if os.path.exists(LAST_RUN_METADATA):
                with open(LAST_RUN_METADATA, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                subject_number = metadata.get("subject_number")
                save_folder = metadata.get("save_folder")
        except Exception as e:
            print(f"Could not read run metadata: {e}", flush=True)

        # Display subject summary statistics
        if subject_number:
            print("\n" + "=" * NUM_EQUALS, flush=True)
            print(f"SUBJECT SUMMARY STATISTICS", flush=True)
            print("=" * NUM_EQUALS + "\n", flush=True)
            display_summary_statistics(subject_number)
            print("\n" + "=" * NUM_EQUALS, flush=True)
            print("=" * NUM_EQUALS, flush=True)

        # Create deidentified results folder
        print("\n" + "=" * NUM_EQUALS, flush=True)
        print(f"CREATING DEIDENTIFIED DATA FOLDER", flush=True)
        print("=" * NUM_EQUALS + "\n", flush=True)
        if create_deidentified_results():
            print(f"Created deidentified data folder.", flush=True)
        print("\n" + "=" * NUM_EQUALS, flush=True)
        print("=" * NUM_EQUALS, flush=True)

        print("\n" + "-" * NUM_EQUALS, flush=True)
        if subject_number and save_folder:
            print(f"Subject {subject_number} results stored in:\n  {save_folder}", flush=True)
        else:
            print("No results folder recorded for this run.", flush=True)
        print("-" * NUM_EQUALS, flush=True)

        print("\n" + "-" * NUM_EQUALS, flush=True)
        print(f"Deidentified results folder:\n  {DEIDENTIFIED_DIR}", flush=True)
        print("-" * NUM_EQUALS, flush=True)

        # Save console log to subject's folder before final prompt
        if subject_number and save_folder:
            console_log_path = os.path.join(save_folder, f"console_log_{subject_number}.txt")
            if save_console_log(console_log_path):
                print(f"\nConsole log saved to:\n  {console_log_path}", flush=True)
            
            # Also copy console log to deidentified folder
            deidentified_subject_folder = os.path.join(DEIDENTIFIED_DIR, str(subject_number))
            if os.path.exists(deidentified_subject_folder):
                deidentified_log_path = os.path.join(deidentified_subject_folder, f"console_log_{subject_number}.txt")
                try:
                    shutil.copy2(console_log_path, deidentified_log_path)
                    print(f"Console log also saved to deidentified folder.", flush=True)
                except Exception as e:
                    print(f"Could not copy console log to deidentified folder: {e}", flush=True)

        input("\nReview logs above or press Enter to complete the experiment...\n\n")
    else:
        # Lazy import to avoid GUI side effects at module load time
        from main_experimental_flow import main as run_experiment
        run_experiment()
