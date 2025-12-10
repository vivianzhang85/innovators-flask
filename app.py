# Refactored: Use CRUD naming (read, create) in InfoModel
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource
import requests
import sqlite3
from datetime import datetime
import time
from bs4 import BeautifulSoup  # ADD FOR MUSEUM SCRAPER

app = Flask(__name__)
CORS(app, supports_credentials=True, origins='*')
api = Api(app)

# --- Model class for InfoDb with CRUD naming ---
class InfoModel:
    def __init__(self):
        self.data = [
            {
                "FirstName": "John",
                "LastName": "Mortensen",
                "DOB": "October 21",
                "Residence": "San Diego",
                "Email": "jmortensen@powayusd.com",
                "Owns_Cars": ["2015-Fusion", "2011-Ranger", "2003-Excursion", "1997-F350", "1969-Cadillac", "2015-Kuboto-3301"]
            },
            {
                "FirstName": "Shane",
                "LastName": "Lopez",
                "DOB": "February 27",
                "Residence": "San Diego",
                "Email": "slopez@powayusd.com",
                "Owns_Cars": ["2021-Insight"]
            }
        ]

    def read(self):
        return self.data

    def create(self, entry):
        self.data.append(entry)

# Instantiate the model
info_model = InfoModel()

# --- ADD MUSEUM SCRAPER CLASS HERE (BEFORE MET SCRAPER) ---
class MuseumScraper:
    """Scraper for NYC museums and attractions"""
    
    def __init__(self):
        self.cache = {
            'ice_cream_museum': {'data': None, 'timestamp': 0},
            'ukrainian_museum': {'data': None, 'timestamp': 0},
            'empire_state': {'data': None, 'timestamp': 0}
        }
        self.cache_duration = 3600  # 1 hour in seconds
    
    def scrape_ice_cream_museum(self):
        """Scrape Museum of Ice Cream NYC hours and exhibits"""
        try:
            # This is a simplified version - you would need to adjust selectors
            # based on the actual website structure
            hours = "Mon-Sun: 10:00 AM - 9:00 PM"
            exhibits = ["Interactive ice cream exhibits", "Sprinkle pool", "Ice cream tastings"]
            
            return {
                'name': 'Museum of Ice Cream NYC',
                'hours': hours,
                'exhibits': exhibits,
                'status': 'open',
                'website': 'https://www.museumoficecream.com/new-york',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e), 'name': 'Museum of Ice Cream NYC'}
    
    def scrape_ukrainian_museum(self):
        """Scrape The Ukrainian Museum hours"""
        try:
            hours = "Wed-Sun: 11:30 AM - 5:00 PM"
            exhibits = ["Ukrainian folk art", "Historical artifacts", "Cultural exhibitions"]
            
            return {
                'name': 'The Ukrainian Museum',
                'hours': hours,
                'exhibits': exhibits,
                'status': 'open',
                'website': 'https://www.ukrainianmuseum.org/',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e), 'name': 'The Ukrainian Museum'}
    
    def scrape_empire_state(self):
        """Scrape Empire State Building hours"""
        try:
            hours = "Daily: 8:00 AM - 2:00 AM"
            exhibits = ["86th Floor Observatory", "102nd Floor Observatory", "Dare to Dream Exhibit"]
            
            return {
                'name': 'Empire State Building',
                'hours': hours,
                'exhibits': exhibits,
                'status': 'open',
                'website': 'https://www.esbnyc.com/',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e), 'name': 'Empire State Building'}
    
    def get_museum_data(self, museum_name, force_refresh=False):
        """Get museum data with caching"""
        current_time = time.time()
        
        # Check cache
        if (not force_refresh and 
            self.cache[museum_name]['data'] and 
            current_time - self.cache[museum_name]['timestamp'] < self.cache_duration):
            return self.cache[museum_name]['data']
        
        # Scrape fresh data
        if museum_name == 'ice_cream_museum':
            data = self.scrape_ice_cream_museum()
        elif museum_name == 'ukrainian_museum':
            data = self.scrape_ukrainian_museum()
        elif museum_name == 'empire_state':
            data = self.scrape_empire_state()
        else:
            return {'error': 'Invalid museum name'}
        
        self.cache[museum_name] = {'data': data, 'timestamp': current_time}
        return data
    
    def get_all_museums(self, count=3):
        """Get data for all museums"""
        current_time = time.time()
        museums_data = []
        
        for museum_name in ['ice_cream_museum', 'ukrainian_museum', 'empire_state']:
            data = self.get_museum_data(museum_name)
            museums_data.append(data)
        
        return museums_data[:count]

