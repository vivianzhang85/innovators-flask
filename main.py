# main.py - Simple Museum Hours Scraper
from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os

app = Flask(__name__)
# Allow ALL origins for your frontend
CORS(app, resources={r"/*": {"origins": "*"}})

class MuseumScraper:
    """Simple web scraper for museum hours"""
    
    def scrape_met_museum(self):
        """Scrape MET Museum hours"""
        try:
            url = "https://www.metmuseum.org/visit/plan-your-visit/metropolitan-museum-of-art"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Sun-Thu: 10:00 AM - 5:30 PM, Fri-Sat: 10:00 AM - 9:00 PM"
            
            # Look for hours in MET page
            hour_sections = soup.find_all(['p', 'div', 'span'], text=re.compile(r'[Hh]ours?|[Oo]pen|[Cc]losed'))
            for section in hour_sections:
                text = section.get_text()
                if '10' in text and ('AM' in text or 'PM' in text):
                    hours = text.strip()[:150]
                    break
            
            return {
                'museum': 'MET Museum',
                'hours': hours,
                'address': '1000 5th Ave, New York, NY 10028',
                'phone': '(212) 535-7710',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p")
            }
            
        except Exception as e:
            return {
                'museum': 'MET Museum',
                'hours': 'Sun-Thu: 10:00 AM - 5:30 PM, Fri-Sat: 10:00 AM - 9:00 PM',
                'address': '1000 5th Ave, New York, NY 10028',
                'phone': '(212) 535-7710',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:50]
            }
    
    def scrape_ice_cream_museum(self):
        """Scrape Museum of Ice Cream hours"""
        try:
            url = "https://www.museumoficecream.com/new-york"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for hours
            hours = "Mon-Sun: 10:00 AM - 9:00 PM"
            all_text = soup.get_text().lower()
            
            if 'hour' in all_text or 'open' in all_text:
                # Find text around hour mentions
                hour_match = re.search(r'([A-Za-z]{3,9}[-\s]*\d{1,2}(?::\d{2})?\s*[APap][Mm]\s*[-–]\s*\d{1,2}(?::\d{2})?\s*[APap][Mm])', soup.get_text())
                if hour_match:
                    hours = hour_match.group(1)
            
            return {
                'museum': 'Museum of Ice Cream',
                'hours': hours,
                'address': '558 Broadway, New York, NY 10012',
                'phone': '(646) 459-3515',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p")
            }
            
        except Exception as e:
            return {
                'museum': 'Museum of Ice Cream',
                'hours': 'Mon-Sun: 10:00 AM - 9:00 PM',
                'address': '558 Broadway, New York, NY 10012',
                'phone': '(646) 459-3515',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:50]
            }
    
    def scrape_ukrainian_museum(self):
        """Scrape Ukrainian Museum hours"""
        try:
            url = "https://www.ukrainianmuseum.org/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Wed-Sun: 11:30 AM - 5:00 PM"
            
            # Common hour patterns
            patterns = [
                r'[Hh]ours?[:\s]*([^\n]{10,100})',
                r'[Oo]pen[:\s]*([^\n]{10,100})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, soup.get_text())
                if match:
                    hours = match.group(1).strip()[:100]
                    break
            
            return {
                'museum': 'Ukrainian Museum',
                'hours': hours,
                'address': '222 East 6th Street, New York, NY 10003',
                'phone': '(212) 228-0110',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p")
            }
            
        except Exception as e:
            return {
                'museum': 'Ukrainian Museum',
                'hours': 'Wed-Sun: 11:30 AM - 5:00 PM',
                'address': '222 East 6th Street, New York, NY 10003',
                'phone': '(212) 228-0110',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:50]
            }
    
    def scrape_empire_state(self):
        """Scrape Empire State Building hours"""
        try:
            url = "https://www.esbnyc.com/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Daily: 8:00 AM - 2:00 AM"
            
            # Empire State hours often visible
            hour_text = soup.get_text()
            hour_match = re.search(r'(\d{1,2}(?::\d{2})?\s*[APap][Mm]\s*[-–]\s*\d{1,2}(?::\d{2})?\s*[APap][Mm])', hour_text)
            if hour_match:
                hours = f"Daily: {hour_match.group(1)}"
            
            return {
                'museum': 'Empire State Building',
                'hours': hours,
                'address': '20 W 34th St, New York, NY 10001',
                'phone': '(212) 736-3100',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p")
            }
            
        except Exception as e:
            return {
                'museum': 'Empire State Building',
                'hours': 'Daily: 8:00 AM - 2:00 AM',
                'address': '20 W 34th St, New York, NY 10001',
                'phone': '(212) 736-3100',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:50]
            }

