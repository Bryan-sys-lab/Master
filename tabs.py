import subprocess
import math
import sys
import shutil
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
def screensize():
    """primary screen size in pixels. """
    try:
        output = subprocess.check_output(['xdpyinfo', '-display', ':0'], stderr=subprocess.STDOUT).decode()
        for line in output.decode().splitlines():
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
def open_windows():
    """all open windows and their IDs"""
    output =subprocess.check_output(['wmctrl', '-l']).decode()
    windows = []
    for line in output.strip().split('\n'):
        parts = line.split(None, 3)
        if len(parts) == 4:
            win_id, desktop, host, title = parts
            if title.strip()and not any(x in title.lower() for x in ['desktop', 'panel', 'dock', 'taskbar']):
                windows.append((win_id, title))
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
        for lin in output.splitlines():
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
    """Arrange all open windows in a grid layout."""
    windows = open_windows()
    if not windows:
        logging.info("No open windows found.")
        return

    #original gometry
    logging.info("original geometry:")
    for win_id, title in windows:
        geometry = get_window_geometry(win_id)
        if geometry:
            x, y, width, height = geometry
            logging.info(f"Window ID: {win_id}, Title: {title}, Geometry: ({x}, {y}, {width}, {height})")
        else:
            logging.error(f"Could not get geometry for window ID: {win_id}")

    cols = math.ceil(math.sqrt(len(windows)))
    rows = math.ceil(len(windows) / cols)
    tab_width, tab_height = tabsize(cols,rows)

    for i, (win_id, title) in enumerate(windows):
        x = (i % cols) * tab_width
        y = (i // cols) * tab_height
        move_resize(win_id, x, y, tab_width, tab_height)
    logging.info(f"Arranged {len(windows)} windows in a {cols}x{rows} grid layout.")

def main():
    """Main function to arrange windows."""
    if shutil.which('wmctrl') is None:
        logging.error("wmctrl command not found. Please install wmctrl.")
        sys.exit(1)
    if shutil.which('xwininfo') is None:
        logging.error("xwininfo command not found. Please install xwininfo.")
        sys.exit(1)
    if len(sys.argv) < 2:
        print("Usage: python3 tabs.py [arrange|geometry|list|test]")
        sys.exit(1)
    logging.info("""Starting tabs manager..
        press Ctrl+C to stop the background manager.""")
    try:
        while True:
            arrange_windows()
            time.sleep(10)  # Arrange every 10 seconds
    except KeyboardInterrupt:
        logging.info("Tabs manager stopped.")
        sys.exit(0)
if __name__ == "__main__":
    main()
