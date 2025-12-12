# imports from flask
from datetime import datetime
from urllib.parse import urljoin, urlparse
from flask import abort, redirect, render_template, request, send_from_directory, url_for, jsonify, current_app, g # import render_template from "public" flask libraries
from flask_login import current_user, login_user, logout_user
from flask.cli import AppGroup
from flask_login import current_user, login_required
from flask import current_app
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from api.jwt_authorize import token_required


# import "objects" from "this" project
from __init__ import app, db, login_manager  # Key Flask objects 
# API endpoints
from api.user import user_api 
from api.python_exec_api import python_exec_api
from api.javascript_exec_api import javascript_exec_api
from api.section import section_api
from api.pfp import pfp_api
from api.stock import stock_api
from api.analytics import analytics_api
from api.student import student_api
from api.groq_api import groq_api
from api.gemini_api import gemini_api
from api.microblog_api import microblog_api
from api.classroom_api import classroom_api
from hacks.joke import joke_api  # Import the joke API blueprint
from api.post import post_api  # Import the social media post API
#from api.announcement import announcement_api ##temporary revert

# database Initialization functions
from model.user import User, initUsers
from model.user import Section;
from model.github import GitHubUser
from model.feedback import Feedback
from api.analytics import get_date_range
# from api.grade_api import grade_api
from api.study import study_api
from api.feedback_api import feedback_api
from model.study import Study, initStudies
from model.classroom import Classroom
from model.post import Post, init_posts
from model.microblog import MicroBlog, Topic, init_microblogs
from hacks.jokes import initJokes 
# from model.announcement import Announcement ##temporary revert

# server only Views

import os
import requests

# Load environment variables
load_dotenv()

app.config['KASM_SERVER'] = os.getenv('KASM_SERVER')
app.config['KASM_API_KEY'] = os.getenv('KASM_API_KEY')
app.config['KASM_API_KEY_SECRET'] = os.getenv('KASM_API_KEY_SECRET')



# register URIs for api endpoints
app.register_blueprint(python_exec_api)
app.register_blueprint(javascript_exec_api)
app.register_blueprint(user_api)
app.register_blueprint(section_api)
app.register_blueprint(pfp_api) 
app.register_blueprint(stock_api)
app.register_blueprint(groq_api)
app.register_blueprint(gemini_api)
app.register_blueprint(microblog_api)

app.register_blueprint(analytics_api)
app.register_blueprint(student_api)
# app.register_blueprint(grade_api)
app.register_blueprint(study_api)
app.register_blueprint(classroom_api)
app.register_blueprint(feedback_api)
app.register_blueprint(joke_api)  # Register the joke API blueprint
app.register_blueprint(post_api)  # Register the social media post API
# app.register_blueprint(announcement_api) ##temporary revert

# Jokes file initialization
with app.app_context():
    initJokes()

# Tell Flask-Login the view function name of your login route
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login', next=request.path))

# register URIs for server pages
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Helper function to check if the URL is safe for redirects
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_page = request.args.get('next', '') or request.form.get('next', '')
    if request.method == 'POST':
        user = User.query.filter_by(_uid=request.form['username']).first()
        if user and user.is_password(request.form['password']):
            login_user(user)
            if not is_safe_url(next_page):
                return abort(400)
            return redirect(next_page or url_for('index'))
        else:
            error = 'Invalid username or password.'
    return render_template("login.html", error=error, next=next_page)

@app.route('/studytracker')  # route for the study tracker page
def studytracker():
    return render_template("studytracker.html")
    
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.errorhandler(404)  # catch for URL not found
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.route('/')  # connects default URL to index() function
def index():
    print("Home:", current_user)
    return render_template("index.html")



@app.route('/users/table2')
@login_required
def u2table():
    users = User.query.all()
    return render_template("u2table.html", user_data=users)

@app.route('/sections/')
@login_required
def sections():
    sections = Section.query.all()
    return render_template("sections.html", sections=sections)

# Helper function to extract uploads for a user (ie PFP image)
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
 
@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.delete()
        return jsonify({'message': 'User deleted successfully'}), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Set the new password
    if user.update({"password": app.config['DEFAULT_PASSWORD']}):
        return jsonify({'message': 'Password reset successfully'}), 200
    return jsonify({'error': 'Password reset failed'}), 500

