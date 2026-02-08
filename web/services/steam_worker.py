"""
Steam Client Worker Process
Runs in separate process to avoid gevent/asyncio conflicts.
"""
import multiprocessing
import time
import queue
from typing import Dict, List, Optional

# IMPORTANT: Set spawn method for Windows compatibility
if __name__ != '__main__':
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass  # Already set


def run_steam_worker(request_queue, response_queue):
    """
    Worker process for Steam Client.
    Runs in its own process with gevent event loop.
    
    Args:
        request_queue: Queue to receive requests (command, data)
        response_queue: Queue to send responses
    """
    print("[STEAM WORKER] Starting Steam Client worker process...")
    print(f"[STEAM WORKER] PID: {multiprocessing.current_process().pid}")
    print(f"[STEAM WORKER] Request queue: {request_queue}")
    print(f"[STEAM WORKER] Response queue: {response_queue}")
    
    # Import Steam client ONLY in this process (gevent scope)
    from steam.client import SteamClient
    from steam.enums import EResult
    
    # Don't monkey patch - SteamClient uses gevent internally anyway
    print("[STEAM WORKER] Steam imports loaded (no monkey patching)")
    
    # Initialize Steam client
    client = SteamClient()
    logged_in = False
    login_failures = 0
    
    print("[STEAM WORKER] Steam Client initialized")
    
    def connect():
        """Connect to Steam anonymously"""
        nonlocal logged_in, login_failures
        
        if logged_in:
            return True
        
        try:
            print("[STEAM WORKER] Attempting anonymous login...")
            result = client.anonymous_login()
            
            if result == EResult.OK:
                logged_in = True
                login_failures = 0
                print("[STEAM WORKER] ✅ Connected to Steam (anonymous)")
                return True
            else:
                login_failures += 1
                print(f"[STEAM WORKER] ❌ Login failed: {result}")
                return False
        except Exception as e:
            login_failures += 1
            print(f"[STEAM WORKER] ❌ Connection error: {e}")
            return False
    
    def get_product_info(app_ids: List[int]) -> Dict[int, Dict]:
        """Get product info for apps"""
        nonlocal logged_in
        
        if not logged_in:
            if not connect():
                return {}
        
        try:
            results = {}
            batch_size = 50
            
            for i in range(0, len(app_ids), batch_size):
                batch = app_ids[i:i+batch_size]
                
                print(f"[STEAM WORKER] Fetching {len(batch)} apps (batch {i//batch_size + 1})...")
                
                resp = client.get_product_info(apps=batch)
                
                for app_id, app_data in resp['apps'].items():
                    if app_data is None:
                        continue
                    
                    common = app_data.get('common', {})
                    
                    # Extract Steam Deck compatibility
                    steam_deck = common.get('steam_deck_compatibility', {})
                    steam_deck_status = steam_deck.get('category', '3')  # 1=Verified, 2=Playable, 3=Unsupported
                    
                    # Extract developer/publisher
                    associations = common.get('associations', {})
                    developer = None
                    publisher = None
                    for assoc in associations.values():
                        if assoc.get('type') == 'developer' and not developer:
                            developer = assoc.get('name')
                        elif assoc.get('type') == 'publisher' and not publisher:
                            publisher = assoc.get('name')
                    
                    # Extract reviews
                    review_score = common.get('review_score')
                    review_percentage = common.get('review_percentage')
                    
                    # Extract release date
                    steam_release_date = common.get('steam_release_date')
                    
                    # Extract controller support
                    controller_support = common.get('controller_support')
                    
                    # Extract supported languages (with audio distinction)
                    supported_languages = common.get('supported_languages', {})
                    languages_with_audio = []
                    languages_subtitles_only = []
                    for lang, details in supported_languages.items():
                        if isinstance(details, dict) and details.get('supported') == 'true':
                            if details.get('full_audio') == 'true':
                                languages_with_audio.append(lang)
                            else:
                                languages_subtitles_only.append(lang)
                    
                    results[app_id] = {
                        'change_number': app_data.get('_change_number', 0),
                        'last_change': app_data.get('_change_number_date', 0),  # Unix timestamp
                        'common': common,
                        # Enriched metadata
                        'steam_deck_status': steam_deck_status,
                        'developer': developer,
                        'publisher': publisher,
                        'review_score': review_score,
                        'review_percentage': review_percentage,
                        'steam_release_date': steam_release_date,
                        'controller_support': controller_support,
                        'languages_with_audio': languages_with_audio,
                        'languages_subtitles_only': languages_subtitles_only,
                    }
                
                if i + batch_size < len(app_ids):
                    time.sleep(0.2)
            
            print(f"[STEAM WORKER] ✅ Fetched {len(results)}/{len(app_ids)} apps")
            return results
        except Exception as e:
            print(f"[STEAM WORKER] ❌ Error: {e}")
            logged_in = False
            return {}
    
    def get_status():
        """Get worker status"""
        return {
            'logged_in': logged_in,
            'login_failures': login_failures,
            'pid': multiprocessing.current_process().pid
        }
    
    # Main worker loop
    print("[STEAM WORKER] Worker ready, waiting for requests...")
    
    while True:
        try:
            # Wait for request (blocking with timeout)
            request = request_queue.get(timeout=1)
            
            command = request.get('command')
            request_id = request.get('id')
            
            print(f"[STEAM WORKER] Received command: {command} (id={request_id})")
            
            if command == 'shutdown':
                print("[STEAM WORKER] Shutdown requested")
                if logged_in:
                    client.logout()
                response_queue.put({'id': request_id, 'result': 'shutdown'})
                break
            
            elif command == 'connect':
                success = connect()
                response_queue.put({'id': request_id, 'result': success})
            
            elif command == 'disconnect':
                if logged_in:
                    client.logout()
                    logged_in = False
                response_queue.put({'id': request_id, 'result': True})
            
            elif command == 'get_product_info':
                app_ids = request.get('app_ids', [])
                results = get_product_info(app_ids)
                response_queue.put({'id': request_id, 'result': results})
            
            elif command == 'status':
                status = get_status()
                response_queue.put({'id': request_id, 'result': status})
            
            else:
                print(f"[STEAM WORKER] Unknown command: {command}")
                response_queue.put({'id': request_id, 'error': f'Unknown command: {command}'})
        
        except queue.Empty:
            # No request, continue loop
            continue
        except Exception as e:
            print(f"[STEAM WORKER] Error in main loop: {e}")
            import traceback
            traceback.print_exc()
    
    print("[STEAM WORKER] Worker process terminated")


