# screenInfo.py
# Prepares the experimental screen and grabs the monitor's width and height
from os import environ
from screeninfo import get_monitors
    
def prepareExperimentalScreen(monitorSizeOrdinal: int = 0) -> tuple[int, int]:
    """
    Prepares experimental screen by choosing experimental screen and returning the monitor's width and height.

    If (monitorSizeOrdinal - 1) exceeds list length or no argument is provided,
    then display the experiment on the largest monitor
    
    Args:
        monitorSizeOrdinal: 1-indexed monitor index in ranked ascending order by monitor size
    
    Returns:
        (WIN_WIDTH, WIN_HEIGHT): width and height of selected monitor
    """

    # Get screen info for each recognized, connected monitor
    monitor_list = get_monitors()
    num_monitors = len(monitor_list)

    # Ensure ordinal is valid and handle default value
    if monitorSizeOrdinal > num_monitors:
        monitorSizeOrdinal = num_monitors

    # Choose the monitor
    selected_monitor = monitor_list[monitorSizeOrdinal - 1]

    # Extract screen location
    winX, winY = selected_monitor.x, selected_monitor.y
    WIN_WIDTH, WIN_HEIGHT = selected_monitor.width, selected_monitor.height

    # Set env var with screen location
    environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (winX, winY)

    # Return monitor's width and height
    return WIN_WIDTH, WIN_HEIGHT