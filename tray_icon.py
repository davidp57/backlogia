"""
System tray integration for Backlogia desktop app.
Optional feature - if pystray is not installed, app works without tray icon.
"""

from pathlib import Path

# Try to import pystray - it's optional
try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


def create_tray_icon(on_quit_callback, on_show_callback=None):
    """
    Create a system tray icon for the application.
    
    Args:
        on_quit_callback: Function to call when user quits from tray
        on_show_callback: Optional function to call when user clicks "Show"
        
    Returns:
        Icon object or None if pystray is not available
    """
    if not TRAY_AVAILABLE:
        return None

    # Create a simple icon image
    icon_path = Path(__file__).parent / "icon.png"

    if icon_path.exists():
        image = Image.open(icon_path)
    else:
        # Create a simple fallback icon
        image = Image.new('RGB', (64, 64), color=(102, 126, 234))

    # Resize for tray (typically 16x16 or 32x32)
    image = image.resize((32, 32), Image.Resampling.LANCZOS)

    # Create menu
    menu_items = []

    if on_show_callback:
        menu_items.extend([
            MenuItem('Show Window', on_show_callback),
            Menu.SEPARATOR
        ])

    menu_items.append(MenuItem('Quit', on_quit_callback))

    # Create icon
    icon = Icon(
        name="Backlogia",
        icon=image,
        title="Backlogia",
        menu=Menu(*menu_items)
    )

    return icon


def run_tray_icon(icon):
    """
    Run the tray icon in a separate thread.
    
    Args:
        icon: Icon object from create_tray_icon()
    """
    if icon and TRAY_AVAILABLE:
        icon.run()


def stop_tray_icon(icon):
    """
    Stop the tray icon.
    
    Args:
        icon: Icon object from create_tray_icon()
    """
    if icon and TRAY_AVAILABLE:
        try:
            icon.stop()
        except:
            pass
