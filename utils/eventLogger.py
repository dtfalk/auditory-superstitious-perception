"""
Event Logger Utility
====================
Provides centralized event logging for all experiment screens.

Usage:
    logger = EventLogger(save_folder, subject_number)
    logger.log_experiment_start()
    
    # For each screen:
    screen_logger = logger.start_screen('examples_screen')
    screen_logger.log_event('button_click', 'actual_audio')
    screen_logger.log_event('button_click', 'target_0')
    screen_logger.save()
    
    logger.log_experiment_end()
"""

import os
import csv
import time
from typing import Optional


class ScreenEventLogger:
    """Logger for a single screen's events."""
    
    def __init__(self, screen_name: str, save_folder: str, subject_number: str):
        self.screen_name = screen_name
        self.subject_number = subject_number
        # Use timestamps subfolder
        self.timestamps_folder = os.path.join(save_folder, f"timestamps_{subject_number}")
        self.screen_presented_ns = time.perf_counter_ns()
        self.events: list[tuple[str, int]] = []  # (event_description, timestamp_ns)
    
    def log_event(self, event_type: str, event_detail: str = "") -> None:
        """Log an event with the current perf_counter_ns timestamp."""
        timestamp_ns = time.perf_counter_ns()
        if event_detail:
            event_desc = f"{event_type}:{event_detail}"
        else:
            event_desc = event_type
        self.events.append((event_desc, timestamp_ns))
    
    def save(self) -> None:
        """Save the screen's event log to a CSV file."""
        # Ensure timestamps directory exists
        os.makedirs(self.timestamps_folder, exist_ok=True)
        
        filename = f'events_{self.screen_name}_{self.subject_number}.csv'
        filepath = os.path.join(self.timestamps_folder, filename)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Event', 'Timestamp_ns', 'ms_since_last', 's_since_last'])
            
            # Screen presented is the first event (no previous event)
            writer.writerow(['screen_presented', self.screen_presented_ns, 0, 0.0])
            
            prev_ts = self.screen_presented_ns
            for event_desc, ts in self.events:
                delta_ns = ts - prev_ts
                ms_since_last = delta_ns / 1_000_000
                s_since_last = delta_ns / 1_000_000_000
                writer.writerow([event_desc, ts, f'{ms_since_last:.3f}', f'{s_since_last:.6f}'])
                prev_ts = ts


class EventLogger:
    """
    Central event logger for the entire experiment.
    
    Tracks experiment-level timestamps and creates per-screen loggers.
    """
    
    def __init__(self, save_folder: str, subject_number: str):
        self.save_folder = save_folder
        self.subject_number = subject_number
        # Use timestamps subfolder
        self.timestamps_folder = os.path.join(save_folder, f"timestamps_{subject_number}")
        self.experiment_start_ns: Optional[int] = None
        self.experiment_end_ns: Optional[int] = None
        self._screen_counter: dict[str, int] = {}  # Track multiple instances of same screen
    
    def log_experiment_start(self) -> None:
        """Log the experiment start timestamp."""
        self.experiment_start_ns = time.perf_counter_ns()
    
    def log_experiment_end(self) -> None:
        """Log the experiment end timestamp and save timestamps file."""
        self.experiment_end_ns = time.perf_counter_ns()
        self._save_experiment_timestamps()
    
    def _save_experiment_timestamps(self) -> None:
        """Save experiment-level timestamps to a CSV file."""
        os.makedirs(self.timestamps_folder, exist_ok=True)
        
        filepath = os.path.join(self.timestamps_folder, f'experiment_timestamps_{self.subject_number}.csv')
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Event', 'Timestamp_ns', 'ms_since_last', 's_since_last'])
            
            prev_ts = None
            if self.experiment_start_ns is not None:
                writer.writerow(['experiment_start', self.experiment_start_ns, 0, 0.0])
                prev_ts = self.experiment_start_ns
            if self.experiment_end_ns is not None:
                if prev_ts is not None:
                    delta_ns = self.experiment_end_ns - prev_ts
                    ms_since_last = delta_ns / 1_000_000
                    s_since_last = delta_ns / 1_000_000_000
                    writer.writerow(['experiment_end', self.experiment_end_ns, f'{ms_since_last:.3f}', f'{s_since_last:.6f}'])
                else:
                    writer.writerow(['experiment_end', self.experiment_end_ns, 0, 0.0])
    
    def start_screen(self, screen_name: str, unique_suffix: str = "") -> ScreenEventLogger:
        """
        Create a new screen event logger.
        
        Args:
            screen_name: Base name for the screen (e.g., 'examples_screen')
            unique_suffix: Optional suffix for disambiguation (e.g., 'block1')
        
        Returns:
            ScreenEventLogger instance for the screen
        """
        # Build full screen name
        if unique_suffix:
            full_name = f"{screen_name}_{unique_suffix}"
        else:
            # Auto-increment if same screen name used multiple times
            if screen_name in self._screen_counter:
                self._screen_counter[screen_name] += 1
                full_name = f"{screen_name}_{self._screen_counter[screen_name]}"
            else:
                self._screen_counter[screen_name] = 1
                full_name = screen_name
        
        return ScreenEventLogger(full_name, self.save_folder, self.subject_number)


# Global logger instance (set during experiment setup)
_global_logger: Optional[EventLogger] = None


def init_global_logger(save_folder: str, subject_number: str) -> EventLogger:
    """Initialize the global event logger."""
    global _global_logger
    _global_logger = EventLogger(save_folder, subject_number)
    return _global_logger


def get_global_logger() -> Optional[EventLogger]:
    """Get the global event logger instance."""
    return _global_logger


def start_screen_log(screen_name: str, unique_suffix: str = "") -> Optional[ScreenEventLogger]:
    """Convenience function to start a screen log using the global logger."""
    if _global_logger is None:
        return None
    return _global_logger.start_screen(screen_name, unique_suffix)