class SteamWorkerClient:
    """
    Client for communicating with Steam Worker process.
    Thread-safe, can be used from FastAPI.
    """
    
    def __init__(self):
        # Use Manager for better Windows compatibility
        self.manager = multiprocessing.Manager()
        self.request_queue = self.manager.Queue()
        self.response_queue = self.manager.Queue()
        self.worker_process: Optional[multiprocessing.Process] = None
        self.request_counter = 0
        self._lock = multiprocessing.Lock()
    
    def start(self):
        """Start the worker process"""
        if self.worker_process and self.worker_process.is_alive():
            print("[STEAM CLIENT] Worker already running")
            return
        
        print("[STEAM CLIENT] Starting Steam worker process...")
        print(f"[STEAM CLIENT] Request queue: {self.request_queue}")
        print(f"[STEAM CLIENT] Response queue: {self.response_queue}")
        self.worker_process = multiprocessing.Process(
            target=run_steam_worker,
            args=(self.request_queue, self.response_queue),
            daemon=True
        )
        self.worker_process.start()
        print(f"[STEAM CLIENT] Worker started (PID: {self.worker_process.pid})")
        time.sleep(0.5)  # Give worker time to initialize
    
    def stop(self):
        """Stop the worker process"""
        if not self.worker_process or not self.worker_process.is_alive():
            return
        
        print("[STEAM CLIENT] Stopping worker process...")
        self._send_request('shutdown', timeout=5)
        self.worker_process.join(timeout=5)
        
        if self.worker_process.is_alive():
            print("[STEAM CLIENT] Force terminating worker...")
            self.worker_process.terminate()
            self.worker_process.join(timeout=2)
    
    def _send_request(self, command: str, timeout: float = 30, **kwargs) -> Optional[Dict]:
        """Send request to worker and wait for response"""
        with self._lock:
            request_id = self.request_counter
            self.request_counter += 1
        
        request = {
            'id': request_id,
            'command': command,
            **kwargs
        }
        
        print(f"[STEAM CLIENT] Sending request {request_id}: {command}")
        self.request_queue.put(request)
        print(f"[STEAM CLIENT] Request {request_id} queued, waiting for response...")
        
        # Wait for response
        start = time.time()
        while time.time() - start < timeout:
            try:
                response = self.response_queue.get(timeout=0.1)
                print(f"[STEAM CLIENT] Got response: {response}")
                if response.get('id') == request_id:
                    if 'error' in response:
                        print(f"[STEAM CLIENT] Error: {response['error']}")
                        return None
                    return response.get('result')
            except Exception:
                continue
        
        print(f"[STEAM CLIENT] Request {request_id} ({command}) timed out after {timeout}s")
        return None
    
    def connect(self) -> bool:
        """Connect to Steam"""
        result = self._send_request('connect', timeout=10)
        return bool(result) if result is not None else False
    
    def disconnect(self) -> bool:
        """Disconnect from Steam"""
        result = self._send_request('disconnect', timeout=5)
        return bool(result) if result is not None else False
    
    def get_product_info(self, app_ids: List[int]) -> Dict[int, Dict]:
        """Get product info for apps"""
        result = self._send_request('get_product_info', app_ids=app_ids, timeout=60)
        return result if result is not None else {}
    
    def get_status(self) -> Dict:
        """Get worker status"""
        result = self._send_request('status', timeout=5)
        return result if result is not None else {'logged_in': False, 'login_failures': 99}
    
    def is_alive(self) -> bool:
        """Check if worker process is alive"""
        return self.worker_process is not None and self.worker_process.is_alive()


# Global instance
_worker_client: Optional[SteamWorkerClient] = None

def get_steam_worker() -> SteamWorkerClient:
    """Get or create Steam Worker client"""
    global _worker_client
    if _worker_client is None:
        _worker_client = SteamWorkerClient()
        _worker_client.start()
    elif not _worker_client.is_alive():
        print("[STEAM CLIENT] Worker died, restarting...")
        _worker_client.start()
    return _worker_client
