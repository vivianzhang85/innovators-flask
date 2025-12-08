# Refactored: Use CRUD naming (read, create) in InfoModel
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource
import requests  # ADD THIS LINE
import sqlite3   # ADD THIS LINE
from datetime import datetime  # ADD THIS LINE

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

# --- ADD MET SCRAPER CLASS HERE ---
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
            import time
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

# Create scraper instance
met_scraper = MetScraper()

# --- API Resource ---
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

api.add_resource(DataAPI, '/api/data')

# --- ADD MET SCRAPER API ENDPOINTS HERE ---
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

# Register the scraper API endpoints
api.add_resource(MetScraperAPI, '/api/met/outfits')
api.add_resource(MetSearchAPI, '/api/met/search')

# ADD THIS SIMPLE SCRAPER ENDPOINT TOO
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

# Wee can use @app.route for HTML endpoints, this will be style for Admin UI
@app.route('/')
def say_hello():
    html_content = """
    <html>
    <head>
        <title>Fashion Scraper API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 800px;
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
            .endpoint {
                background: #f8f9fa;
                padding: 15px;
                margin: 15px 0;
                border-left: 4px solid #007bff;
                border-radius: 4px;
            }
            code {
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }
            .btn {
                display: inline-block;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
            }
            .btn:hover {
                background: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👗 Fashion Scraper API</h1>
            <p>This API can scrape fashion items from The Metropolitan Museum of Art.</p>
            
            <h2>Available Endpoints:</h2>
            
            <div class="endpoint">
                <h3>GET <code>/api/met/outfits</code></h3>
                <p>Get previously scraped MET outfits.</p>
                <p><strong>Parameters:</strong> <code>?limit=10</code> (optional)</p>
                <a class="btn" href="/api/met/outfits">Try it</a>
            </div>
            
            <div class="endpoint">
                <h3>POST <code>/api/met/outfits</code></h3>
                <p>Trigger new scraping of MET fashion items.</p>
                <p><strong>Body:</strong> <code>{"limit": 10}</code> (optional)</p>
            </div>
            
            <div class="endpoint">
                <h3>GET <code>/api/met/search</code></h3>
                <p>Search MET collection.</p>
                <p><strong>Parameters:</strong> <code>?q=costume</code> (optional)</p>
                <a class="btn" href="/api/met/search?q=dress">Search "dress"</a>
            </div>
            
            <div class="endpoint">
                <h3>GET <code>/api/scrape/met</code></h3>
                <p>Quick scrape of MET costume items.</p>
                <a class="btn" href="/api/scrape/met">Quick Scrape</a>
            </div>
            
            <h2>How to Use:</h2>
            <ol>
                <li>Click "Quick Scrape" to get sample MET fashion items</li>
                <li>Use the search endpoint to find specific items</li>
                <li>Use POST to scrape new items into the database</li>
            </ol>
        </div>
    </body>
    </html>
    """
    return html_content

if __name__ == '__main__':
    app.run(debug=True, port=5002)  # Changed to 5002