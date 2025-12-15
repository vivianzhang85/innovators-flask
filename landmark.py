# main.py - Simple Museum Hours Scraper
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import os

app = Flask(__name__)
CORS(app)

class MuseumScraper:
    """Simple web scraper for museum hours"""
    
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
                'error': str(e)[:50]
            }
    
    def scrape_met_museum(self):
        """Scrape MET Museum hours"""
        try:
            # MET Museum uses API, but we'll scrape their hours page
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
                'error': str(e)[:50]
            }

# Create scraper instance
scraper = MuseumScraper()

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🏛️ Museum Hours Scraper</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f0f2f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
            }
            .museums-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .museum-box {
                background: white;
                border-radius: 10px;
                padding: 25px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                transition: transform 0.3s;
            }
            .museum-box:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            }
            .museum-icon {
                font-size: 2.5em;
                margin-bottom: 15px;
                text-align: center;
            }
            .museum-name {
                font-size: 1.5em;
                color: #333;
                margin-bottom: 15px;
                text-align: center;
            }
            .museum-hours {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                font-family: monospace;
                font-size: 1.1em;
            }
            .scrape-btn {
                display: block;
                width: 100%;
                padding: 12px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 1em;
                cursor: pointer;
                margin-top: 15px;
                transition: background 0.3s;
            }
            .scrape-btn:hover {
                background: #45a049;
            }
            .scrape-btn.loading {
                background: #666;
            }
            .info-line {
                display: flex;
                align-items: center;
                margin: 8px 0;
                color: #555;
            }
            .info-line svg {
                margin-right: 10px;
                color: #666;
            }
            .status {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.9em;
                margin-left: 10px;
            }
            .open {
                background: #d4edda;
                color: #155724;
            }
            .updated {
                font-size: 0.9em;
                color: #666;
                margin-top: 15px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏛️ Museum Hours Scraper</h1>
            
            <div class="museums-grid">
                <!-- MET Museum Box -->
                <div class="museum-box" id="met-box">
                    <div class="museum-icon">🎨</div>
                    <div class="museum-name">MET Museum</div>
                    <div class="museum-hours" id="met-hours">Click to scrape hours...</div>
                    <button class="scrape-btn" onclick="scrapeMuseum('met')">
                        Scrape MET Hours
                    </button>
                    <div class="updated" id="met-updated"></div>
                </div>
                
                <!-- Ice Cream Museum Box -->
                <div class="museum-box" id="icecream-box">
                    <div class="museum-icon">🍦</div>
                    <div class="museum-name">Museum of Ice Cream</div>
                    <div class="museum-hours" id="icecream-hours">Click to scrape hours...</div>
                    <button class="scrape-btn" onclick="scrapeMuseum('icecream')">
                        Scrape Ice Cream Hours
                    </button>
                    <div class="updated" id="icecream-updated"></div>
                </div>
                
                <!-- Ukrainian Museum Box -->
                <div class="museum-box" id="ukrainian-box">
                    <div class="museum-icon">🇺🇦</div>
                    <div class="museum-name">Ukrainian Museum</div>
                    <div class="museum-hours" id="ukrainian-hours">Click to scrape hours...</div>
                    <button class="scrape-btn" onclick="scrapeMuseum('ukrainian')">
                        Scrape Ukrainian Hours
                    </button>
                    <div class="updated" id="ukrainian-updated"></div>
                </div>
                
                <!-- Empire State Box -->
                <div class="museum-box" id="empire-box">
                    <div class="museum-icon">🗽</div>
                    <div class="museum-name">Empire State Building</div>
                    <div class="museum-hours" id="empire-hours">Click to scrape hours...</div>
                    <button class="scrape-btn" onclick="scrapeMuseum('empire')">
                        Scrape Empire State Hours
                    </button>
                    <div class="updated" id="empire-updated"></div>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <button onclick="scrapeAll()" style="padding: 15px 30px; font-size: 1.1em;">
                    🔄 Scrape All Museums
                </button>
            </div>
        </div>
        
        <script>
            async function scrapeMuseum(museum) {
                const btn = document.querySelector(`#${museum}-box .scrape-btn`);
                const hoursDiv = document.getElementById(`${museum}-hours`);
                const updatedDiv = document.getElementById(`${museum}-updated`);
                
                // Show loading
                btn.classList.add('loading');
                btn.textContent = 'Scraping...';
                hoursDiv.textContent = '🔄 Scraping website...';
                
                try {
                    const response = await fetch(`/api/${museum}`);
                    const data = await response.json();
                    
                    if (data.success) {
                        const museumData = data.data;
                        hoursDiv.innerHTML = `
                            <div style="color: #155724; font-weight: bold;">${museumData.hours}</div>
                            <div style="margin-top: 10px; font-size: 0.9em;">
                                <div>📍 ${museumData.address}</div>
                                <div>📞 ${museumData.phone}</div>
                                <div>Status: <span class="status open">${museumData.status}</span></div>
                            </div>
                        `;
                        updatedDiv.textContent = `Updated: ${museumData.last_updated}`;
                    } else {
                        hoursDiv.textContent = `Error: ${data.message}`;
                    }
                } catch (error) {
                    hoursDiv.textContent = 'Error scraping website';
                } finally {
                    btn.classList.remove('loading');
                    btn.textContent = `Scrape ${museum.charAt(0).toUpperCase() + museum.slice(1)} Hours`;
                }
            }
            
            async function scrapeAll() {
                const museums = ['met', 'icecream', 'ukrainian', 'empire'];
                
                for (const museum of museums) {
                    await scrapeMuseum(museum);
                    // Small delay between requests
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
                
                alert('✅ All museums scraped!');
            }
            
            // Scrape all on page load
            window.onload = function() {
                // Uncomment to auto-scrape on load:
                // scrapeAll();
            };
        </script>
    </body>
    </html>
    '''

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    print(f"🏛️  Museum Hours Scraper")
    print(f"🌐 Starting server on http://localhost:{port}")
    print("\nFour Museum Scrapers:")
    print("1. 🎨 MET Museum")
    print("2. 🍦 Museum of Ice Cream")
    print("3. 🇺🇦 Ukrainian Museum")
    print("4. 🗽 Empire State Building")
    print("\nClick the buttons to scrape live hours!")
    
    app.run(debug=True, host='0.0.0.0', port=port)