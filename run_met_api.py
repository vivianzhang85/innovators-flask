from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from met_scraper import scrape_met_hours, read_from_json
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)

# Global cache
met_cache = None

def update_cache():
    """Update cache in background"""
    global met_cache
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Updating MET cache...")
        met_cache = scrape_met_hours()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Cache update failed: {e}")

@app.route('/api/met-hours')
def get_met_hours():
    """API endpoint to get MET hours"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Fetching MET hours...")
        data = scrape_met_hours()
        return jsonify(data)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {e}")
        # Try cache
        global met_cache
        if met_cache:
            return jsonify(met_cache)
        # Try file
        cached = read_from_json()
        if cached:
            return jsonify(cached)
        return jsonify({'error': 'Unable to fetch data'}), 500

@app.route('/api/met-hours/cached')
def get_cached_met_hours():
    """API endpoint to get cached MET hours"""
    try:
        cached = read_from_json()
        if cached:
            return jsonify(cached)
        return jsonify({'error': 'No cached data'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_status():
    """API status endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'MET Museum Scraper API',
        'time': datetime.now().isoformat(),
        'endpoints': {
            'live_data': '/api/met-hours',
            'cached_data': '/api/met-hours/cached',
            'status': '/api/status'
        }
    })

@app.route('/')
def index():
    """Serve a simple test page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MET Museum Scraper API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            code { background: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🏛️ MET Museum Web Scraper API</h1>
        <p>This API provides live hours and admission information from the MET Museum website.</p>
        
        <div class="endpoint">
            <h3>📡 Live Data</h3>
            <p><code>GET /api/met-hours</code></p>
            <p>Fetches current data from the MET website</p>
            <a href="/api/met-hours" target="_blank">Test endpoint</a>
        </div>
        
        <div class="endpoint">
            <h3>💾 Cached Data</h3>
            <p><code>GET /api/met-hours/cached</code></p>
            <p>Returns previously saved data</p>
            <a href="/api/met-hours/cached" target="_blank">Test endpoint</a>
        </div>
        
        <div class="endpoint">
            <h3>📊 Status</h3>
            <p><code>GET /api/status</code></p>
            <a href="/api/status" target="_blank">Test endpoint</a>
        </div>
        
        <hr>
        <p><strong>To use in your frontend:</strong></p>
        <pre>
fetch('http://localhost:5001/api/met-hours')
  .then(response => response.json())
  .then(data => console.log(data));
        </pre>
    </body>
    </html>
    '''

def background_updater():
    """Background thread to update cache"""
    while True:
        update_cache()
        time.sleep(1800)  # 30 minutes

if __name__ == '__main__':
    # Initial cache update
    update_cache()
    
    # Start background updater
    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()
    
    print("=" * 50)
    print("🏛️  MET Museum Web Scraper API")
    print("=" * 50)
    print("📡 API Endpoints:")
    print("  • http://localhost:5001/api/met-hours")
    print("  • http://localhost:5001/api/met-hours/cached")
    print("  • http://localhost:5001/api/status")
    print("  • http://localhost:5001/ (test page)")
    print("=" * 50)
    print("🚀 Starting server on port 5001...")
    app.run(debug=True, port=5001, use_reloader=False)
