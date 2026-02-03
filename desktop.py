"""
Backlogia Desktop Launcher

Starts the FastAPI server in a background thread and displays it in a native window.
"""

import socket
import threading
import time
import sys

try:
    import webview
except ImportError:
    print("[FAIL] PyWebView is not installed.")
    print("Please install it with: pip install pywebview")
    sys.exit(1)

try:
    import uvicorn
except ImportError:
    print("[FAIL] Uvicorn is not installed.")
    print("Please install it with: pip install uvicorn")
    sys.exit(1)


class SingleInstance:
    """Ensure only one instance of the application is running."""

    def __init__(self, name="backlogia"):
        """Initialize single instance lock using a socket."""
        self.name = name
        self.socket = None
        self.locked = False

    def acquire(self):
        """Try to acquire the lock. Returns True if successful."""
        try:
            # Use an abstract Unix socket on Unix, or a TCP socket on Windows
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Bind to localhost with a specific port for this app
            self.socket.bind(('127.0.0.1', 47777))  # Random high port
            self.socket.listen(1)
            self.locked = True
            return True
        except OSError:
            # Port is already in use, another instance is running
            return False

    def release(self):
        """Release the lock."""
        if self.locked and self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.locked = False

    def __enter__(self):
        """Context manager entry."""
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


def find_free_port(start_port=8000, max_attempts=100):
    """Find an available port starting from start_port.
    
    Args:
        start_port: Port number to start searching from
        max_attempts: Maximum number of ports to try
        
    Returns:
        int: Available port number
        
    Raises:
        RuntimeError: If no free port is found in the range
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"Could not find a free port in range {start_port}-{start_port + max_attempts}. "
        f"Please close some applications and try again."
    )


def run_server(port):
    """Run the FastAPI server in a background thread.
    
    Args:
        port: Port number to bind the server to
    """
    try:
        from web.main import app

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",  # Reduce console noise
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"[FAIL] Server error: {e}")
        # Thread will terminate, main thread will detect startup failure


def main():
    """Launch the desktop application."""
    # Check for single instance
    instance_lock = SingleInstance()
    if not instance_lock.acquire():
        print("[INFO] Another instance of Backlogia is already running.")
        print("[INFO] Please close the existing instance or use that window.")

        # Wait a bit so user can see the message if launched from terminal
        if not getattr(sys, 'frozen', False):
            time.sleep(3)
        sys.exit(0)

    try:
        # Redirect stdout/stderr to a log file in frozen mode
        if getattr(sys, 'frozen', False):
            from web.config import get_data_dir
            log_dir = get_data_dir() / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"backlogia_{time.strftime('%Y%m%d_%H%M%S')}.log"

            # Keep old file handles for emergencies
            sys.stdout = open(log_file, 'w', encoding='utf-8')
            sys.stderr = sys.stdout

        # Show data directory info on first run or in debug mode
        from web.config import get_data_dir
        data_dir = get_data_dir()
        print(f"[OK] Data directory: {data_dir}")

        # Find an available port
        port = find_free_port()
        url = f"http://127.0.0.1:{port}"
        loading_url = f"{url}/loading"

        print(f"[OK] Starting Backlogia on port {port}...")

        # Start FastAPI server in a background thread FIRST
        server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
        server_thread.start()

        # Wait for server to be ready before creating window
        max_wait = 10  # seconds
        start_time = time.time()
        server_ready = False

        print("[OK] Waiting for server to start...")
        while time.time() - start_time < max_wait:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(("127.0.0.1", port))
                    server_ready = True
                    break
            except (ConnectionRefusedError, OSError):
                time.sleep(0.1)

        if not server_ready:
            print(f"[FAIL] Server failed to start within {max_wait} seconds")
            sys.exit(1)

        print("[OK] Server ready, opening window...")

        # Create window with loading URL (server is already running)
        window = webview.create_window(
            title="Backlogia",
            url=loading_url,
            width=1280,
            height=800,
            resizable=True,
            min_size=(800, 600),
        )

        # Try to create system tray icon (optional feature)
        tray_icon = None
        try:
            from tray_icon import create_tray_icon, run_tray_icon, stop_tray_icon, TRAY_AVAILABLE

            if TRAY_AVAILABLE:
                def on_quit():
                    """Quit from tray menu."""
                    try:
                        window.destroy()
                    except:
                        pass
                    sys.exit(0)

                tray_icon = create_tray_icon(on_quit_callback=on_quit)

                if tray_icon:
                    # Run tray in background thread
                    tray_thread = threading.Thread(target=run_tray_icon, args=(tray_icon,), daemon=True)
                    tray_thread.start()
                    print("[OK] System tray icon enabled")
        except ImportError:
            print("[INFO] System tray not available (pystray not installed)")
        except Exception as e:
            print(f"[WARN] Could not create system tray icon: {e}")

        # Start the webview (this blocks until window closes)
        # The loading page will auto-redirect to / once fully ready
        webview.start(debug=False)

        # Clean up tray icon on exit
        if tray_icon:
            try:
                stop_tray_icon(tray_icon)
            except:
                pass

        print("[OK] Application closed")

    except RuntimeError as e:
        print(f"[FAIL] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[OK] Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