@app.route('/kasm_users')
def kasm_users():
    # Fetch configuration details from environment or app config
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    # Validate required configurations
    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return render_template('error.html', message='KASM keys are missing'), 400

    try:
        # Prepare API request details
        url = f"{SERVER}/api/public/get_users"
        data = {
            "api_key": API_KEY,
            "api_key_secret": API_KEY_SECRET
        }

        # Perform the POST request
        response = requests.post(url, json=data, timeout=10)  # Added timeout for reliability

        # Validate the API response
        if response.status_code != 200:
            return render_template(
                'error.html', 
                message='Failed to get users', 
                code=response.status_code
            ), response.status_code

        # Parse the users list from the response
        users = response.json().get('users', [])

        # Process `last_session` and handle potential parsing issues
        for user in users:
            last_session = user.get('last_session')
            try:
                user['last_session'] = datetime.fromisoformat(last_session) if last_session else None
            except ValueError:
                user['last_session'] = None  # Fallback for invalid date formats

        # Sort users by `last_session`, treating `None` as the oldest date
        sorted_users = sorted(
            users, 
            key=lambda x: x['last_session'] or datetime.min, 
            reverse=True
        )

        # Render the sorted users in the template
        return render_template('kasm_users.html', users=sorted_users)

    except requests.RequestException as e:
        # Handle connection errors or other request exceptions
        return render_template(
            'error.html', 
            message=f"Error connecting to KASM API: {str(e)}"
        ), 500
        
        
@app.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user_kasm(user_id):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return {'message': 'KASM keys are missing'}, 400

    try:
        # Kasm API to delete a user
        url = f"{SERVER}/api/public/delete_user"
        data = {
            "api_key": API_KEY,
            "api_key_secret": API_KEY_SECRET,
            "target_user": {"user_id": user_id},
            "force": False
        }
        response = requests.post(url, json=data)

        if response.status_code == 200:
            return {'message': 'User deleted successfully'}, 200
        else:
            return {'message': 'Failed to delete user'}, response.status_code

    except requests.RequestException as e:
        return {'message': 'Error connecting to KASM API', 'error': str(e)}, 500


@app.route('/update_user/<string:uid>', methods=['PUT'])
def update_user(uid):
    # Authorization check
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403

    # Get the JSON data from the request
    data = request.get_json()
    print(f"Request Data: {data}")  # Log the incoming data

    # Find the user in the database
    user = User.query.filter_by(_uid=uid).first()
    if user:
        print(f"Found user: {user.uid}")  # Log the found user's UID
        
        # Update the user using the provided data
        user.update(data)  # Assuming `user.update(data)` is a method on your User model
        
        # Save changes to the database
        return jsonify({"message": "User updated successfully."}), 200
    else:
        print("User not found.")  # Log when user is not found
        return jsonify({"message": "User not found."}), 404

# ============================================================================
# MUSEUM HOURS SCRAPER - Simple Museum Hours Scraper
# ============================================================================

from flask_cors import CORS
from bs4 import BeautifulSoup
import re

# Enable CORS for the museum scraper routes
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

# Museum scraper route
@app.route('/museums')
def museums_home():
    '''Main museum scraper interface'''
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
            .back-btn {
                display: inline-block;
                padding: 10px 20px;
                background: #6c757d;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-bottom: 20px;
                transition: background 0.3s;
            }
            .back-btn:hover {
                background: #5a6268;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Main App</a>
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
                    const response = await fetch(`/api/museums/${museum}`);
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
        </script>
    </body>
    </html>
    '''

# API endpoints for each museum
@app.route('/api/museums/met')
def get_met_hours():
    data = scraper.scrape_met_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/museums/icecream')
def get_icecream_hours():
    data = scraper.scrape_ice_cream_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/museums/ukrainian')
def get_ukrainian_hours():
    data = scraper.scrape_ukrainian_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/museums/empire')
def get_empire_hours():
    data = scraper.scrape_empire_state()
    return jsonify({'success': True, 'data': data})

@app.route('/api/museums/all')
def get_all_museum_hours():
    data = {
        'met': scraper.scrape_met_museum(),
        'icecream': scraper.scrape_ice_cream_museum(),
        'ukrainian': scraper.scrape_ukrainian_museum(),
        'empire': scraper.scrape_empire_state(),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return jsonify({'success': True, 'data': data})

# Create an AppGroup for custom commands
custom_cli = AppGroup('custom', help='Custom commands')

# Define a command to run the data generation functions
@custom_cli.command('generate_data')
def generate_data():
    initUsers()
    init_microblogs()

# Register the custom command group with the Flask application
app.cli.add_command(custom_cli)
        
# this runs the flask application on the development server
if __name__ == "__main__":
    host = "0.0.0.0"
    port = app.config['FLASK_PORT']
    print(f"** Server running: http://localhost:{port}")
    print(f"** Museum Scraper: http://localhost:{port}/museums")
    app.run(debug=True, host=host, port=port, use_reloader=False)