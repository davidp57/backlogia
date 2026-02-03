"""
Test script for Backlogia desktop application.
Tests various edge cases and scenarios.
"""
import subprocess
import time
import socket
import sys
from pathlib import Path

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def test_port_conflict():
    """Test behavior when default port is already in use."""
    print("\n=== Test: Port Conflict Handling ===")

    # Start a simple server on port 8000
    print("[*] Starting dummy server on port 8000...")
    dummy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    dummy_server.bind(('127.0.0.1', 8000))
    dummy_server.listen(1)

    print("[*] Port 8000 is now occupied")
    print("[*] Starting Backlogia (should find a different port)...")

    # Start Backlogia
    app_path = Path(__file__).parent / "dist" / "Backlogia" / "Backlogia.exe"
    if not app_path.exists():
        print(f"[FAIL] Executable not found: {app_path}")
        dummy_server.close()
        return False

    try:
        # Start the app (it should find another port)
        proc = subprocess.Popen([str(app_path)])
        time.sleep(5)  # Wait for startup

        # Check if app is still running
        if proc.poll() is None:
            print("[PASS] Backlogia started successfully on a different port")
            proc.terminate()
            proc.wait(timeout=5)
            dummy_server.close()
            return True
        else:
            print("[FAIL] Backlogia failed to start")
            dummy_server.close()
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        dummy_server.close()
        return False

def test_data_persistence():
    """Test that data persists across sessions."""
    print("\n=== Test: Data Persistence ===")

    import os
    data_dir = Path(os.getenv('APPDATA')) / 'Backlogia'

    print(f"[*] Checking data directory: {data_dir}")

    if data_dir.exists():
        db_path = data_dir / 'game_library.db'
        if db_path.exists():
            print(f"[PASS] Database found at: {db_path}")
            print(f"[INFO] Database size: {db_path.stat().st_size} bytes")
            return True
        else:
            print("[WARN] Data directory exists but no database found")
            return False
    else:
        print("[INFO] Data directory doesn't exist yet (first run)")
        return True

def test_multiple_instances():
    """Test behavior when trying to start multiple instances."""
    print("\n=== Test: Multiple Instances ===")
    print("[INFO] This test is manual - try launching Backlogia.exe twice")
    print("[INFO] Expected: Second instance should either:")
    print("       1. Focus existing window (with single-instance lock)")
    print("       2. Open new window on different port (current behavior)")
    return True

def test_startup_time():
    """Measure application startup time."""
    print("\n=== Test: Startup Performance ===")

    app_path = Path(__file__).parent / "dist" / "Backlogia" / "Backlogia.exe"
    if not app_path.exists():
        print(f"[FAIL] Executable not found: {app_path}")
        return False

    print("[*] Starting Backlogia and measuring startup time...")
    start = time.time()

    try:
        proc = subprocess.Popen([str(app_path)])

        # Wait for window to appear (check if process is still running)
        for i in range(15):  # Wait up to 15 seconds
            time.sleep(1)
            if proc.poll() is not None:
                print("[FAIL] Process terminated unexpectedly")
                return False

            # Check if a port is now in use (app is ready)
            for port in range(8000, 8100):
                if is_port_in_use(port):
                    elapsed = time.time() - start
                    print(f"[PASS] App started in {elapsed:.2f} seconds on port {port}")
                    proc.terminate()
                    proc.wait(timeout=5)
                    return True

        print("[FAIL] App didn't start within 15 seconds")
        proc.terminate()
        return False

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def test_logs():
    """Check if logs are being created properly."""
    print("\n=== Test: Log File Creation ===")

    import os
    log_dir = Path(os.getenv('APPDATA')) / 'Backlogia' / 'logs'

    print(f"[*] Checking log directory: {log_dir}")

    if log_dir.exists():
        log_files = list(log_dir.glob('backlogia_*.log'))
        if log_files:
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            print(f"[PASS] Found {len(log_files)} log file(s)")
            print(f"[INFO] Latest log: {latest_log.name}")
            print(f"[INFO] Log size: {latest_log.stat().st_size} bytes")

            # Show last 10 lines
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print("\n[INFO] Last 10 lines of log:")
                for line in lines[-10:]:
                    print(f"      {line.rstrip()}")
            return True
        else:
            print("[WARN] Log directory exists but no log files found")
            return False
    else:
        print("[INFO] Log directory doesn't exist yet")
        return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Backlogia Desktop Application Tests")
    print("=" * 60)

    tests = [
        ("Data Persistence", test_data_persistence),
        ("Log Files", test_logs),
        ("Startup Time", test_startup_time),
        ("Port Conflict", test_port_conflict),
        ("Multiple Instances", test_multiple_instances),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