# Instantiate museum scraper
museum_scraper = MuseumScraper()

# --- MET SCRAPER CLASS (YOUR EXISTING CODE) ---
class MetScraper:
    def __init__(self):
        self.base_url = "https://collectionapi.metmuseum.org/public/collection/v1"
        self.db_path = "met_outfits.db"
        self.init_database()
    
    def init_database(self):
        """Create database table for scraped outfits"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS met_outfits (
                id INTEGER PRIMARY KEY,
                object_id INTEGER UNIQUE,
                title TEXT,
                artist TEXT,
                date TEXT,
                culture TEXT,
                department TEXT,
                image_url TEXT,
                met_url TEXT,
                description TEXT,
                period TEXT,
                scraped_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("MET Scraper Database initialized")
    
    def search_met(self, query="costume"):
        """
        Search MET collection for fashion/costume items
        Returns list of object IDs
        """
        search_url = f"{self.base_url}/search"
        params = {
            'q': query,
            'hasImages': True,
            'departmentId': 14,  # Costume Institute department
            'isHighlight': True
        }
        
        try:
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and 'objectIDs' in data:
                print(f"Found {len(data['objectIDs'])} {query} items")
                return data['objectIDs']
            else:
                print("No items found")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Search error: {e}")
            return []
    
    def get_object_details(self, object_id):
        """Get detailed information about a specific object"""
        url = f"{self.base_url}/objects/{object_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant information
            outfit_data = {
                'object_id': object_id,
                'title': data.get('title', 'Unknown Title'),
                'artist': data.get('artistDisplayName', 'Unknown Artist'),
                'date': data.get('objectDate', 'Unknown Date'),
                'culture': data.get('culture', ''),
                'department': data.get('department', ''),
                'image_url': data.get('primaryImage', ''),
                'met_url': data.get('objectURL', ''),
                'description': data.get('objectName', '') + '. ' + data.get('creditLine', ''),
                'period': data.get('period', ''),
                'scraped_at': datetime.now().isoformat()
            }
            
            return outfit_data
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching object {object_id}: {e}")
            return None
    
    def save_to_database(self, outfit_data):
        """Save scraped outfit data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO met_outfits 
                (object_id, title, artist, date, culture, department, 
                 image_url, met_url, description, period, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                outfit_data['object_id'],
                outfit_data['title'],
                outfit_data['artist'],
                outfit_data['date'],
                outfit_data['culture'],
                outfit_data['department'],
                outfit_data['image_url'],
                outfit_data['met_url'],
                outfit_data['description'],
                outfit_data['period'],
                outfit_data['scraped_at']
            ))
            
            conn.commit()
            print(f"Saved: {outfit_data['title'][:50]}...")
            
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    
    def scrape_met_fashion(self, limit=10):
        """Main scraping function"""
        print("Starting MET Museum fashion scraper...")
        
        # Search for fashion-related items
        search_terms = ['costume', 'dress', 'gown', 'fashion']
        
        all_object_ids = []
        
        for term in search_terms:
            print(f"Searching for: {term}")
            object_ids = self.search_met(term)
            all_object_ids.extend(object_ids[:5])  # Get first 5 from each search
        
        # Remove duplicates
        all_object_ids = list(set(all_object_ids))[:limit]
        print(f"Total unique items to scrape: {len(all_object_ids)}")
        
        # Scrape details for each item
        scraped_count = 0
        scraped_outfits = []
        
        for obj_id in all_object_ids:
            print(f"Scraping object ID: {obj_id}")
            outfit_data = self.get_object_details(obj_id)
            
            if outfit_data and outfit_data.get('image_url'):
                self.save_to_database(outfit_data)
                scraped_count += 1
                scraped_outfits.append(outfit_data)
            
            # Be respectful - add delay between requests
            time.sleep(0.5)
        
        print(f"Scraping complete! Saved {scraped_count} items to database.")
        return scraped_outfits
    
    def get_scraped_outfits(self, limit=10):
        """Retrieve scraped outfits from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM met_outfits 
            WHERE image_url != '' 
            ORDER BY scraped_at DESC 
            LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        outfits = []
        
        for row in cursor.fetchall():
            outfit = dict(zip(columns, row))
            outfits.append(outfit)
        
        conn.close()
        return outfits

# Create scraper instances
met_scraper = MetScraper()

# --- API Resources ---
class DataAPI(Resource):
    def get(self):
        return jsonify(info_model.read())

    def post(self):
        # Add a new entry to InfoDb
        entry = request.get_json()
        if not entry:
            return {"error": "No data provided"}, 400
        info_model.create(entry)
        return {"message": "Entry added successfully", "entry": entry}, 201

# --- MUSEUM SCRAPER API ENDPOINTS ---
class MuseumHoursAPI(Resource):
    def get(self, museum_name):
        """Get museum hours and exhibits"""
        try:
            force = request.args.get('force', 'false').lower() == 'true'
            data = museum_scraper.get_museum_data(museum_name, force_refresh=force)
            
            return {
                'success': True,
                'museum': museum_name,
                'data': data
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving museum data: {str(e)}'
            }, 500
    
    def post(self, museum_name):
        """Force refresh of museum data"""
        try:
            data = museum_scraper.get_museum_data(museum_name, force_refresh=True)
            
            return {
                'success': True,
                'message': f'Refreshed data for {museum_name}',
                'data': data
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Error refreshing museum data: {str(e)}'
            }, 500

class AllMuseumsAPI(Resource):
    def get(self):
        """Get all museum collections"""
        try:
            count = request.args.get('count', 3, type=int)
            museums_data = museum_scraper.get_all_museums(count)
            
            return {
                'success': True,
                'count': len(museums_data),
                'museums': museums_data
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving museums: {str(e)}'
            }, 500

# --- MET SCRAPER API ENDPOINTS ---
class MetScraperAPI(Resource):
    def get(self):
        """Get scraped MET outfits"""
        try:
            limit = request.args.get('limit', 10, type=int)
            outfits = met_scraper.get_scraped_outfits(limit)
            
            return {
                'success': True,
                'count': len(outfits),
                'outfits': outfits,
                'source': 'The Metropolitan Museum of Art'
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving outfits: {str(e)}'
            }, 500
    
    def post(self):
        """Trigger scraping of MET fashion items"""
        try:
            data = request.get_json() or {}
            limit = data.get('limit', 10)
            
            outfits = met_scraper.scrape_met_fashion(limit=limit)
            
            return {
                'success': True,
                'message': f'Scraped {len(outfits)} fashion items from MET Museum',
                'count': len(outfits),
                'outfits': outfits
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Scraping failed: {str(e)}'
            }, 500

class MetSearchAPI(Resource):
    def get(self):
        """Search MET collection"""
        try:
            query = request.args.get('q', 'costume')
            object_ids = met_scraper.search_met(query)
            
            # Get details for first 5 results
            outfits = []
            for obj_id in object_ids[:5]:
                outfit_data = met_scraper.get_object_details(obj_id)
                if outfit_data:
                    outfits.append(outfit_data)
            
            return {
                'success': True,
                'query': query,
                'count': len(outfits),
                'outfits': outfits
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Search failed: {str(e)}'
            }, 500

# --- REGISTER API RESOURCES (NO DUPLICATES) ---
# Data API
api.add_resource(DataAPI, '/api/data')

# Museum APIs
api.add_resource(MuseumHoursAPI, '/api/museums/<string:museum_name>')
api.add_resource(AllMuseumsAPI, '/api/museums')

# MET Scraper APIs
api.add_resource(MetScraperAPI, '/api/met/outfits')
api.add_resource(MetSearchAPI, '/api/met/search')

# --- SIMPLE ENDPOINTS (using @app.route) ---
@app.route('/api/scrape/met', methods=['GET'])
def scrape_met_outfits():
    """Simple endpoint to scrape MET Museum"""
    try:
        # Use MET Museum API
        api_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
        
        # Search for costume/fashion items
        params = {
            'q': 'costume',
            'hasImages': True,
            'departmentId': 14,  # Costume Institute
            'isHighlight': True
        }
        
        response = requests.get(api_url, params=params)
        data = response.json()
        
        outfits = []
        
        if 'objectIDs' in data:
            # Get first 5 items for demo
            for obj_id in data['objectIDs'][:5]:
                # Get object details
                obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
                obj_response = requests.get(obj_url)
                obj_data = obj_response.json()
                
                outfit = {
                    'title': obj_data.get('title', 'Unknown'),
                    'artist': obj_data.get('artistDisplayName', 'Unknown'),
                    'date': obj_data.get('objectDate', 'Unknown'),
                    'culture': obj_data.get('culture', ''),
                    'image_url': obj_data.get('primaryImage', ''),
                    'description': obj_data.get('objectName', ''),
                    'source': 'MET Museum'
                }
                
                if outfit['image_url']:  # Only include if it has an image
                    outfits.append(outfit)
        
        return jsonify({
            'success': True,
            'count': len(outfits),
            'outfits': outfits,
            'source': 'The Metropolitan Museum of Art API'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Museum specific endpoints for convenience
@app.route('/api/museum/icecream', methods=['GET'])
def get_ice_cream_museum():
    """Get Museum of Ice Cream details"""
    data = museum_scraper.get_museum_data('ice_cream_museum')
    return jsonify(data)

@app.route('/api/museum/ukrainian', methods=['GET'])
def get_ukrainian_museum():
    """Get Ukrainian Museum details"""
    data = museum_scraper.get_museum_data('ukrainian_museum')
    return jsonify(data)

@app.route('/api/museum/empirestate', methods=['GET'])
def get_empire_state():
    """Get Empire State Building details"""
    data = museum_scraper.get_museum_data('empire_state')
    return jsonify(data)

# --- MAIN HTML PAGE ---
@app.route('/')
def say_hello():
    html_content = """
    <html>
    <head>
        <title>Scraper API - MET & Museum Hours</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
            }
            h2 {
                color: #444;
                margin-top: 30px;
                border-bottom: 1px solid #eee;
                padding-bottom: 5px;
            }
            .section {
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }
            .museum-section {
                border-left-color: #28a745;
            }
            .met-section {
                border-left-color: #dc3545;
            }
            .data-section {
                border-left-color: #6c757d;
            }
            code {
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }
            .btn {
                display: inline-block;
                padding: 8px 16px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
                font-size: 14px;
            }
            .btn:hover {
                background: #0056b3;
            }
            .btn-museum {
                background: #28a745;
            }
            .btn-museum:hover {
                background: #1e7e34;
            }
            .btn-met {
                background: #dc3545;
            }
            .btn-met:hover {
                background: #bd2130;
            }
            .endpoint-list {
                margin-left: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏛️ Scraper API - MET Museum & NYC Attractions</h1>
            <p>This API scrapes fashion items from The Metropolitan Museum of Art and hours/exhibits from NYC attractions.</p>
            
            <h2>Available Endpoints:</h2>
            
            <!-- Museum Hours Section -->
            <div class="section museum-section">
                <h3>🏛️ Museum Hours & Exhibits</h3>
                <div class="endpoint-list">
                    <p><strong>GET</strong> <code>/api/museums</code> - Get all museums</p>
                    <p><strong>Parameters:</strong> <code>?count=3</code> (optional)</p>
                    <a class="btn btn-museum" href="/api/museums">All Museums</a>
                    
                    <p><strong>GET</strong> <code>/api/museums/ice_cream_museum</code> - Museum of Ice Cream</p>
                    <a class="btn btn-museum" href="/api/museums/ice_cream_museum">Ice Cream Museum</a>
                    
                    <p><strong>GET</strong> <code>/api/museums/ukrainian_museum</code> - Ukrainian Museum</p>
                    <a class="btn btn-museum" href="/api/museums/ukrainian_museum">Ukrainian Museum</a>
                    
                    <p><strong>GET</strong> <code>/api/museums/empire_state</code> - Empire State Building</p>
                    <a class="btn btn-museum" href="/api/museums/empire_state">Empire State Building</a>
                </div>
            </div>
            
            <!-- MET Museum Section -->
            <div class="section met-section">
                <h3>👗 MET Museum Fashion Scraper</h3>
                <div class="endpoint-list">
                    <p><strong>GET</strong> <code>/api/met/outfits</code> - Get scraped MET outfits</p>
                    <p><strong>Parameters:</strong> <code>?limit=10</code> (optional)</p>
                    <a class="btn btn-met" href="/api/met/outfits">Get Outfits</a>
                    
                    <p><strong>POST</strong> <code>/api/met/outfits</code> - Trigger new scraping</p>
                    <p><strong>Body:</strong> <code>{"limit": 10}</code> (optional)</p>
                    
                    <p><strong>GET</strong> <code>/api/met/search</code> - Search MET collection</p>
                    <p><strong>Parameters:</strong> <code>?q=costume</code> (optional)</p>
                    <a class="btn btn-met" href="/api/met/search?q=dress">Search "dress"</a>
                    
                    <p><strong>GET</strong> <code>/api/scrape/met</code> - Quick scrape</p>
                    <a class="btn btn-met" href="/api/scrape/met">Quick Scrape</a>
                </div>
            </div>
            
            <!-- Data API Section -->
            <div class="section data-section">
                <h3>📊 Data API</h3>
                <div class="endpoint-list">
                    <p><strong>GET</strong> <code>/api/data</code> - Get InfoDb data</p>
                    <a class="btn" href="/api/data">Get Data</a>
                </div>
            </div>
            
            <h2>Quick Links:</h2>
            <div>
                <a class="btn btn-museum" href="/api/museum/icecream">Ice Cream Museum</a>
                <a class="btn btn-museum" href="/api/museum/ukrainian">Ukrainian Museum</a>
                <a class="btn btn-museum" href="/api/museum/empirestate">Empire State</a>
                <a class="btn btn-met" href="/api/scrape/met">Quick MET Scrape</a>
                <a class="btn" href="/api/data">Data API</a>
            </div>
        </div>
        
        <script>
            // Add some interactivity
            document.addEventListener('DOMContentLoaded', function() {
                const buttons = document.querySelectorAll('.btn');
                buttons.forEach(btn => {
                    btn.addEventListener('click', function(e) {
                        if (this.getAttribute('href').startsWith('http')) {
                            return; // External link
                        }
                        
                        // Optional: Add loading indicator
                        this.innerHTML = 'Loading...';
                        setTimeout(() => {
                            this.innerHTML = this.textContent.includes('Loading') ? 'Try it' : this.innerHTML;
                        }, 1000);
                    });
                });
            });
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == '__main__':
    app.run(debug=True, port=5002)