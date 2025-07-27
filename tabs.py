import subprocess
import math
import sys
import shutil
import logging
import time
prev_window_state = {}


logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
def screensize():
    """primary screen size in pixels. """
    try:
        output = subprocess.check_output(['xdpyinfo', '-display', ':0'], stderr=subprocess.STDOUT).decode()
        for line in output.splitlines():
            if 'dimensions:' in line:
                parts = line.split()
                width, height = map(int, parts[1].split('x'))
                return width, height
    except subprocess.CalledProcessError:
        return 1920, 1080   # Default to 1920x1080 if xrandr fails
    except FileNotFoundError:
        return 1920, 1080       
    except Exception as e:
        logging.error(f"Error retrieving screen size: {e}")
        return 1920, 1080   

def tabsize(cols,rows):
    """returns the size of a tab in pixels. """
    width, height = screensize()
    tab_width = math.floor(width / cols)
    tab_height = math.floor(height / rows)
    return tab_width, tab_height    

def is_minimized(window_id):
    """Check if a window is minimized."""
    try:
        output = subprocess.check_output(['xprop', '-id', window_id, '_NET_WM_STATE']).decode()
        return '_NET_WM_STATE_HIDDEN' in output or '_NET_WM_STATE_ICONIC' in output
    except subprocess.CalledProcessError:
        logging.error(f"Error checking minimized state for window {window_id}")
        return False
    except FileNotFoundError:
        logging.error("xprop command not found. Please install xprop.")
        return False
def is_maximized(window_id):
    try:
        output = subprocess.check_output(['xprop', '-id', window_id, '_NET_WM_STATE']).decode()
        return '_NET_WM_STATE_MAXIMIZED_HORZ' in output or '_NET_WM_STATE_MAXIMIZED_VERT' in output
    except subprocess.CalledProcessError:
        logging.error(f"Error checking maximized state for window {window_id}")
        return False
    except FileNotFoundError:
        logging.error("xprop command not found. Please install xprop.")
        return False

def get_window_type(window_id):
    try:
        output = subprocess.check_output(['xprop', '-id', window_id, '_NET_WM_WINDOW_TYPE']).decode()
        for line in output.splitlines():
            if '_NET_WM_WINDOW_TYPE' in line:
                return line.split()[-1].strip('"')
    except subprocess.CalledProcessError:
        logging.error(f"Error getting window type for {window_id}")
        return None

def open_windows():
    """all open windows and their IDs"""
    try:
        output =subprocess.check_output(['wmctrl', '-l']).decode()
    except subprocess.CalledProcessError:
        logging.error("Error retrieving open windows. Ensure wmctrl is installed.")
        return []
    except FileNotFoundError:
        logging.error("wmctrl command not found. Please install wmctrl.")
        return []
    
    windows = []
    for line in output.strip().split('\n'):
        parts = line.split(None,3)
        if len(parts) == 4:
            win_id,destop,host,title = parts
            if not title.strip():
                continue
            if is_minimized(win_id):
                logging.info(f"Skipping minimized window: {title} (ID: {win_id})")
                continue
            win_type = get_window_type(win_id)
            if win_type is not None and win_type != '_NET_WM_WINDOW_TYPE_NORMAL':
                logging.info(f"Skipping window of type {win_type}: {title} (ID: {win_id})")
                continue
            windows.append((win_id, title.strip()))
    return windows

def move_resize(window_id, x, y, width, height):
    """move and resize a window"""
    try:
        subprocess.check_call(['wmctrl', '-ir', window_id, '-e', f'0,{x},{y},{width},{height}'])

    except subprocess.CalledProcessError as e:
        logging.error(f"Error moving/resizing window {window_id}: {e}")
    except FileNotFoundError:
        logging.error("wmctrl command not found. Please install wmctrl.")

def get_window_size(window_id):
    """get the win size given its ID"""
    try:
        output = subprocess.check_output(['xwininfo', '-id', window_id]).decode()
        width =height = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith('Width:'):
                width = int(line.split(':')[1].strip())
            elif line.startswith('Height:'):
                height = int(line.split(':')[1].strip())
        if width is not None and height is not None:
            return width, height
        else:
            logging.warning(f"Could not determine size for window {window_id}")
            return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting window size for {window_id}: {e}")
        return None 
    except FileNotFoundError:
        logging.error("xwininfo command not found. Please install xwininfo.")
        return None 

def get_window_geometry(window_id):
    """Get the (x, y, width, height) of a window given its ID."""
    try:
        output = subprocess.check_output(['xwininfo', '-id', window_id]).decode()
        x = y = width = height = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith('Absolute upper-left X:'):
                x = int(line.split(':')[1].strip())
            elif line.startswith('Absolute upper-left Y:'):
                y = int(line.split(':')[1].strip())
            elif line.startswith('Width:'):
                width = int(line.split(':')[1].strip())
            elif line.startswith('Height:'):
                height = int(line.split(':')[1].strip())
        if None not in (x, y, width, height):
            return x, y, width, height
        else:
            logging.warning(f"Could not determine geometry for window {window_id}")
            return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting window geometry for {window_id}: {e}")
        return None
    except FileNotFoundError:
        logging.error("xwininfo command not found. Please install xwininfo.")
        return None

def arrange_windows():
    """Only arrange windows if any are added, removed, or moved (not maximized)."""
    global prev_window_state
    current_windows = open_windows()
    current_ids = [win_id for win_id, _ in current_windows]

    # Step 1: Detect new or closed windows
    if set(current_ids) != set(prev_window_state.keys()):
        logging.info("Window set changed — rearranging.")
        arrange_and_update_state(current_windows)
        return

    # Step 2: Check for any moved or resized (non-maximized) windows
    for win_id in current_ids:
        if is_maximized(win_id):
            continue  # Respect maximized windows
        geom = get_window_geometry(win_id)
        if not geom:
            continue
        if prev_window_state.get(win_id) != geom:
            logging.info(f"Window {win_id} moved/resized — rearranging.")
            arrange_and_update_state(current_windows)
            return

    logging.debug("No layout change needed.")
def arrange_and_update_state(windows):
    """Arrange windows and update their state."""
    global prev_window_state
    cols = math.ceil(math.sqrt(len(windows)))
    rows = math.ceil(len(windows) / cols)
    tab_width, tab_height = tabsize(cols, rows)

    new_state = {}
    for i, (win_id, title) in enumerate(windows):
        if is_maximized(win_id):
            logging.info(f"Skipping maximized window: {title} (ID: {win_id})")
            geom = get_window_geometry(win_id)
            if geom:
                new_state[win_id] = geom
            continue
        x = (i % cols) * tab_width
        y = (i // cols) * tab_height
        move_resize(win_id, x, y, tab_width, tab_height)
        new_state[win_id] = (x, y, tab_width, tab_height)

    prev_window_states = new_state
    logging.info(f"Updated layout of {len(windows)} windows.")


def main():
    """Main function to arrange windows."""
    if shutil.which('wmctrl') is None:
        logging.error("wmctrl command not found. Please install wmctrl.")
        sys.exit(1)
    if shutil.which('xwininfo') is None:
        logging.error("xwininfo command not found. Please install xwininfo.")
        sys.exit(1)
    logging.info("Starting tabs manager..press Ctrl+C to stop the background manager.")
    try:
        while True:
            arrange_windows()
            time.sleep(5)  # Arrange every 10 seconds
    except KeyboardInterrupt:
        logging.info("Tabs manager stopped.")
        sys.exit(0)
if __name__ == "__main__":
    main()