# Create scraper instance
scraper = MuseumScraper()

# API endpoints for each museum
@app.route('/api/met')
def get_met_hours():
    data = scraper.scrape_met_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/icecream')
def get_icecream_hours():
    data = scraper.scrape_ice_cream_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/ukrainian')
def get_ukrainian_hours():
    data = scraper.scrape_ukrainian_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/empire')
def get_empire_hours():
    data = scraper.scrape_empire_state()
    return jsonify({'success': True, 'data': data})

@app.route('/api/all')
def get_all_hours():
    data = {
        'met': scraper.scrape_met_museum(),
        'icecream': scraper.scrape_ice_cream_museum(),
        'ukrainian': scraper.scrape_ukrainian_museum(),
        'empire': scraper.scrape_empire_state(),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return jsonify({'success': True, 'data': data})

# Test endpoint to check if API is working
@app.route('/api/test')
def test_api():
    return jsonify({
        'success': True,
        'message': 'Museum Hours API is running!',
        'endpoints': {
            '/api/met': 'MET Museum hours',
            '/api/icecream': 'Ice Cream Museum hours',
            '/api/ukrainian': 'Ukrainian Museum hours',
            '/api/empire': 'Empire State Building hours',
            '/api/all': 'All museums at once'
        }
    })

# Simple HTML page for testing
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Museum Hours API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .test-btn { background: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>🏛️ Museum Hours Scraper API</h1>
        <p>This API provides live museum hours. Use these endpoints:</p>
        
        <div class="endpoint">
            <strong>GET /api/met</strong> - MET Museum hours
            <button class="test-btn" onclick="testEndpoint('/api/met')">Test</button>
        </div>
        
        <div class="endpoint">
            <strong>GET /api/icecream</strong> - Ice Cream Museum hours
            <button class="test-btn" onclick="testEndpoint('/api/icecream')">Test</button>
        </div>
        
        <div class="endpoint">
            <strong>GET /api/ukrainian</strong> - Ukrainian Museum hours
            <button class="test-btn" onclick="testEndpoint('/api/ukrainian')">Test</button>
        </div>
        
        <div class="endpoint">
            <strong>GET /api/empire</strong> - Empire State Building hours
            <button class="test-btn" onclick="testEndpoint('/api/empire')">Test</button>
        </div>
        
        <div class="endpoint">
            <strong>GET /api/all</strong> - All museums at once
            <button class="test-btn" onclick="testEndpoint('/api/all')">Test</button>
        </div>
        
        <div id="result" style="margin-top: 20px; padding: 15px; background: #e8f4f8; border-radius: 5px; display: none;"></div>
        
        <script>
            async function testEndpoint(endpoint) {
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = 'Testing...';
                
                try {
                    const response = await fetch(endpoint);
                    const data = await response.json();
                    resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    resultDiv.innerHTML = 'Error: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    print("=" * 50)
    print("🏛️  Museum Hours Scraper API")
    print("=" * 50)
    print(f"📡 Server running on: http://localhost:{port}")
    print(f"🔗 Test page: http://localhost:{port}/")
    print("\n📋 Available Endpoints:")
    print("  • http://localhost:5002/api/met")
    print("  • http://localhost:5002/api/icecream")
    print("  • http://localhost:5002/api/ukrainian")
    print("  • http://localhost:5002/api/empire")
    print("  • http://localhost:5002/api/all")
    print("  • http://localhost:5002/api/test")
    print("\n⚡ Ready to serve live museum hours to your frontend!")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=port)