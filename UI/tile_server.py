import os
import urllib.request
import urllib.error
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import random
from PyQt6.QtCore import QThread, pyqtSignal

class TileDownloader:
    """Downloads map tiles and caches them locally"""
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        # Create cache directory if it doesn't exist
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating cache directory: {e}")
    
    def get_tile_path(self, tile_source, z, x, y):
        """Get the local path for a map tile"""
        # Use uppercase for consistency with existing cache
        if tile_source.lower() == 'topo':
            tile_source = 'TOPO'
            
        try:
            tile_dir = os.path.join(self.cache_dir, tile_source, str(z), str(x))
            os.makedirs(tile_dir, exist_ok=True)
            return os.path.join(tile_dir, f"{y}.png")
        except OSError as e:
            print(f"Error creating tile directory: {e}")
            return None
    
    def download_tile(self, tile_url, tile_path):
        """Download a single tile from the remote server"""
        try:
            # Add a User-Agent to avoid being blocked
            headers = {
                'User-Agent': 'DroneControlApplication/1.0'
            }
            req = urllib.request.Request(url=tile_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                tile_data = response.read()
                with open(tile_path, 'wb') as f:
                    f.write(tile_data)
                return True
        except urllib.error.URLError as e:
            print(f"Error downloading tile: {e}")
            return False
    def get_tile(self, tile_source, tile_url, z, x, y):
        """Get a tile from cache or download it if not cached"""
        tile_path = self.get_tile_path(tile_source, z, x, y)
        
        # If tile exists in cache, return its path
        if tile_path and os.path.exists(tile_path):
            return tile_path
        
        # Otherwise download the tile
        if tile_path and self.download_tile(tile_url, tile_path):
            return tile_path
        
        return None

class TileRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for serving map tiles"""
    def log_request(self, code='-', size='-'):
        """Suppress request logging"""
        pass

    def log_message(self, format, *args):
        """Suppress log messages"""
        pass

    def log_error(self, format, *args):
        """Suppress error logging"""
        pass

    def do_GET(self):
        """Handle GET requests for tiles"""
        parts = self.path.split('/')

        # Handle tile requests
        if len(parts) >= 5 and parts[1] == 'tiles':
            try:
                tile_source = parts[2]
                z = int(parts[3])
                x = int(parts[4].split('.')[0])  # Remove any extension
                y = int(parts[5].split('.')[0])  # Remove any extension

                # Construct the remote URL
                if tile_source.lower() == 'topo':
                    server = random.choice(['a', 'b', 'c'])
                    remote_url = f"https://{server}.tile.opentopomap.org/{z}/{x}/{y}.png"
                    
                    # Try to get the tile
                    tile_path = self.server.downloader.get_tile(tile_source, remote_url, z, x, y)
                    
                    if tile_path and os.path.exists(tile_path):
                        self.send_response(200)
                        self.send_header('Content-type', 'image/png')
                        self.end_headers()
                        
                        with open(tile_path, 'rb') as f:
                            self.wfile.write(f.read())
                        return
                    
                print(f"Tile not found: {self.path}")
                self.send_response(404)
                self.end_headers()
                return
                
            except (ValueError, IndexError) as e:
                print(f"Error processing tile request: {e}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid tile request')
                return

        elif '/resources/' in self.path:
            resource_path = self.path.replace('/resources/', '')
            local_path = os.path.join(self.server.resource_dir, resource_path)
            
            if os.path.exists(local_path):
                self.send_response(200)
                if local_path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                elif local_path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif local_path.endswith('.png'):
                    self.send_header('Content-type', 'image/png')
                self.end_headers()
                
                with open(local_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
        # If we get here, the resource wasn't found
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'Not found')

class LocalTileServer(QThread):
    """Thread for running the local tile server"""
    
    server_started = pyqtSignal(int)
    
    def __init__(self, resource_dir, cache_dir, parent=None):
        super().__init__(parent)
        self.resource_dir = resource_dir
        self.cache_dir = cache_dir
        self.server = None
        self.port = 8080  # Default port
    
    def run(self):
        """Start the local tile server"""
        # Try ports until we find an available one
        for port in range(8080, 8100):
            try:
                # Create a tile downloader
                downloader = TileDownloader(self.cache_dir)
                
                # Create and configure the server
                server = HTTPServer(('localhost', port), TileRequestHandler)
                server.downloader = downloader
                server.resource_dir = self.resource_dir
                
                self.port = port
                self.server = server
                
                # Emit signal with the port number
                self.server_started.emit(port)
                
                # Start serving
                self.server.serve_forever()
                break
            except OSError:
                # Port in use, try the next one
                continue
        else:
            print("Error: No available ports in the range 8080-8100.")
    
    def stop(self):
        """Stop the server"""
        if self.server:
            # Create a new thread to call shutdown
            shutdown_thread = threading.Thread(target=self.server.shutdown)
            shutdown_thread.daemon = True
            shutdown_thread.start()
            shutdown_thread.join()