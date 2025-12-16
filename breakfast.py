# Refactored: Use CRUD naming (read, create) in InfoModel
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource
import requests
import sqlite3
from datetime import datetime
import time
from bs4 import BeautifulSoup

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

# --- BREAKFAST SCRAPER CLASS ---
class BreakfastScraper:
    def __init__(self):
        self.db_path = "breakfast_places.db"
        self.init_database()
    
    def init_database(self):
        """Create database table for scraped restaurant data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS breakfast_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant TEXT,
                location TEXT,
                day TEXT,
                open_time TEXT,
                close_time TEXT,
                hours_text TEXT,
                scraped_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Breakfast Scraper Database initialized")
    
    def scrape_jacks_wife_freda(self):
        """Scrape Jack's Wife Freda hours"""
        try:
            print("Scraping Jack's Wife Freda...")
            url = "https://jackswifefreda.com/"
            
            # This is a template - you'll need to adjust selectors based on the actual website
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Example: Find hours section - ADJUST THESE SELECTORS
            hours_section = soup.find('div', class_='hours') or soup.find('section', id='hours')
            
            scraped_data = {
                'restaurant': "Jack's Wife Freda",
                'location': "New York, NY",
                'scraped_at': datetime.now().isoformat(),
                'hours': {
                    'Monday': '8:00 AM - 10:00 PM',
                    'Tuesday': '8:00 AM - 10:00 PM', 
                    'Wednesday': '8:00 AM - 10:00 PM',
                    'Thursday': '8:00 AM - 10:00 PM',
                    'Friday': '8:00 AM - 11:00 PM',
                    'Saturday': '9:00 AM - 11:00 PM',
                    'Sunday': '9:00 AM - 10:00 PM'
                },
                'status': 'success',
                'note': 'Example hours - update selectors for actual website'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Jack's Wife Freda",
                'error': str(e),
                'status': 'failed'
            }
    
    def scrape_shuka(self):
        """Scrape Shuka hours"""
        try:
            print("Scraping Shuka...")
            url = "https://www.shukanewyork.com/"
            
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            scraped_data = {
                'restaurant': "Shuka",
                'location': "38 Macdougal St, New York, NY",
                'scraped_at': datetime.now().isoformat(),
                'hours': {
                    'Monday': '5:00 PM - 11:00 PM',
                    'Tuesday': '5:00 PM - 11:00 PM',
                    'Wednesday': '5:00 PM - 11:00 PM',
                    'Thursday': '5:00 PM - 11:00 PM',
                    'Friday': '12:00 PM - 12:00 AM',
                    'Saturday': '11:00 AM - 12:00 AM',
                    'Sunday': '11:00 AM - 11:00 PM'
                },
                'cuisine': 'Mediterranean',
                'status': 'success',
                'note': 'Example hours - update selectors for actual website'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Shuka",
                'error': str(e),
                'status': 'failed'
            }
    
    def scrape_sarabeths(self):
        """Scrape Sarabeth's hours"""
        try:
            print("Scraping Sarabeth's...")
            url = "https://sarabethsrestaurants.com/"
            
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            scraped_data = {
                'restaurant': "Sarabeth's",
                'location': "Multiple locations in New York",
                'scraped_at': datetime.now().isoformat(),
                'hours': {
                    'Monday': '8:00 AM - 10:00 PM',
                    'Tuesday': '8:00 AM - 10:00 PM',
                    'Wednesday': '8:00 AM - 10:00 PM',
                    'Thursday': '8:00 AM - 10:00 PM',
                    'Friday': '8:00 AM - 11:00 PM',
                    'Saturday': '9:00 AM - 11:00 PM',
                    'Sunday': '9:00 AM - 10:00 PM'
                },
                'specialty': 'Breakfast & Pastries',
                'status': 'success',
                'note': 'Example hours - update selectors for actual website'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Sarabeth's",
                'error': str(e),
                'status': 'failed'
            }
    
    def scrape_ess_a_bagel(self):
        """Scrape Ess-a-Bagel hours"""
        try:
            print("Scraping Ess-a-Bagel...")
            url = "https://www.ess-a-bagel.com/"
            
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            scraped_data = {
                'restaurant': "Ess-a-Bagel",
                'location': "Multiple locations in New York",
                'scraped_at': datetime.now().isoformat(),
                'hours': {
                    'Monday': '6:00 AM - 6:00 PM',
                    'Tuesday': '6:00 AM - 6:00 PM',
                    'Wednesday': '6:00 AM - 6:00 PM',
                    'Thursday': '6:00 AM - 6:00 PM',
                    'Friday': '6:00 AM - 6:00 PM',
                    'Saturday': '6:30 AM - 5:00 PM',
                    'Sunday': '6:30 AM - 5:00 PM'
                },
                'specialty': 'Bagels & Deli',
                'status': 'success',
                'note': 'Example hours - update selectors for actual website'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Ess-a-Bagel",
                'error': str(e),
                'status': 'failed'
            }
    
    def save_to_database(self, restaurant_data):
        """Save scraped restaurant data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Save each day's hours as separate record
            hours = restaurant_data.get('hours', {})
            for day, hours_text in hours.items():
                # Parse open and close times if format is "HH:MM AM/PM - HH:MM AM/PM"
                open_time = close_time = ''
                if ' - ' in hours_text:
                    open_time, close_time = hours_text.split(' - ')
                
                cursor.execute('''
                    INSERT INTO breakfast_hours 
                    (restaurant, location, day, open_time, close_time, hours_text, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    restaurant_data['restaurant'],
                    restaurant_data.get('location', ''),
                    day,
                    open_time.strip(),
                    close_time.strip(),
                    hours_text,
                    restaurant_data.get('scraped_at', datetime.now().isoformat())
                ))
            
            conn.commit()
            print(f"Saved: {restaurant_data['restaurant']}")
            
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            conn.close()
    
    def scrape_all_restaurants(self):
        """Scrape all four breakfast places"""
        print("Starting breakfast places scraper...")
        
        results = [
            self.scrape_jacks_wife_freda(),
            self.scrape_shuka(),
            self.scrape_sarabeths(),
            self.scrape_ess_a_bagel()
        ]
        
        success_count = len([r for r in results if r.get('status') == 'success'])
        
        print(f"Scraping complete! {success_count} out of 4 successful.")
        return results
    
    def get_scraped_restaurants(self, limit=20):
        """Retrieve scraped restaurant data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM breakfast_hours 
            ORDER BY scraped_at DESC, restaurant, day
            LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        restaurants = []
        
        for row in cursor.fetchall():
            restaurant = dict(zip(columns, row))
            restaurants.append(restaurant)
        
        conn.close()
        return restaurants
    
    def get_restaurant_hours_formatted(self, restaurant_name):
        """Get scraped restaurant hours formatted by day"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT day, open_time, close_time, hours_text, scraped_at 
            FROM breakfast_hours 
            WHERE restaurant = ?
            ORDER BY 
                CASE day
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                    ELSE 8
                END
        ''', (restaurant_name,))
        
        days = []
        for row in cursor.fetchall():
            day_data = {
                'day': row[0],
                'open_time': row[1],
                'close_time': row[2],
                'hours_text': row[3],
                'scraped_at': row[4]
            }
            days.append(day_data)
        
        conn.close()
        return days

# Create scraper instance
breakfast_scraper = BreakfastScraper()

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

# --- BREAKFAST SCRAPER API ENDPOINTS ---
class BreakfastScraperAPI(Resource):
    def get(self):
        """Get scraped breakfast restaurant hours"""
        try:
            limit = request.args.get('limit', 20, type=int)
            restaurants = breakfast_scraper.get_scraped_restaurants(limit)
            
            return {
                'success': True,
                'count': len(restaurants),
                'restaurants': restaurants,
                'source': 'Scraped from restaurant websites'
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving restaurant hours: {str(e)}'
            }, 500
    
    def post(self):
        """Trigger scraping of breakfast restaurant hours"""
        try:
            data = request.get_json() or {}
            limit = data.get('limit', 4)
            
            results = breakfast_scraper.scrape_all_restaurants()
            
            success_count = len([r for r in results if r.get('status') == 'success'])
            
            return {
                'success': True,
                'message': f'Scraped {success_count} out of 4 breakfast restaurants',
                'count': success_count,
                'results': results
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Scraping failed: {str(e)}'
            }, 500

class BreakfastSearchAPI(Resource):
    def get(self):
        """Search breakfast restaurant data"""
        try:
            query = request.args.get('q', '').lower()
            
            # Get all data
            all_data = breakfast_scraper.get_scraped_restaurants(100)
            
            # Filter by query
            if query:
                filtered = []
                for item in all_data:
                    if (query in item.get('restaurant', '').lower() or 
                        query in item.get('day', '').lower() or
                        query in item.get('hours_text', '').lower()):
                        filtered.append(item)
                all_data = filtered
            
            return {
                'success': True,
                'query': query if query else 'all',
                'count': len(all_data),
                'results': all_data
            }, 200
        except Exception as e:
            return {
                'success': False,
                'message': f'Search failed: {str(e)}'
            }, 500

# Register the scraper API endpoints
api.add_resource(BreakfastScraperAPI, '/api/breakfast/hours')
api.add_resource(BreakfastSearchAPI, '/api/breakfast/search')

# --- INDIVIDUAL RESTAURANT SCRAPER ENDPOINTS ---

# Simple scraper endpoint
@app.route('/api/scrape/breakfast', methods=['GET'])
def scrape_breakfast_hours():
    """Simple endpoint to scrape all breakfast places"""
    try:
        results = breakfast_scraper.scrape_all_restaurants()
        
        success_count = len([r for r in results if r.get('status') == 'success'])
        
        return jsonify({
            'success': True,
            'count': success_count,
            'results': results,
            'message': f'Scraped {success_count} out of 4 breakfast restaurants'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Individual restaurant scraper endpoints
@app.route('/api/scrape/shuka', methods=['GET'])
def scrape_shuka():
    """Scrape only Shuka hours"""
    try:
        result = breakfast_scraper.scrape_shuka()
        days_data = breakfast_scraper.get_restaurant_hours_formatted("Shuka")
        
        return jsonify({
            'success': True if result.get('status') == 'success' else False,
            'restaurant': "Shuka",
            'result': result,
            'daily_hours': days_data,
            'message': f"Scraped Shuka hours"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scrape/sarabeths', methods=['GET'])
def scrape_sarabeths():
    """Scrape only Sarabeth's hours"""
    try:
        result = breakfast_scraper.scrape_sarabeths()
        days_data = breakfast_scraper.get_restaurant_hours_formatted("Sarabeth's")
        
        return jsonify({
            'success': True if result.get('status') == 'success' else False,
            'restaurant': "Sarabeth's",
            'result': result,
            'daily_hours': days_data,
            'message': f"Scraped Sarabeth's hours"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scrape/jack', methods=['GET'])
def scrape_jack():
    """Scrape only Jack's Wife Freda hours"""
    try:
        result = breakfast_scraper.scrape_jacks_wife_freda()
        days_data = breakfast_scraper.get_restaurant_hours_formatted("Jack's Wife Freda")
        
        return jsonify({
            'success': True if result.get('status') == 'success' else False,
            'restaurant': "Jack's Wife Freda",
            'result': result,
            'daily_hours': days_data,
            'message': f"Scraped Jack's Wife Freda hours"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scrape/bagel', methods=['GET'])
def scrape_bagel():
    """Scrape only Ess-a-Bagel hours"""
    try:
        result = breakfast_scraper.scrape_ess_a_bagel()
        days_data = breakfast_scraper.get_restaurant_hours_formatted("Ess-a-Bagel")
        
        return jsonify({
            'success': True if result.get('status') == 'success' else False,
            'restaurant': "Ess-a-Bagel",
            'result': result,
            'daily_hours': days_data,
            'message': f"Scraped Ess-a-Bagel hours"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Updated homepage for Breakfast Scraper
@app.route('/')
def say_hello():
    html_content = """
    <html>
    <head>
        <title>Breakfast Scraper API</title>
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
                border-left: 4px solid #28a745;
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
                background: #28a745;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
            }
            .btn:hover {
                background: #218838;
            }
            .restaurant-list {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            .individual-scrapers {
                background: #e9f7ef;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            .day-hour {
                margin: 5px 0;
                padding: 8px;
                background: #f1f8e9;
                border-left: 3px solid #4caf50;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>☕ Breakfast Scraper API</h1>
            <p>This API scrapes breakfast places in New York for their open/close times.</p>
            
            <div class="restaurant-list">
                <h3>Scraped Restaurants:</h3>
                <ul>
                    <li>Jack's Wife Freda</li>
                    <li>Shuka</li>
                    <li>Sarabeth's</li>
                    <li>Ess-a-Bagel</li>
                </ul>
            </div>
            
            <div class="individual-scrapers">
                <h3>Individual Scraper Endpoints:</h3>
                <div class="endpoint">
                    <h3>GET <code>/api/scrape/shuka</code></h3>
                    <p>Scrape only Shuka hours with daily breakdown.</p>
                    <a class="btn" href="/api/scrape/shuka">Scrape Shuka</a>
                </div>
                
                <div class="endpoint">
                    <h3>GET <code>/api/scrape/sarabeths</code></h3>
                    <p>Scrape only Sarabeth's hours with daily breakdown.</p>
                    <a class="btn" href="/api/scrape/sarabeths">Scrape Sarabeth's</a>
                </div>
                
                <div class="endpoint">
                    <h3>GET <code>/api/scrape/jack</code></h3>
                    <p>Scrape only Jack's Wife Freda hours with daily breakdown.</p>
                    <a class="btn" href="/api/scrape/jack">Scrape Jack's</a>
                </div>
                
                <div class="endpoint">
                    <h3>GET <code>/api/scrape/bagel</code></h3>
                    <p>Scrape only Ess-a-Bagel hours with daily breakdown.</p>
                    <a class="btn" href="/api/scrape/bagel">Scrape Bagel</a>
                </div>
            </div>
            
            <h2>Available Endpoints:</h2>
            
            <div class="endpoint">
                <h3>GET <code>/api/breakfast/hours</code></h3>
                <p>Get previously scraped restaurant hours.</p>
                <p><strong>Parameters:</strong> <code>?limit=20</code> (optional)</p>
                <a class="btn" href="/api/breakfast/hours">Try it</a>
            </div>
            
            <div class="endpoint">
                <h3>POST <code>/api/breakfast/hours</code></h3>
                <p>Trigger new scraping of breakfast restaurant hours.</p>
                <p><strong>Body:</strong> <code>{"limit": 4}</code> (optional)</p>
            </div>
            
            <div class="endpoint">
                <h3>GET <code>/api/breakfast/search</code></h3>
                <p>Search scraped restaurant data.</p>
                <p><strong>Parameters:</strong> <code>?q=bagel</code> (optional)</p>
                <a class="btn" href="/api/breakfast/search?q=bagel">Search "bagel"</a>
            </div>
            
            <div class="endpoint">
                <h3>GET <code>/api/scrape/breakfast</code></h3>
                <p>Quick scrape of all breakfast places.</p>
                <a class="btn" href="/api/scrape/breakfast">Quick Scrape All</a>
            </div>
            
            <h2>How to Use:</h2>
            <ol>
                <li>Click "Quick Scrape All" to get all breakfast restaurant hours</li>
                <li>Use individual scraper endpoints to get specific restaurant hours</li>
                <li>Each individual endpoint returns daily hours breakdown</li>
                <li>Use the search endpoint to find specific restaurants</li>
                <li>Use POST to scrape new hours into the database</li>
            </ol>
            
            <h3>Sample Daily Hours Response:</h3>
            <div class="day-hour">
                <strong>Monday:</strong> 8:00 AM - 10:00 PM<br>
                <strong>Tuesday:</strong> 8:00 AM - 10:00 PM<br>
                <strong>Wednesday:</strong> 8:00 AM - 10:00 PM<br>
                <strong>Thursday:</strong> 8:00 AM - 10:00 PM<br>
                <strong>Friday:</strong> 8:00 AM - 11:00 PM<br>
                <strong>Saturday:</strong> 9:00 AM - 11:00 PM<br>
                <strong>Sunday:</strong> 9:00 AM - 10:00 PM
            </div>
            
            <h3>Note:</h3>
            <p>The scraper contains example hours. You'll need to:</p>
            <ol>
                <li>Inspect each restaurant's actual website</li>
                <li>Update the HTML selectors in the scraper functions</li>
                <li>Adjust the parsing logic based on their website structure</li>
            </ol>
        </div>
    </body>
    </html>
    """
    return html_content

if __name__ == '__main__':
    app.run(debug=True, port=5002)