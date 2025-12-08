from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from met_scraper import scrape_met_hours, read_from_json
import threading
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global cache for MET data
met_data_cache = None
last_update = None
is_updating = False

def update_met_cache():
    """Update the MET data cache in background"""
    global met_data_cache, last_update, is_updating
    
    if is_updating:
        return
    
    is_updating = True
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Updating MET cache...")
        met_data_cache = scrape_met_hours()
        last_update = met_data_cache.get('scraped_at')
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ MET cache updated at {last_update}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error updating MET cache: {e}")
        
        # Try to load from file
        cached = read_from_json()
        if cached:
            met_data_cache = cached
            last_update = cached.get('scraped_at')
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📂 Loaded cached data")
    finally:
        is_updating = False

@app.route('/api/met-hours')
def get_met_hours():
    """API endpoint to get current MET hours (with live scraping)"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📡 API Request: /api/met-hours")
        
        # Scrape fresh data
        data = scrape_met_hours()
        
        # Update cache with new data
        global met_data_cache, last_update
        met_data_cache = data
        last_update = data.get('scraped_at')
        
        return jsonify(data)
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Live scraping failed: {e}")
        
        # Fall back to cache
        if met_data_cache:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 Returning cached data")
            return jsonify(met_data_cache)
        
        # Fall back to file
        cached = read_from_json()
        if cached:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📂 Returning file data")
            return jsonify(cached)
        
        return jsonify({
            'error': 'Unable to fetch MET data',
            'message': str(e),
            'status': 'offline'
        }), 500

@app.route('/api/met-hours/cached')
def get_cached_met_hours():
    """API endpoint to get cached MET hours"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📡 API Request: /api/met-hours/cached")
        
        if met_data_cache:
            return jsonify(met_data_cache)
        
        cached = read_from_json()
        if cached:
            return jsonify(cached)
        
        return jsonify({
            'error': 'No cached data available',
            'status': 'no_cache'
        }), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_status():
    """API status endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'MET Museum Scraper API',
        'last_update': last_update,
        'cache_available': met_data_cache is not None,
        'server_time': datetime.now().isoformat()
    })

@app.route('/api/refresh')
def refresh_data():
    """Manually trigger data refresh"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Manual refresh requested")
        
        # Update cache
        update_met_cache()
        
        if met_data_cache:
            return jsonify({
                'status': 'success',
                'message': 'Data refreshed successfully',
                'last_update': last_update
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to refresh data'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('.', 'step3_landmarks.md')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)

def background_updater(interval=1800):  # 30 minutes = 1800 seconds
    """Background thread to update MET data periodically"""
    while True:
        update_met_cache()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏰ Next update in {interval//60} minutes")
        time.sleep(interval)

if __name__ == '__main__':
    print("=" * 50)
    print("🏛️  MET Museum Web Scraper API")
    print("=" * 50)
    
    # Initial cache update
    print("[INFO] Performing initial cache update...")
    update_met_cache()
    
    # Start background updater thread
    print("[INFO] Starting background updater (30 minute intervals)...")
    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()
    
    # Server information
    print("\n✅ Server Information:")
    print(f"   API URL: http://localhost:5000")
    print(f"   MET Data: http://localhost:5000/api/met-hours")
    print(f"   Status: http://localhost:5000/api/status")
    print(f"   Manual Refresh: http://localhost:5000/api/refresh")
    print(f"\n📂 Cached data will be saved to: met_data.json")
    print("=" * 50)
    print("[INFO] Starting Flask server...\n")
    
    # Start Flask server
    app.run(debug=True, port=5000, use_reloader=False)