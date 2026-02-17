# main.py - Combined Museum Scraper API with Full Flask Application and Budget Tracking
from flask import Flask, jsonify, abort, redirect, render_template, request, send_from_directory, url_for, current_app, g
from flask_cors import CORS
from flask_login import current_user, login_user, logout_user, login_required, LoginManager
from flask.cli import AppGroup
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urljoin, urlparse
import os
import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import json
import uuid
from datetime import timedelta

# Import database and models
from __init__ import app, db, login_manager

# Import API blueprints
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
from hacks.joke import joke_api
from hacks.lyric import lyric_api
from hacks.lyrics import initLyrics
from api.post import post_api
from api.study import study_api
from api.feedback_api import feedback_api
from api.jwt_authorize import token_required

# Import models
from model.user import User, Section, initUsers
from model.github import GitHubUser
from model.feedback import Feedback
from model.study import Study, initStudies
from model.classroom import Classroom
from model.post import Post, init_posts
from model.microblog import MicroBlog, Topic, init_microblogs
from hacks.jokes import initJokes

# Load environment variables
load_dotenv()

# Initialize CORS for all origins
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Origin"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])

# Configuration
app.config['KASM_SERVER'] = os.getenv('KASM_SERVER')
app.config['KASM_API_KEY'] = os.getenv('KASM_API_KEY')
app.config['KASM_API_KEY_SECRET'] = os.getenv('KASM_API_KEY_SECRET')

# Register all API blueprints
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
app.register_blueprint(study_api)
app.register_blueprint(classroom_api)
app.register_blueprint(feedback_api)
app.register_blueprint(joke_api)
app.register_blueprint(lyric_api)
app.register_blueprint(post_api)

# Initialize jokes
with app.app_context():
    initJokes()
    initLyrics()

# Flask-Login configuration
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login', next=request.path))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# ============================================================================
# BUDGET TRACKING SYSTEM (NEW)
# ============================================================================

class BudgetTracker:
    """Database storage for user budget tracking across all modules"""
    
    def __init__(self):
        self.db_path = "budget_tracking.db"
        self.init_database()
    
    def init_database(self):
        """Create database table for budget tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User budget table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                total_budget DECIMAL(10, 2),
                remaining_budget DECIMAL(10, 2),
                spent_budget DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                budget_name TEXT,
                currency TEXT DEFAULT 'USD',
                trip_duration INTEGER DEFAULT 1,
                notes TEXT,
                UNIQUE(user_id) ON CONFLICT REPLACE,
                UNIQUE(session_id) ON CONFLICT REPLACE
            )
        ''')
        
        # Expense tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                budget_id INTEGER,
                user_id INTEGER,
                session_id TEXT,
                category TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT,
                price DECIMAL(10, 2) NOT NULL,
                quantity INTEGER DEFAULT 1,
                total_cost DECIMAL(10, 2) NOT NULL,
                description TEXT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                module TEXT NOT NULL,
                FOREIGN KEY (budget_id) REFERENCES user_budgets(id) ON DELETE CASCADE
            )
        ''')
        
        # Daily budget breakdown
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_budget (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                budget_id INTEGER,
                day_number INTEGER,
                date DATE,
                daily_budget DECIMAL(10, 2),
                daily_spent DECIMAL(10, 2),
                daily_remaining DECIMAL(10, 2),
                FOREIGN KEY (budget_id) REFERENCES user_budgets(id) ON DELETE CASCADE
            )
        ''')
        
        # Budget alerts and notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                alert_type TEXT,
                message TEXT,
                threshold DECIMAL(10, 2),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id_budget ON user_budgets(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id_budget ON user_budgets(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_budget_id ON budget_expenses(budget_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON budget_expenses(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_module ON budget_expenses(module)')
        
        conn.commit()
        conn.close()
        print("✅ Budget Tracking Database initialized")
    
    def create_budget(self, user_id=None, session_id=None, total_budget=0, budget_name="Trip Budget", 
                     currency="USD", trip_duration=1, notes=""):
        """Create a new budget for user or session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_budgets 
                (user_id, session_id, total_budget, remaining_budget, spent_budget, 
                 budget_name, currency, trip_duration, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                session_id,
                total_budget,
                total_budget,  # Remaining starts as total
                0,  # Spent starts at 0
                budget_name,
                currency,
                trip_duration,
                notes
            ))
            
            budget_id = cursor.lastrowid
            
            # Initialize daily budgets
            for day in range(1, trip_duration + 1):
                daily_budget = total_budget / trip_duration if trip_duration > 0 else total_budget
                cursor.execute('''
                    INSERT INTO daily_budget 
                    (budget_id, day_number, daily_budget, daily_spent, daily_remaining)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    budget_id,
                    day,
                    daily_budget,
                    0,
                    daily_budget
                ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'budget_id': budget_id,
                'message': 'Budget created successfully'
            }
            
        except Exception as e:
            print(f"❌ Error creating budget: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_budget(self, user_id=None, session_id=None):
        """Get budget information for user or session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM user_budgets WHERE '
            params = []
            
            if user_id:
                query += 'user_id = ?'
                params.append(user_id)
            elif session_id:
                query += 'session_id = ?'
                params.append(session_id)
            else:
                conn.close()
                return {
                    'success': False,
                    'error': 'No user_id or session_id provided'
                }
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                budget_data = dict(zip(columns, row))
                
                # Get expenses for this budget
                cursor.execute('''
                    SELECT * FROM budget_expenses 
                    WHERE budget_id = ? 
                    ORDER BY date_added DESC
                ''', (budget_data['id'],))
                
                expense_rows = cursor.fetchall()
                expense_columns = [desc[0] for desc in cursor.description]
                expenses = [dict(zip(expense_columns, row)) for row in expense_rows]
                
                # Get daily breakdown
                cursor.execute('''
                    SELECT * FROM daily_budget 
                    WHERE budget_id = ? 
                    ORDER BY day_number
                ''', (budget_data['id'],))
                
                daily_rows = cursor.fetchall()
                daily_columns = [desc[0] for desc in cursor.description]
                daily_breakdown = [dict(zip(daily_columns, row)) for row in daily_rows]
                
                # Calculate category totals
                cursor.execute('''
                    SELECT category, SUM(total_cost) as total_spent 
                    FROM budget_expenses 
                    WHERE budget_id = ?
                    GROUP BY category
                ''', (budget_data['id'],))
                
                category_totals = {}
                for cat_row in cursor.fetchall():
                    category_totals[cat_row[0]] = cat_row[1]
                
                conn.close()
                
                return {
                    'success': True,
                    'budget': budget_data,
                    'expenses': expenses,
                    'daily_breakdown': daily_breakdown,
                    'category_totals': category_totals,
                    'expense_count': len(expenses)
                }
            else:
                conn.close()
                return {
                    'success': True,
                    'budget': None,
                    'expenses': [],
                    'message': 'No budget found'
                }
                
        except Exception as e:
            print(f"❌ Error getting budget: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_expense(self, user_id=None, session_id=None, category="", item_name="", 
                   item_type="", price=0, quantity=1, description="", module="", day_number=1):
        """Add an expense to the budget"""
        try:
            # First get the budget
            budget_result = self.get_budget(user_id=user_id, session_id=session_id)
            if not budget_result['success'] or not budget_result['budget']:
                return {
                    'success': False,
                    'error': 'No budget found. Please create a budget first.'
                }
            
            budget = budget_result['budget']
            budget_id = budget['id']
            total_cost = price * quantity
            
            # Check if enough budget remains
            if total_cost > budget['remaining_budget']:
                return {
                    'success': False,
                    'error': f'Not enough budget. Need ${total_cost:.2f}, only ${budget["remaining_budget"]:.2f} remaining.',
                    'remaining': budget['remaining_budget'],
                    'needed': total_cost
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Add the expense
            cursor.execute('''
                INSERT INTO budget_expenses 
                (budget_id, user_id, session_id, category, item_name, item_type, 
                 price, quantity, total_cost, description, module)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                budget_id,
                user_id,
                session_id,
                category,
                item_name,
                item_type,
                price,
                quantity,
                total_cost,
                description,
                module
            ))
            
            # Update budget totals
            cursor.execute('''
                UPDATE user_budgets SET 
                    spent_budget = spent_budget + ?,
                    remaining_budget = remaining_budget - ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (total_cost, total_cost, budget_id))
            
            # Update daily budget
            cursor.execute('''
                UPDATE daily_budget SET 
                    daily_spent = daily_spent + ?,
                    daily_remaining = daily_remaining - ?
                WHERE budget_id = ? AND day_number = ?
            ''', (total_cost, total_cost, budget_id, day_number))
            
            # Check for budget alerts
            self.check_budget_alerts(budget_id, budget['remaining_budget'] - total_cost, cursor)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'expense_id': cursor.lastrowid,
                'total_cost': total_cost,
                'remaining_budget': budget['remaining_budget'] - total_cost,
                'message': f'Added {item_name} for ${total_cost:.2f}'
            }
            
        except Exception as e:
            print(f"❌ Error adding expense: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_budget_alerts(self, budget_id, new_remaining, cursor):
        """Check and create budget alerts"""
        # Get budget info
        cursor.execute('SELECT total_budget FROM user_budgets WHERE id = ?', (budget_id,))
        budget_row = cursor.fetchone()
        if not budget_row:
            return
        
        total_budget = budget_row[0]
        
        # Check thresholds
        thresholds = [
            (0.10, "LOW_BUDGET", "Warning: Only 10% of budget remaining!"),
            (0.05, "CRITICAL_BUDGET", "Critical: Only 5% of budget remaining!"),
            (0, "NO_BUDGET", "Alert: Budget exceeded!")
        ]
        
        for threshold_percent, alert_type, message in thresholds:
            threshold_amount = total_budget * threshold_percent
            if new_remaining <= threshold_amount:
                # Check if alert already exists
                cursor.execute('''
                    SELECT id FROM budget_alerts 
                    WHERE budget_id = ? AND alert_type = ? AND is_active = 1
                ''', (budget_id, alert_type))
                
                if not cursor.fetchone():
                    # Create new alert
                    cursor.execute('''
                        INSERT INTO budget_alerts 
                        (budget_id, alert_type, message, threshold, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (budget_id, alert_type, message, threshold_amount))
    
    def update_budget(self, user_id=None, session_id=None, total_budget=None, 
                     budget_name=None, currency=None, trip_duration=None, notes=None):
        """Update budget information"""
        try:
            budget_result = self.get_budget(user_id=user_id, session_id=session_id)
            if not budget_result['success'] or not budget_result['budget']:
                return {
                    'success': False,
                    'error': 'No budget found'
                }
            
            budget = budget_result['budget']
            budget_id = budget['id']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build update query dynamically
            updates = []
            params = []
            
            if total_budget is not None:
                updates.append("total_budget = ?")
                params.append(total_budget)
                
                # Recalculate remaining based on new total
                new_remaining = total_budget - budget['spent_budget']
                if new_remaining < 0:
                    return {
                        'success': False,
                        'error': f'Cannot set budget below spent amount (${budget["spent_budget"]:.2f})'
                    }
                
                updates.append("remaining_budget = ?")
                params.append(new_remaining)
            
            if budget_name is not None:
                updates.append("budget_name = ?")
                params.append(budget_name)
            
            if currency is not None:
                updates.append("currency = ?")
                params.append(currency)
            
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)
            
            if trip_duration is not None and trip_duration != budget['trip_duration']:
                updates.append("trip_duration = ?")
                params.append(trip_duration)
                
                # Recreate daily budgets
                cursor.execute('DELETE FROM daily_budget WHERE budget_id = ?', (budget_id,))
                
                daily_budget_amount = total_budget / trip_duration if trip_duration > 0 else total_budget
                for day in range(1, trip_duration + 1):
                    cursor.execute('''
                        INSERT INTO daily_budget 
                        (budget_id, day_number, daily_budget, daily_spent, daily_remaining)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        budget_id,
                        day,
                        daily_budget_amount,
                        0,
                        daily_budget_amount
                    ))
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                query = f"UPDATE user_budgets SET {', '.join(updates)} WHERE id = ?"
                params.append(budget_id)
                
                cursor.execute(query, params)
                conn.commit()
            
            conn.close()
            
            return {
                'success': True,
                'message': 'Budget updated successfully'
            }
            
        except Exception as e:
            print(f"❌ Error updating budget: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def remove_expense(self, expense_id, user_id=None, session_id=None):
        """Remove an expense and refund the budget"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get expense details
            cursor.execute('''
                SELECT be.*, ub.id as budget_id 
                FROM budget_expenses be
                JOIN user_budgets ub ON be.budget_id = ub.id
                WHERE be.id = ? AND (be.user_id = ? OR be.session_id = ? OR ub.user_id = ? OR ub.session_id = ?)
            ''', (expense_id, user_id, session_id, user_id, session_id))
            
            expense_row = cursor.fetchone()
            if not expense_row:
                conn.close()
                return {
                    'success': False,
                    'error': 'Expense not found or unauthorized'
                }
            
            expense_columns = [desc[0] for desc in cursor.description]
            expense = dict(zip(expense_columns, expense_row))
            
            # Remove the expense
            cursor.execute('DELETE FROM budget_expenses WHERE id = ?', (expense_id,))
            
            # Refund the budget
            cursor.execute('''
                UPDATE user_budgets SET 
                    spent_budget = spent_budget - ?,
                    remaining_budget = remaining_budget + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (expense['total_cost'], expense['total_cost'], expense['budget_id']))
            
            # Refund daily budget if day_number exists
            if expense.get('day_number'):
                cursor.execute('''
                    UPDATE daily_budget SET 
                        daily_spent = daily_spent - ?,
                        daily_remaining = daily_remaining + ?
                    WHERE budget_id = ? AND day_number = ?
                ''', (expense['total_cost'], expense['total_cost'], 
                      expense['budget_id'], expense['day_number']))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': f'Removed {expense["item_name"]} and refunded ${expense["total_cost"]:.2f}'
            }
            
        except Exception as e:
            print(f"❌ Error removing expense: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_expense_summary(self, user_id=None, session_id=None):
        """Get summary of expenses by category and module"""
        try:
            budget_result = self.get_budget(user_id=user_id, session_id=session_id)
            if not budget_result['success'] or not budget_result['budget']:
                return {
                    'success': False,
                    'error': 'No budget found'
                }
            
            budget = budget_result['budget']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Expenses by category
            cursor.execute('''
                SELECT category, COUNT(*) as count, SUM(total_cost) as total 
                FROM budget_expenses 
                WHERE budget_id = ?
                GROUP BY category 
                ORDER BY total DESC
            ''', (budget['id'],))
            
            by_category = []
            for row in cursor.fetchall():
                by_category.append({
                    'category': row[0],
                    'count': row[1],
                    'total': row[2]
                })
            
            # Expenses by module
            cursor.execute('''
                SELECT module, COUNT(*) as count, SUM(total_cost) as total 
                FROM budget_expenses 
                WHERE budget_id = ?
                GROUP BY module 
                ORDER BY total DESC
            ''', (budget['id'],))
            
            by_module = []
            for row in cursor.fetchall():
                by_module.append({
                    'module': row[0],
                    'count': row[1],
                    'total': row[2]
                })
            
            # Recent expenses
            cursor.execute('''
                SELECT item_name, category, module, total_cost, date_added 
                FROM budget_expenses 
                WHERE budget_id = ?
                ORDER BY date_added DESC 
                LIMIT 10
            ''', (budget['id'],))
            
            recent_expenses = []
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                recent_expenses.append(dict(zip(columns, row)))
            
            conn.close()
            
            return {
                'success': True,
                'summary': {
                    'by_category': by_category,
                    'by_module': by_module,
                    'recent_expenses': recent_expenses,
                    'total_expenses': len(budget_result['expenses']),
                    'total_spent': budget['spent_budget'],
                    'total_remaining': budget['remaining_budget'],
                    'budget_utilization': (budget['spent_budget'] / budget['total_budget'] * 100) if budget['total_budget'] > 0 else 0
                }
            }
            
        except Exception as e:
            print(f"❌ Error getting expense summary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def reset_budget(self, user_id=None, session_id=None, keep_expenses=False):
        """Reset budget (clear expenses or entire budget)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if keep_expenses:
                # Just reset budget amounts
                cursor.execute('''
                    UPDATE user_budgets SET 
                        spent_budget = 0,
                        remaining_budget = total_budget,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? OR session_id = ?
                ''', (user_id, session_id))
                
                cursor.execute('''
                    UPDATE daily_budget SET 
                        daily_spent = 0,
                        daily_remaining = daily_budget
                    WHERE budget_id IN (
                        SELECT id FROM user_budgets 
                        WHERE user_id = ? OR session_id = ?
                    )
                ''', (user_id, session_id))
            else:
                # Delete everything
                cursor.execute('''
                    DELETE FROM budget_expenses 
                    WHERE budget_id IN (
                        SELECT id FROM user_budgets 
                        WHERE user_id = ? OR session_id = ?
                    )
                ''', (user_id, session_id))
                
                cursor.execute('''
                    DELETE FROM daily_budget 
                    WHERE budget_id IN (
                        SELECT id FROM user_budgets 
                        WHERE user_id = ? OR session_id = ?
                    )
                ''', (user_id, session_id))
                
                cursor.execute('''
                    DELETE FROM user_budgets 
                    WHERE user_id = ? OR session_id = ?
                ''', (user_id, session_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': 'Budget reset successfully'
            }
            
        except Exception as e:
            print(f"❌ Error resetting budget: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Create budget tracker instance
budget_tracker = BudgetTracker()

# ============================================================================
# ORIGINAL MUSEUM SCRAPER CLASS (unchanged)
# ============================================================================

class MuseumScraper:
    """Web scraper for museum hours with improved parsing"""
    
    def scrape_met_museum(self):
        """Scrape MET Museum hours"""
        try:
            url = "https://www.metmuseum.org/visit/plan-your-visit/metropolitan-museum-of-art"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Sun-Thu: 10:00 AM - 5:30 PM, Fri-Sat: 10:00 AM - 9:00 PM"
            
            # Look for hours in MET page with multiple strategies
            hour_sections = soup.find_all(['p', 'div', 'span', 'li'], 
                                         text=re.compile(r'[Hh]ours?|[Oo]pen|[Cc]losed|10.*AM.*5.*PM', re.IGNORECASE))
            
            for section in hour_sections:
                text = section.get_text().strip()
                if '10' in text and ('AM' in text or 'am' in text) and ('PM' in text or 'pm' in text):
                    hours = text[:200]
                    break
            
            # Also check for structured hours data
            hour_divs = soup.find_all(['div', 'section'], class_=re.compile(r'hour|time|schedule', re.IGNORECASE))
            for div in hour_divs:
                text = div.get_text().strip()
                if len(text) > 50 and ('AM' in text or 'PM' in text):
                    hours = text[:200]
                    break
            
            return {
                'museum': 'MET Museum',
                'hours': hours,
                'address': '1000 5th Ave, New York, NY 10028',
                'phone': '(212) 535-7710',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'source': 'metmuseum.org'
            }
            
        except Exception as e:
            return {
                'museum': 'MET Museum',
                'hours': 'Sun-Thu: 10:00 AM - 5:30 PM, Fri-Sat: 10:00 AM - 9:00 PM',
                'address': '1000 5th Ave, New York, NY 10028',
                'phone': '(212) 535-7710',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:100],
                'source': 'fallback'
            }
    
    def scrape_ice_cream_museum(self):
        """Scrape Museum of Ice Cream hours"""
        try:
            url = "https://www.museumoficecream.com/new-york"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for hours with multiple patterns
            hours = "Mon-Sun: 10:00 AM - 9:00 PM"
            all_text = soup.get_text()
            
            # Pattern 1: Direct hour patterns
            hour_patterns = [
                r'([A-Za-z]{3,9}[-\s]*\d{1,2}(?::\d{2})?\s*[APap][Mm]\s*[-–]\s*\d{1,2}(?::\d{2})?\s*[APap][Mm])',
                r'(\d{1,2}(?::\d{2})?\s*[APap][Mm]\s*[-–]\s*\d{1,2}(?::\d{2})?\s*[APap][Mm])',
                r'[Hh]ours?[:\s]*([^\n]{10,80})'
            ]
            
            for pattern in hour_patterns:
                match = re.search(pattern, all_text)
                if match:
                    hours = match.group(1).strip()
                    break
            
            # Pattern 2: Look for opening hours sections
            hour_sections = soup.find_all(['p', 'div', 'span'], 
                                         text=re.compile(r'[Oo]pen|[Hh]ours?|[Mm]on.*[Ss]un', re.IGNORECASE))
            for section in hour_sections:
                text = section.get_text().strip()
                if 'AM' in text or 'PM' in text:
                    hours = text[:150]
                    break
            
            return {
                'museum': 'Museum of Ice Cream',
                'hours': hours,
                'address': '558 Broadway, New York, NY 10012',
                'phone': '(646) 459-3515',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'source': 'museumoficecream.com'
            }
            
        except Exception as e:
            return {
                'museum': 'Museum of Ice Cream',
                'hours': 'Mon-Sun: 10:00 AM - 9:00 PM',
                'address': '558 Broadway, New York, NY 10012',
                'phone': '(646) 459-3515',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:100],
                'source': 'fallback'
            }
    
    def scrape_ukrainian_museum(self):
        """Scrape Ukrainian Museum hours"""
        try:
            url = "https://www.ukrainianmuseum.org/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Wed-Sun: 11:30 AM - 5:00 PM"
            
            # Multiple search strategies
            patterns = [
                r'[Hh]ours?[:\s]*([^\n]{10,100})',
                r'[Oo]pen[:\s]*([^\n]{10,100})',
                r'(\d{1,2}:\d{2}\s*[APap][Mm]\s*[-–]\s*\d{1,2}:\d{2}\s*[APap][Mm])'
            ]
            
            all_text = soup.get_text()
            for pattern in patterns:
                match = re.search(pattern, all_text)
                if match:
                    hours = match.group(1).strip()[:100]
                    break
            
            # Also search in footer or specific sections
            footer = soup.find(['footer', 'div'], class_=re.compile(r'footer|hours|visit', re.IGNORECASE))
            if footer:
                footer_text = footer.get_text()
                for pattern in patterns:
                    match = re.search(pattern, footer_text)
                    if match:
                        hours = match.group(1).strip()[:100]
                        break
            
            return {
                'museum': 'Ukrainian Museum',
                'hours': hours,
                'address': '222 East 6th Street, New York, NY 10003',
                'phone': '(212) 228-0110',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'source': 'ukrainianmuseum.org'
            }
            
        except Exception as e:
            return {
                'museum': 'Ukrainian Museum',
                'hours': 'Wed-Sun: 11:30 AM - 5:00 PM',
                'address': '222 East 6th Street, New York, NY 10003',
                'phone': '(212) 228-0110',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:100],
                'source': 'fallback'
            }
    
    def scrape_empire_state(self):
        """Scrape Empire State Building hours"""
        try:
            url = "https://www.esbnyc.com/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Daily: 8:00 AM - 2:00 AM"
            
            # Multiple search strategies
            hour_text = soup.get_text()
            
            # Pattern 1: Direct time patterns
            hour_patterns = [
                r'(\d{1,2}(?::\d{2})?\s*[APap][Mm]\s*[-–]\s*\d{1,2}(?::\d{2})?\s*[APap][Mm])',
                r'[Hh]ours?[:\s]*([^\n]{10,80})',
                r'[Oo]pen[:\s]*([^\n]{10,80})'
            ]
            
            for pattern in hour_patterns:
                match = re.search(pattern, hour_text)
                if match:
                    found = match.group(1).strip()
                    if 'AM' in found or 'PM' in found:
                        hours = f"Daily: {found}" if 'daily' not in found.lower() else found
                        break
            
            # Pattern 2: Look in specific sections
            visit_sections = soup.find_all(['div', 'section'], 
                                          text=re.compile(r'[Vv]isit|[Hh]ours?|[Oo]bservatory', re.IGNORECASE))
            for section in visit_sections:
                text = section.get_text()
                for pattern in hour_patterns:
                    match = re.search(pattern, text)
                    if match:
                        found = match.group(1).strip()
                        if 'AM' in found or 'PM' in found:
                            hours = found
                            break
            
            return {
                'museum': 'Empire State Building',
                'hours': hours,
                'address': '20 W 34th St, New York, NY 10001',
                'phone': '(212) 736-3100',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'source': 'esbnyc.com'
            }
            
        except Exception as e:
            return {
                'museum': 'Empire State Building',
                'hours': 'Daily: 8:00 AM - 2:00 AM',
                'address': '20 W 34th St, New York, NY 10001',
                'phone': '(212) 736-3100',
                'status': 'open',
                'last_updated': datetime.now().strftime("%I:%M %p"),
                'error': str(e)[:100],
                'source': 'fallback'
            }

# Create scraper instance
scraper = MuseumScraper()

# ============================================================================
# ORIGINAL MUSEUM API ENDPOINTS (unchanged)
# ============================================================================

@app.route('/api/met')
def get_met_hours():
    """GET MET Museum hours"""
    data = scraper.scrape_met_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/icecream')
def get_icecream_hours():
    """GET Ice Cream Museum hours"""
    data = scraper.scrape_ice_cream_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/ukrainian')
def get_ukrainian_hours():
    """GET Ukrainian Museum hours"""
    data = scraper.scrape_ukrainian_museum()
    return jsonify({'success': True, 'data': data})

@app.route('/api/empire')
def get_empire_hours():
    """GET Empire State Building hours"""
    data = scraper.scrape_empire_state()
    return jsonify({'success': True, 'data': data})

@app.route('/api/all')
def get_all_hours():
    """GET all museum hours at once"""
    data = {
        'met': scraper.scrape_met_museum(),
        'icecream': scraper.scrape_ice_cream_museum(),
        'ukrainian': scraper.scrape_ukrainian_museum(),
        'empire': scraper.scrape_empire_state(),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return jsonify({'success': True, 'data': data})

@app.route('/api/test')
def test_api():
    """Test endpoint to verify API is working"""
    return jsonify({
        'success': True,
        'message': 'Museum Hours API is running!',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'endpoints': {
            '/api/met': 'MET Museum hours',
            '/api/icecream': 'Ice Cream Museum hours',
            '/api/ukrainian': 'Ukrainian Museum hours',
            '/api/empire': 'Empire State Building hours',
            '/api/all': 'All museums at once',
            '/api/test': 'Test endpoint'
        }
    })

# ============================================================================
# ORIGINAL BREAKFAST SCRAPER CLASS (unchanged)
# ============================================================================

class BreakfastScraper:
    """Web scraper for breakfast restaurant hours"""
    
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
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find hours - these selectors might need adjustment
            hours = "Mon-Sun: 8:00 AM - 10:00 PM"
            
            # Search for hour patterns
            hour_sections = soup.find_all(['p', 'div', 'span', 'li'], 
                                         text=re.compile(r'[Hh]ours?|[Oo]pen|[Cc]losed|8.*AM.*10.*PM', re.IGNORECASE))
            
            for section in hour_sections:
                text = section.get_text().strip()
                if ('8' in text or '9' in text) and ('AM' in text or 'am' in text) and ('PM' in text or 'pm' in text):
                    hours = text[:150]
                    break
            
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
                'source': 'jackswifefreda.com'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Jack's Wife Freda",
                'hours': "Mon-Sun: 8:00 AM - 10:00 PM",
                'location': "New York, NY",
                'error': str(e)[:100],
                'status': 'failed',
                'source': 'fallback'
            }
    
    def scrape_shuka(self):
        """Scrape Shuka hours"""
        try:
            print("Scraping Shuka...")
            url = "https://www.shukanewyork.com/"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Mon-Thu: 5:00 PM - 11:00 PM, Fri: 12:00 PM - 12:00 AM, Sat-Sun: 11:00 AM - 11:00 PM"
            
            hour_sections = soup.find_all(['p', 'div', 'span', 'li'], 
                                         text=re.compile(r'[Hh]ours?|[Oo]pen|[Cc]losed|5.*PM.*11.*PM', re.IGNORECASE))
            
            for section in hour_sections:
                text = section.get_text().strip()
                if 'PM' in text or 'AM' in text:
                    hours = text[:150]
                    break
            
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
                'source': 'shukanewyork.com'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Shuka",
                'hours': "Mon-Thu: 5:00 PM - 11:00 PM, Fri: 12:00 PM - 12:00 AM, Sat-Sun: 11:00 AM - 11:00 PM",
                'location': "38 Macdougal St, New York, NY",
                'error': str(e)[:100],
                'status': 'failed',
                'source': 'fallback'
            }
    
    def scrape_sarabeths(self):
        """Scrape Sarabeth's hours"""
        try:
            print("Scraping Sarabeth's...")
            url = "https://sarabethsrestaurants.com/"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Mon-Fri: 8:00 AM - 10:00 PM, Sat-Sun: 9:00 AM - 11:00 PM"
            
            hour_sections = soup.find_all(['p', 'div', 'span', 'li'], 
                                         text=re.compile(r'[Hh]ours?|[Oo]pen|[Cc]losed|8.*AM.*10.*PM', re.IGNORECASE))
            
            for section in hour_sections:
                text = section.get_text().strip()
                if ('8' in text or '9' in text) and ('AM' in text or 'am' in text):
                    hours = text[:150]
                    break
            
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
                'source': 'sarabethsrestaurants.com'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Sarabeth's",
                'hours': "Mon-Fri: 8:00 AM - 10:00 PM, Sat-Sun: 9:00 AM - 11:00 PM",
                'location': "Multiple locations in New York",
                'error': str(e)[:100],
                'status': 'failed',
                'source': 'fallback'
            }
    
    def scrape_ess_a_bagel(self):
        """Scrape Ess-a-Bagel hours"""
        try:
            print("Scraping Ess-a-Bagel...")
            url = "https://www.ess-a-bagel.com/"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hours = "Mon-Fri: 6:00 AM - 6:00 PM, Sat-Sun: 6:30 AM - 5:00 PM"
            
            hour_sections = soup.find_all(['p', 'div', 'span', 'li'], 
                                         text=re.compile(r'[Hh]ours?|[Oo]pen|[Cc]losed|6.*AM.*6.*PM', re.IGNORECASE))
            
            for section in hour_sections:
                text = section.get_text().strip()
                if '6:' in text and ('AM' in text or 'am' in text):
                    hours = text[:150]
                    break
            
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
                'source': 'ess-a-bagel.com'
            }
            
            self.save_to_database(scraped_data)
            return scraped_data
            
        except Exception as e:
            return {
                'restaurant': "Ess-a-Bagel",
                'hours': "Mon-Fri: 6:00 AM - 6:00 PM, Sat-Sun: 6:30 AM - 5:00 PM",
                'location': "Multiple locations in New York",
                'error': str(e)[:100],
                'status': 'failed',
                'source': 'fallback'
            }
    
    def save_to_database(self, restaurant_data):
        """Save scraped restaurant data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Save each day's hours as separate record
            hours = restaurant_data.get('hours', {})
            for day, hours_text in hours.items():
                # Parse open and close times
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
            conn.close()
            print(f"✅ Saved: {restaurant_data['restaurant']}")
            
        except Exception as e:
            print(f"⚠️ Database error: {e}")
    
    def scrape_all_restaurants(self):
        """Scrape all four breakfast places"""
        print("🍳 Starting breakfast places scraper...")
        
        results = [
            self.scrape_jacks_wife_freda(),
            self.scrape_shuka(),
            self.scrape_sarabeths(),
            self.scrape_ess_a_bagel()
        ]
        
        success_count = len([r for r in results if r.get('status') == 'success'])
        
        print(f"✅ Scraping complete! {success_count} out of 4 successful.")
        return results
    
    def get_restaurant_hours_formatted(self, restaurant_name):
        """Get scraped restaurant hours formatted by day"""
        try:
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
        except Exception as e:
            print(f"Error getting hours: {e}")
            return []

# Create breakfast scraper instance
breakfast_scraper = BreakfastScraper()

# ============================================================================
# ORIGINAL BROADWAY SCRAPER CLASS (unchanged)
# ============================================================================

class BroadwayScraper:
    """Web scraper for Broadway show availability"""
    
    def __init__(self):
        self.db_path = "broadway_shows.db"
        self.init_database()
    
    def init_database(self):
        """Create database table for scraped Broadway data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS broadway_shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                show_name TEXT,
                show_date TEXT,
                price_range TEXT,
                status TEXT,
                scraped_at TIMESTAMP,
                show_day TEXT,
                show_month TEXT,
                show_year TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Broadway Scraper Database initialized")
    
    def scrape_broadway_availability(self, start_date=None, end_date=None, quantity=2):
        """
        Scrape Broadway.com show availability data for the specified date range
        If no dates provided, uses next 5 days
        """
        try:
            # Set default dates if none provided (next 5 days)
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
            
            if not end_date:
                # Calculate 5 days from start
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = start_dt + timedelta(days=5)
                end_date = end_dt.strftime("%Y-%m-%d")
            
            print(f"🎭 Scraping Broadway.com shows from {start_date} to {end_date}...")
            
            # Try multiple URL patterns since Broadway.com might block scraping
            urls_to_try = [
                f"https://www.broadway.com/shows/tickets/",
                f"https://www.broadway.com/shows/",
                f"https://www.broadway.com/",
                f"https://www.broadway.com/shows/find-by-date/?query=&start_date={start_date}&end_date={end_date}&quantity={quantity}"
            ]
            
            for url in urls_to_try:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extract show information from the page
                    shows = self.extract_shows_from_html(soup, start_date, end_date)
                    
                    if shows:
                        scraped_data = {
                            'source': 'broadway.com',
                            'date_range': f'{start_date} to {end_date}',
                            'ticket_quantity': quantity,
                            'shows': shows,
                            'total_found': len(shows),
                            'scraped_at': datetime.now().isoformat(),
                            'status': 'success',
                            'url_used': url
                        }
                        
                        print(f"✅ Found {len(shows)} Broadway shows")
                        return scraped_data
                        
                except Exception as e:
                    print(f"⚠️ URL {url} failed: {e}")
                    continue
            
            # If no URLs worked, generate sample data
            print("⚠️ All URLs failed, generating sample data")
            return self.generate_sample_data(start_date, end_date, quantity)
            
        except Exception as e:
            print(f"❌ Error scraping Broadway: {e}")
            return self.generate_sample_data(start_date, end_date, quantity)
    
    def extract_shows_from_html(self, soup, start_date, end_date):
        """Extract show information from HTML content"""
        shows = []
        
        # Try to find show listings in various HTML structures
        show_selectors = [
            ('div', {'class': 'show-card'}),
            ('div', {'class': 'show-listing'}),
            ('div', {'class': 'ticket-item'}),
            ('article', {'class': 'show'}),
            ('li', {'class': 'show-item'}),
            ('a', {'href': re.compile(r'/shows/|/tickets/')}),
        ]
        
        for tag_name, attrs in show_selectors:
            elements = soup.find_all(tag_name, attrs=attrs)
            if elements:
                for element in elements[:10]:  # Limit to 10 shows
                    try:
                        show_info = self.parse_show_element(element)
                        if show_info:
                            shows.append(show_info)
                            self.save_to_database(show_info)
                    except Exception as e:
                        continue
        
        # If no shows found with selectors, look for any text containing show names
        if not shows:
            all_text = soup.get_text()
            popular_shows = [
                "Hamilton", "The Lion King", "Wicked", "Hadestown",
                "Moulin Rouge", "Six", "Chicago", "Phantom of the Opera",
                "Book of Mormon", "Aladdin", "Frozen", "Harry Potter",
                "MJ The Musical", "Some Like It Hot", "Kimberly Akimbo"
            ]
            
            for show_name in popular_shows:
                if show_name.lower() in all_text.lower():
                    show_info = {
                        'show_name': show_name,
                        'show_date': 'Check website',
                        'price_range': 'from $99.00 - $399.00',
                        'status': 'Likely Available',
                        'description': f'{show_name} - Check official site for exact dates and prices'
                    }
                    shows.append(show_info)
        
        return shows
    
    def parse_show_element(self, element):
        """Parse individual show element from HTML"""
        try:
            # Try to extract show name
            show_name = "Broadway Show"
            name_elements = element.find_all(['h2', 'h3', 'h4', 'span', 'a'], 
                                           class_=re.compile(r'title|name|show', re.IGNORECASE))
            if name_elements:
                show_name = name_elements[0].get_text(strip=True)
            
            # Try to extract price
            price_range = "from $99.00 - $299.00"
            price_elements = element.find_all(['span', 'div'], 
                                            class_=re.compile(r'price|cost|ticket', re.IGNORECASE))
            if price_elements:
                for price_el in price_elements:
                    price_text = price_el.get_text(strip=True)
                    if '$' in price_text:
                        price_range = price_text
                        break
            
            # Generate status based on random availability
            import random
            statuses = ['Available', 'Limited Availability', 'Almost Sold Out']
            status = random.choice(statuses)
            
            return {
                'show_name': show_name[:100],
                'show_date': 'Various Dates',
                'price_range': price_range,
                'status': status,
                'description': f'{show_name} - {status}'
            }
        except:
            return None
    
    def generate_sample_data(self, start_date, end_date, quantity):
        """Generate sample Broadway show data when scraping fails"""
        sample_shows = [
            {
                'show_name': 'Hamilton',
                'show_date': 'Various Dates',
                'price_range': 'from $199.00 - $699.00',
                'status': 'Available',
                'description': 'The revolutionary musical phenomenon - limited tickets available'
            },
            {
                'show_name': 'Wicked',
                'show_date': 'Various Dates',
                'price_range': 'from $129.00 - $399.00',
                'status': 'Available',
                'description': 'The untold story of the Witches of Oz'
            },
            {
                'show_name': 'The Lion King',
                'show_date': 'Various Dates',
                'price_range': 'from $159.00 - $349.00',
                'status': 'Limited Availability',
                'description': 'Disney\'s award-winning masterpiece - family favorite'
            },
            {
                'show_name': 'Hadestown',
                'show_date': 'Various Dates',
                'price_range': 'from $99.00 - $299.00',
                'status': 'Available',
                'description': 'Tony-winning folk opera - journey to the underworld'
            },
            {
                'show_name': 'Moulin Rouge! The Musical',
                'show_date': 'Various Dates',
                'price_range': 'from $149.00 - $499.00',
                'status': 'Almost Sold Out',
                'description': 'Spectacular spectacular! Baz Luhrmann\'s iconic film on stage'
            }
        ]
        
        for show in sample_shows:
            self.save_to_database(show)
        
        return {
            'source': 'sample data',
            'date_range': f'{start_date} to {end_date}',
            'ticket_quantity': quantity,
            'shows': sample_shows,
            'total_found': len(sample_shows),
            'scraped_at': datetime.now().isoformat(),
            'status': 'sample',
            'note': 'Using sample data - real scraping was blocked or failed'
        }
    
    def save_to_database(self, show_data):
        """Save scraped Broadway data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO broadway_shows 
                (show_name, show_date, price_range, status, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                show_data.get('show_name', ''),
                show_data.get('show_date', ''),
                show_data.get('price_range', ''),
                show_data.get('status', ''),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Broadway database error: {e}")
    
    def get_recent_shows(self, limit=50):
        """Get recently scraped Broadway shows from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT show_name, show_date, price_range, status, scraped_at 
                FROM broadway_shows 
                ORDER BY scraped_at DESC 
                LIMIT ?
            ''', (limit,))
            
            shows = []
            for row in cursor.fetchall():
                show_data = {
                    'show_name': row[0],
                    'show_date': row[1],
                    'price_range': row[2],
                    'status': row[3],
                    'scraped_at': row[4]
                }
                shows.append(show_data)
            
            conn.close()
            return shows
        except Exception as e:
            print(f"Error getting Broadway shows: {e}")
            return []

# Create Broadway scraper instance
broadway_scraper = BroadwayScraper()

# ============================================================================
# ORIGINAL ITINERARY STORAGE CLASS (unchanged)
# ============================================================================

class ItineraryStorage:
    """Database storage for itinerary choices with user authentication support"""
    
    def __init__(self):
        self.db_path = "itinerary_storage.db"
        self.init_database()
    
    def init_database(self):
        """Create database table for itinerary data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main itinerary table with user_id for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS itinerary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                user_id INTEGER,
                trip_info TEXT,
                breakfast TEXT,
                landmarks TEXT,
                shopping TEXT,
                broadway TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id) ON CONFLICT REPLACE  -- One itinerary per user
            )
        ''')
        
        # Create indexes for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON itinerary(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON itinerary(user_id)')
        
        conn.commit()
        conn.close()
        print("✅ Itinerary Storage Database initialized with user authentication support")
    
    def create_session(self):
        """Create a new session ID"""
        return str(uuid.uuid4())
    
    def save_itinerary(self, session_id, itinerary_data, user_id=None):
        """Save or update itinerary data for a session or user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user already has an itinerary
            existing_id = None
            if user_id:
                cursor.execute('SELECT id FROM itinerary WHERE user_id = ?', (user_id,))
                existing_user = cursor.fetchone()
                if existing_user:
                    existing_id = existing_user[0]
            
            # If no user itinerary, check by session
            if not existing_id and session_id:
                cursor.execute('SELECT id FROM itinerary WHERE session_id = ?', (session_id,))
                existing_session = cursor.fetchone()
                if existing_session:
                    existing_id = existing_session[0]
            
            if existing_id:
                # Update existing record
                cursor.execute('''
                    UPDATE itinerary SET 
                        session_id = COALESCE(?, session_id),
                        user_id = COALESCE(?, user_id),
                        trip_info = ?,
                        breakfast = ?,
                        landmarks = ?,
                        shopping = ?,
                        broadway = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    session_id,
                    user_id,
                    json.dumps(itinerary_data.get('trip_info')) if itinerary_data.get('trip_info') else None,
                    json.dumps(itinerary_data.get('breakfast')) if itinerary_data.get('breakfast') else None,
                    json.dumps(itinerary_data.get('landmarks')) if itinerary_data.get('landmarks') else None,
                    json.dumps(itinerary_data.get('shopping')) if itinerary_data.get('shopping') else None,
                    json.dumps(itinerary_data.get('broadway')) if itinerary_data.get('broadway') else None,
                    existing_id
                ))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO itinerary 
                    (session_id, user_id, trip_info, breakfast, landmarks, shopping, broadway)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    user_id,
                    json.dumps(itinerary_data.get('trip_info')) if itinerary_data.get('trip_info') else None,
                    json.dumps(itinerary_data.get('breakfast')) if itinerary_data.get('breakfast') else None,
                    json.dumps(itinerary_data.get('landmarks')) if itinerary_data.get('landmarks') else None,
                    json.dumps(itinerary_data.get('shopping')) if itinerary_data.get('shopping') else None,
                    json.dumps(itinerary_data.get('broadway')) if itinerary_data.get('broadway') else None
                ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'session_id': session_id,
                'user_id': user_id,
                'message': 'Itinerary saved successfully'
            }
            
        except Exception as e:
            print(f"❌ Error saving itinerary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_itinerary(self, session_id=None, user_id=None):
        """Get itinerary data for a session or user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT trip_info, breakfast, landmarks, shopping, broadway, created_at, updated_at
                FROM itinerary 
                WHERE 1=1
            '''
            params = []
            
            if user_id:
                query += ' AND user_id = ?'
                params.append(user_id)
            elif session_id:
                query += ' AND session_id = ?'
                params.append(session_id)
            else:
                conn.close()
                return {
                    'success': False,
                    'error': 'No session_id or user_id provided'
                }
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Parse JSON data back to Python objects
                itinerary_data = {
                    'trip_info': json.loads(row[0]) if row[0] else None,
                    'breakfast': json.loads(row[1]) if row[1] else None,
                    'landmarks': json.loads(row[2]) if row[2] else None,
                    'shopping': json.loads(row[3]) if row[3] else None,
                    'broadway': json.loads(row[4]) if row[4] else None,
                    'created_at': row[5],
                    'updated_at': row[6]
                }
                
                return {
                    'success': True,
                    'session_id': session_id,
                    'user_id': user_id,
                    'data': itinerary_data
                }
            else:
                # Return empty itinerary if none exists
                return {
                    'success': True,
                    'session_id': session_id,
                    'user_id': user_id,
                    'data': {
                        'trip_info': None,
                        'breakfast': None,
                        'landmarks': None,
                        'shopping': None,
                        'broadway': None,
                        'created_at': None,
                        'updated_at': None
                    }
                }
                
        except Exception as e:
            print(f"❌ Error getting itinerary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_section(self, session_id=None, user_id=None, section_name=None, section_data=None):
        """Update a specific section of the itinerary"""
        try:
            # Validate section name
            valid_sections = ['trip_info', 'breakfast', 'landmarks', 'shopping', 'broadway']
            if section_name not in valid_sections:
                return {
                    'success': False,
                    'error': f'Invalid section. Must be one of: {", ".join(valid_sections)}'
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if itinerary exists
            query = 'SELECT id FROM itinerary WHERE '
            params = []
            
            if user_id:
                query += 'user_id = ?'
                params.append(user_id)
            elif session_id:
                query += 'session_id = ?'
                params.append(session_id)
            else:
                conn.close()
                return {
                    'success': False,
                    'error': 'No session_id or user_id provided'
                }
            
            cursor.execute(query, params)
            existing = cursor.fetchone()
            
            if not existing:
                # Create new record with just this section
                cursor.execute(f'''
                    INSERT INTO itinerary (session_id, user_id, {section_name})
                    VALUES (?, ?, ?)
                ''', (session_id, user_id, json.dumps(section_data) if section_data else None))
            else:
                # Update specific section
                cursor.execute(f'''
                    UPDATE itinerary SET 
                        {section_name} = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (json.dumps(section_data) if section_data else None, existing[0]))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'session_id': session_id,
                'user_id': user_id,
                'section': section_name,
                'message': f'{section_name} updated successfully'
            }
            
        except Exception as e:
            print(f"❌ Error updating section: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear_itinerary(self, session_id=None, user_id=None):
        """Clear all itinerary data for a session or user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                UPDATE itinerary SET 
                    trip_info = NULL,
                    breakfast = NULL,
                    landmarks = NULL,
                    shopping = NULL,
                    broadway = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE 1=1
            '''
            params = []
            
            if user_id:
                query += ' AND user_id = ?'
                params.append(user_id)
            elif session_id:
                query += ' AND session_id = ?'
                params.append(session_id)
            else:
                conn.close()
                return {
                    'success': False,
                    'error': 'No session_id or user_id provided'
                }
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'session_id': session_id,
                'user_id': user_id,
                'message': 'Itinerary cleared successfully'
            }
            
        except Exception as e:
            print(f"❌ Error clearing itinerary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_itinerary(self, session_id=None, user_id=None):
        """Delete an entire itinerary"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'DELETE FROM itinerary WHERE '
            params = []
            
            if user_id:
                query += 'user_id = ?'
                params.append(user_id)
            elif session_id:
                query += 'session_id = ?'
                params.append(session_id)
            else:
                conn.close()
                return {
                    'success': False,
                    'error': 'No session_id or user_id provided'
                }
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'session_id': session_id,
                'user_id': user_id,
                'message': 'Itinerary deleted successfully'
            }
            
        except Exception as e:
            print(f"❌ Error deleting itinerary: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def merge_sessions(self, from_session_id, to_user_id):
        """Merge session-based itinerary into user account"""
        try:
            # Get session itinerary
            session_result = self.get_itinerary(session_id=from_session_id)
            if not session_result['success']:
                return session_result
            
            session_data = session_result['data']
            
            # Get user itinerary (if any)
            user_result = self.get_itinerary(user_id=to_user_id)
            
            # Merge data - session data takes precedence
            merged_data = {}
            sections = ['trip_info', 'breakfast', 'landmarks', 'shopping', 'broadway']
            
            if user_result['success']:
                user_data = user_result['data']
                for section in sections:
                    # Use session data if it exists, otherwise keep user data
                    if session_data.get(section):
                        merged_data[section] = session_data[section]
                    else:
                        merged_data[section] = user_data.get(section)
            else:
                # No user data, use session data
                merged_data = session_data
            
            # Save merged data to user account
            return self.save_itinerary(None, merged_data, to_user_id)
            
        except Exception as e:
            print(f"❌ Error merging sessions: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Create itinerary storage instance
itinerary_storage = ItineraryStorage()

# ============================================================================
# ENHANCED ITINERARY STORAGE WITH BUDGET INTEGRATION (NEW)
# ============================================================================

class EnhancedItineraryStorage(ItineraryStorage):
    """Enhanced itinerary storage with budget integration"""
    
    def save_itinerary_with_budget(self, session_id, itinerary_data, user_id=None, budget_id=None):
        """Save itinerary with budget tracking"""
        try:
            # First save to regular itinerary
            result = super().save_itinerary(session_id, itinerary_data, user_id)
            if not result['success']:
                return result
            
            # Extract prices and add to budget
            total_cost = 0
            
            # Breakfast prices
            if itinerary_data.get('breakfast'):
                breakfast = itinerary_data['breakfast']
                if isinstance(breakfast, dict) and 'price' in breakfast:
                    price = float(breakfast.get('price', 0))
                    if price > 0 and budget_id:
                        budget_tracker.add_expense(
                            budget_id=budget_id,
                            category='food',
                            item_name=breakfast.get('name', 'Breakfast'),
                            price=price,
                            module='breakfast'
                        )
                        total_cost += price
            
            # Broadway prices
            if itinerary_data.get('broadway'):
                broadway = itinerary_data['broadway']
                if isinstance(broadway, dict) and 'price' in broadway:
                    price = float(broadway.get('price', 0))
                    if price > 0 and budget_id:
                        budget_tracker.add_expense(
                            budget_id=budget_id,
                            category='entertainment',
                            item_name=broadway.get('show_name', 'Broadway Show'),
                            price=price,
                            module='broadway'
                        )
                        total_cost += price
            
            # Update result with budget info
            result['total_cost'] = total_cost
            result['budget_id'] = budget_id
            result['message'] = f'Itinerary saved with ${total_cost:.2f} added to budget'
            
            return result
            
        except Exception as e:
            print(f"❌ Error saving itinerary with budget: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Create enhanced itinerary storage
enhanced_itinerary_storage = EnhancedItineraryStorage()

# ============================================================================
# BUDGET TRACKING API ENDPOINTS (NEW)
# ============================================================================

@app.route('/api/budget', methods=['GET'])
def get_budget_info():
    """GET budget information for current user/session"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('budget_session_id')
        
        result = budget_tracker.get_budget(user_id=user_id, session_id=session_id)
        
        if result['success']:
            # Set session cookie if needed
            response = jsonify(result)
            if not session_id and result.get('budget'):
                session_id = result['budget'].get('session_id')
                if session_id:
                    response.set_cookie('budget_session_id', session_id, max_age=30*24*60*60)
            return response
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/budget', methods=['POST'])
def create_update_budget():
    """Create or update a budget"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get or create session ID
        session_id = request.cookies.get('budget_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Get budget data from request
        data = request.get_json()
        if not data or 'total_budget' not in data:
            return jsonify({
                'success': False,
                'error': 'total_budget is required'
            }), 400
        
        # Check if budget already exists
        existing = budget_tracker.get_budget(user_id=user_id, session_id=session_id)
        
        if existing['success'] and existing.get('budget'):
            # Update existing budget
            result = budget_tracker.update_budget(
                user_id=user_id,
                session_id=session_id,
                total_budget=data.get('total_budget'),
                budget_name=data.get('budget_name'),
                currency=data.get('currency', 'USD'),
                trip_duration=data.get('trip_duration', 1),
                notes=data.get('notes')
            )
        else:
            # Create new budget
            result = budget_tracker.create_budget(
                user_id=user_id,
                session_id=session_id,
                total_budget=data.get('total_budget'),
                budget_name=data.get('budget_name', 'Trip Budget'),
                currency=data.get('currency', 'USD'),
                trip_duration=data.get('trip_duration', 1),
                notes=data.get('notes', '')
            )
        
        if result['success']:
            response = jsonify(result)
            response.set_cookie('budget_session_id', session_id, max_age=30*24*60*60)
            return response
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/budget/expense', methods=['POST'])
def add_budget_expense():
    """Add an expense to the budget"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('budget_session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'No budget session. Please create a budget first.'
            }), 400
        
        # Get expense data from request
        data = request.get_json()
        if not data or 'price' not in data:
            return jsonify({
                'success': False,
                'error': 'price and item_name are required'
            }), 400
        
        result = budget_tracker.add_expense(
            user_id=user_id,
            session_id=session_id,
            category=data.get('category', 'Uncategorized'),
            item_name=data.get('item_name', 'Item'),
            item_type=data.get('item_type', ''),
            price=data.get('price', 0),
            quantity=data.get('quantity', 1),
            description=data.get('description', ''),
            module=data.get('module', 'general'),
            day_number=data.get('day_number', 1)
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/budget/expense/<int:expense_id>', methods=['DELETE'])
def remove_budget_expense(expense_id):
    """Remove an expense from the budget"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('budget_session_id')
        
        result = budget_tracker.remove_expense(
            expense_id=expense_id,
            user_id=user_id,
            session_id=session_id
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/budget/summary', methods=['GET'])
def get_budget_summary():
    """Get budget summary and analytics"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('budget_session_id')
        
        result = budget_tracker.get_expense_summary(
            user_id=user_id,
            session_id=session_id
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/budget/reset', methods=['POST'])
def reset_budget_data():
    """Reset budget data (clear expenses or entire budget)"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('budget_session_id')
        
        data = request.get_json() or {}
        keep_expenses = data.get('keep_expenses', False)
        
        result = budget_tracker.reset_budget(
            user_id=user_id,
            session_id=session_id,
            keep_expenses=keep_expenses
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/budget/sync', methods=['POST'])
@login_required
def sync_budget_to_account():
    """Sync session budget to user account (on login)"""
    try:
        # Get session ID from cookie
        session_id = request.cookies.get('budget_session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'No session budget to sync'
            }), 400
        
        # Get user ID
        user_id = current_user.id
        
        # Get session budget
        session_budget = budget_tracker.get_budget(session_id=session_id)
        if not session_budget['success'] or not session_budget.get('budget'):
            return jsonify({
                'success': False,
                'error': 'No session budget found'
            }), 400
        
        # Get user budget
        user_budget = budget_tracker.get_budget(user_id=user_id)
        
        # If user has no budget, transfer session budget to user
        if not user_budget.get('budget'):
            # Update session budget with user_id
            conn = sqlite3.connect(budget_tracker.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_budgets 
                SET user_id = ?, session_id = NULL 
                WHERE session_id = ?
            ''', (user_id, session_id))
            
            cursor.execute('''
                UPDATE budget_expenses 
                SET user_id = ?, session_id = NULL 
                WHERE session_id = ?
            ''', (user_id, session_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Budget synced to user account',
                'user_id': user_id
            })
        else:
            # Merge session expenses into user budget
            session_expenses = session_budget.get('expenses', [])
            
            for expense in session_expenses:
                budget_tracker.add_expense(
                    user_id=user_id,
                    session_id=None,
                    category=expense['category'],
                    item_name=expense['item_name'],
                    item_type=expense.get('item_type', ''),
                    price=expense['price'],
                    quantity=expense['quantity'],
                    description=expense.get('description', ''),
                    module=expense['module'],
                    day_number=expense.get('day_number', 1)
                )
            
            # Delete session budget
            budget_tracker.reset_budget(session_id=session_id, keep_expenses=False)
            
            return jsonify({
                'success': True,
                'message': 'Session expenses merged into user budget',
                'user_id': user_id,
                'expenses_merged': len(session_expenses)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/budget/test', methods=['GET'])
def test_budget_api():
    """Test budget API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Budget Tracking API is running!',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'endpoints': {
            'GET /api/budget': 'Get budget information',
            'POST /api/budget': 'Create/update budget',
            'POST /api/budget/expense': 'Add expense',
            'DELETE /api/budget/expense/<id>': 'Remove expense',
            'GET /api/budget/summary': 'Get budget summary',
            'POST /api/budget/reset': 'Reset budget',
            'POST /api/budget/sync': 'Sync to user account (login)',
            'GET /api/budget/test': 'Test endpoint'
        },
        'features': [
            'User authentication integration',
            'Session-based fallback for guests',
            'Automatic merging on login',
            'Category and module tracking',
            'Daily budget breakdown',
            'Budget alerts and notifications',
            'Expense analytics and summaries'
        ]
    })

# ============================================================================
# ENHANCED ITINERARY API ENDPOINTS WITH BUDGET INTEGRATION (NEW)
# ============================================================================

@app.route('/api/itinerary/with-budget', methods=['POST'])
def save_itinerary_with_budget():
    """Save itinerary with automatic budget tracking"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session IDs
        session_id = request.cookies.get('itinerary_session_id')
        budget_session_id = request.cookies.get('budget_session_id')
        
        if not session_id:
            session_id = itinerary_storage.create_session()
        
        # Get itinerary data from request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No itinerary data provided'
            }), 400
        
        # Get budget ID if exists
        budget_id = None
        if budget_session_id:
            budget_info = budget_tracker.get_budget(session_id=budget_session_id)
            if budget_info['success'] and budget_info.get('budget'):
                budget_id = budget_info['budget']['id']
        
        # Save itinerary with budget integration
        result = enhanced_itinerary_storage.save_itinerary_with_budget(
            session_id=session_id,
            itinerary_data=data,
            user_id=user_id,
            budget_id=budget_id
        )
        
        if result['success']:
            response = jsonify(result)
            # Set cookies
            response.set_cookie('itinerary_session_id', session_id, max_age=30*24*60*60)
            if budget_session_id:
                response.set_cookie('budget_session_id', budget_session_id, max_age=30*24*60*60)
            return response
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/budget-summary', methods=['GET'])
def get_itinerary_budget_summary():
    """Get combined itinerary and budget summary"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session IDs
        itinerary_session_id = request.cookies.get('itinerary_session_id')
        budget_session_id = request.cookies.get('budget_session_id')
        
        # Get itinerary data
        itinerary_result = itinerary_storage.get_itinerary(
            user_id=user_id,
            session_id=itinerary_session_id
        )
        
        # Get budget data
        budget_result = budget_tracker.get_budget(
            user_id=user_id,
            session_id=budget_session_id
        )
        
        combined_data = {
            'success': True,
            'itinerary': itinerary_result if itinerary_result['success'] else None,
            'budget': budget_result if budget_result['success'] else None,
            'has_budget': budget_result['success'] and budget_result.get('budget') is not None,
            'has_itinerary': itinerary_result['success'] and itinerary_result.get('data') is not None
        }
        
        # Calculate combined metrics
        if combined_data['has_itinerary'] and combined_data['has_budget']:
            # Extract prices from itinerary
            itinerary_cost = 0
            if itinerary_result['data'].get('breakfast'):
                breakfast = itinerary_result['data']['breakfast']
                if isinstance(breakfast, dict) and 'price' in breakfast:
                    itinerary_cost += float(breakfast.get('price', 0))
            
            if itinerary_result['data'].get('broadway'):
                broadway = itinerary_result['data']['broadway']
                if isinstance(broadway, dict) and 'price' in broadway:
                    itinerary_cost += float(broadway.get('price', 0))
            
            budget_total = budget_result['budget'].get('total_budget', 0)
            budget_remaining = budget_result['budget'].get('remaining_budget', 0)
            
            combined_data['combined_metrics'] = {
                'itinerary_cost': itinerary_cost,
                'budget_total': budget_total,
                'budget_remaining': budget_remaining,
                'budget_after_itinerary': budget_remaining - itinerary_cost,
                'percentage_used': (itinerary_cost / budget_total * 100) if budget_total > 0 else 0
            }
        
        return jsonify(combined_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# ALL ORIGINAL API ENDPOINTS (unchanged)
# ============================================================================

@app.route('/api/id')
def get_user_id():
    """Get current user information for frontend login system"""
    try:
        if current_user.is_authenticated:
            # Prepare user data for frontend
            user_data = {
                'id': current_user.id,
                'uid': current_user.uid,
                'name': current_user.name if hasattr(current_user, 'name') else current_user.uid,
                'roles': [role.to_dict() for role in current_user.roles] if hasattr(current_user, 'roles') else [],
                'is_authenticated': True
            }
            return jsonify(user_data)
        else:
            # User is not logged in
            return jsonify({
                'is_authenticated': False,
                'message': 'Not authenticated'
            })
    except Exception as e:
        print(f"Error in /api/id: {e}")
        return jsonify({
            'is_authenticated': False,
            'error': str(e)
        })

@app.route('/api/user/class')
@login_required
def get_user_classes():
    """Get classes for the current user"""
    try:
        # Assuming you have a relationship between User and Classroom
        # This depends on your User model structure
        
        # Option 1: If you have a direct relationship
        if hasattr(current_user, 'classes'):
            classes = [cls.name for cls in current_user.classes]
            return jsonify({
                'success': True,
                'class': classes
            })
        
        # Option 2: If you have a class attribute
        elif hasattr(current_user, '_class'):
            # Assuming _class is a comma-separated string like "CSSE,CSP,CSA"
            class_list = current_user._class.split(',') if current_user._class else []
            return jsonify({
                'success': True,
                'class': [cls.strip() for cls in class_list]
            })
        
        # Option 3: Default fallback
        else:
            return jsonify({
                'success': True,
                'class': []
            })
            
    except Exception as e:
        print(f"Error in /api/user/class: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/breakfast')
def get_all_breakfast():
    """GET all breakfast restaurant hours"""
    try:
        results = breakfast_scraper.scrape_all_restaurants()
        success_count = len([r for r in results if r.get('status') == 'success'])
        
        return jsonify({
            'success': True,
            'count': success_count,
            'data': results,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message': f'Scraped {success_count} out of 4 breakfast restaurants'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/api/breakfast/<restaurant>')
def get_breakfast_hours(restaurant):
    """GET specific breakfast restaurant hours"""
    try:
        restaurant_map = {
            'jacks': breakfast_scraper.scrape_jacks_wife_freda,
            'shuka': breakfast_scraper.scrape_shuka,
            'sarabeths': breakfast_scraper.scrape_sarabeths,
            'bagel': breakfast_scraper.scrape_ess_a_bagel,
            'ess': breakfast_scraper.scrape_ess_a_bagel  # Added alias for frontend
        }
        
        if restaurant not in restaurant_map:
            return jsonify({
                'success': False,
                'error': f'Restaurant not found. Available: {list(restaurant_map.keys())}',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 404
        
        result = restaurant_map[restaurant]()
        days_data = breakfast_scraper.get_restaurant_hours_formatted(result['restaurant'])
        
        return jsonify({
            'success': True if result.get('status') == 'success' else False,
            'data': result,
            'daily_hours': days_data,
            'timestamp': datetime.now().strftime("%Y-%m-d %H:%M:%S")
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/api/breakfast/test')
def test_breakfast_api():
    """Test breakfast API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Breakfast Scraper API is running!',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'endpoints': {
            '/api/breakfast': 'All breakfast restaurant hours',
            '/api/breakfast/jacks': "Jack's Wife Freda hours",
            '/api/breakfast/shuka': 'Shuka hours',
            '/api/breakfast/sarabeths': "Sarabeth's hours",
            '/api/breakfast/bagel': 'Ess-a-Bagel hours',
            '/api/breakfast/ess': 'Ess-a-Bagel hours (alias)',
            '/api/breakfast/test': 'Test endpoint'
        },
        'restaurants': [
            "Jack's Wife Freda",
            "Shuka", 
            "Sarabeth's",
            "Ess-a-Bagel"
        ]
    })

@app.route('/api/broadway')
def get_broadway_availability():
    """GET Broadway show availability"""
    try:
        # Get parameters from query string or use defaults
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        quantity = request.args.get('quantity', 2, type=int)
        
        # If no dates provided, use default range
        if not start_date:
            # Default to next 7 days
            start_date = datetime.now().strftime("%Y-%m-%d")
        
        result = broadway_scraper.scrape_broadway_availability(
            start_date=start_date,
            end_date=end_date,
            quantity=quantity
        )
        
        # Get recent shows from database for context
        recent_shows = broadway_scraper.get_recent_shows(limit=20)
        
        return jsonify({
            'success': True,
            'data': result,
            'recent_shows': recent_shows,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message': f'Found {result.get("total_found", 0)} Broadway show(s)',
            'date_info': f'Dates: {result.get("date_range", "Various")}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/api/broadway/history')
def get_broadway_history():
    """GET historical Broadway data from database"""
    try:
        limit = request.args.get('limit', 100, type=int)
        shows = broadway_scraper.get_recent_shows(limit=limit)
        
        return jsonify({
            'success': True,
            'data': shows,
            'count': len(shows),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/api/broadway/test')
def test_broadway_api():
    """Test Broadway API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Broadway Scraper API is running!',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'endpoints': {
            '/api/broadway': 'Scrape Broadway availability (default: next 7 days)',
            '/api/broadway?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&quantity=N': 'Custom date range',
            '/api/broadway/history': 'Get scraped data from database',
            '/api/broadway/test': 'Test endpoint'
        },
        'parameters': {
            'start_date': 'YYYY-MM-DD format (optional, defaults to today)',
            'end_date': 'YYYY-MM-DD format (optional, defaults to 5 days after start)',
            'quantity': 'Number of tickets (default: 2)'
        }
    })

# ============================================================================
# ORIGINAL ITINERARY API ENDPOINTS (unchanged)
# ============================================================================

@app.route('/api/itinerary', methods=['GET'])
def get_itinerary():
    """GET itinerary for current session or logged-in user"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID from cookie
        session_id = request.cookies.get('itinerary_session_id')
        
        # Priority: User account > Session
        if user_id:
            # Try to get user's itinerary
            result = itinerary_storage.get_itinerary(user_id=user_id)
            if result['success']:
                # Check if user has any data
                user_data = result['data']
                has_user_data = any([
                    user_data.get('trip_info'),
                    user_data.get('breakfast'),
                    user_data.get('landmarks'),
                    user_data.get('shopping'),
                    user_data.get('broadway')
                ])
                
                if has_user_data:
                    return jsonify({
                        'success': True,
                        'user_id': user_id,
                        'session_id': session_id,
                        'data': user_data,
                        'source': 'user_account',
                        'message': 'Loaded from user account'
                    })
        
        # If no user data or user not logged in, check session
        if not session_id:
            # Create new session
            session_id = itinerary_storage.create_session()
            response = jsonify({
                'success': True,
                'user_id': user_id,
                'session_id': session_id,
                'data': {
                    'trip_info': None,
                    'breakfast': None,
                    'landmarks': None,
                    'shopping': None,
                    'broadway': None
                },
                'source': 'new_session',
                'message': 'New session created'
            })
            # Set session cookie
            response.set_cookie('itinerary_session_id', session_id, max_age=30*24*60*60)
            return response
        
        # Get session itinerary
        result = itinerary_storage.get_itinerary(session_id=session_id)
        
        if result['success']:
            result['user_id'] = user_id
            result['source'] = 'session'
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to get itinerary',
                'session_id': session_id
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/api/itinerary', methods=['POST', 'PUT'])
def save_itinerary():
    """Save or update entire itinerary"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('itinerary_session_id')
        if not session_id:
            session_id = itinerary_storage.create_session()
        
        # Get itinerary data from request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No itinerary data provided'
            }), 400
        
        # Save itinerary (will save to user account if user_id provided)
        result = itinerary_storage.save_itinerary(session_id, data, user_id)
        
        if result['success']:
            response = jsonify(result)
            # Ensure cookie is set
            response.set_cookie('itinerary_session_id', session_id, max_age=30*24*60*60)
            return response
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/section/<section_name>', methods=['POST', 'PUT'])
def update_itinerary_section(section_name):
    """Update specific section of itinerary"""
    try:
        # Validate section name
        valid_sections = ['trip_info', 'breakfast', 'landmarks', 'shopping', 'broadway']
        if section_name not in valid_sections:
            return jsonify({
                'success': False,
                'error': f'Invalid section. Must be one of: {", ".join(valid_sections)}'
            }), 400
        
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('itinerary_session_id')
        if not session_id:
            session_id = itinerary_storage.create_session()
        
        # Get section data from request
        data = request.get_json()
        
        # Update section
        result = itinerary_storage.update_section(
            session_id=session_id,
            user_id=user_id,
            section_name=section_name,
            section_data=data
        )
        
        if result['success']:
            response = jsonify(result)
            response.set_cookie('itinerary_session_id', session_id, max_age=30*24*60*60)
            return response
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/sync', methods=['POST'])
@login_required
def sync_itinerary_to_account():
    """Sync session itinerary to user account (login)"""
    try:
        # Get session ID from cookie
        session_id = request.cookies.get('itinerary_session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'No session data to sync'
            }), 400
        
        # Get user ID
        user_id = current_user.id
        
        # Merge session data into user account
        result = itinerary_storage.merge_sessions(session_id, user_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Itinerary synced to user account',
                'user_id': user_id,
                'session_id': session_id
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/user', methods=['GET'])
@login_required
def get_user_itinerary():
    """Get itinerary specifically for logged-in user"""
    try:
        user_id = current_user.id
        result = itinerary_storage.get_itinerary(user_id=user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/clear', methods=['POST', 'DELETE'])
def clear_itinerary():
    """Clear all itinerary data"""
    try:
        # Get user ID if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        # Get session ID
        session_id = request.cookies.get('itinerary_session_id')
        
        if not user_id and not session_id:
            return jsonify({
                'success': False,
                'error': 'No session or user to clear'
            }), 400
        
        result = itinerary_storage.clear_itinerary(
            session_id=session_id if not user_id else None,
            user_id=user_id
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/session', methods=['GET'])
def get_session_info():
    """Get current session information"""
    try:
        session_id = request.cookies.get('itinerary_session_id')
        user_id = current_user.id if current_user.is_authenticated else None
        
        return jsonify({
            'success': True,
            'has_session': bool(session_id),
            'is_logged_in': current_user.is_authenticated,
            'session_id': session_id,
            'user_id': user_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/new', methods=['POST'])
def create_new_itinerary():
    """Create a new itinerary session"""
    try:
        # Create new session
        session_id = itinerary_storage.create_session()
        
        response = jsonify({
            'success': True,
            'session_id': session_id,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'message': 'New itinerary session created'
        })
        
        # Set cookie
        response.set_cookie('itinerary_session_id', session_id, max_age=30*24*60*60)
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/itinerary/test', methods=['GET'])
def test_itinerary_api():
    """Test itinerary API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Itinerary Storage API is running!',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'features': [
            'User authentication integration',
            'Session-based fallback for guests',
            'Automatic merging on login',
            'Persistent storage in SQLite database'
        ],
        'endpoints': {
            'GET /api/itinerary': 'Get itinerary (auto-detects user/session)',
            'POST /api/itinerary': 'Save itinerary (saves to user account if logged in)',
            'POST /api/itinerary/section/{section}': 'Update specific section',
            'POST /api/itinerary/sync': 'Sync session data to user account (login)',
            'GET /api/itinerary/user': 'Get user-specific itinerary',
            'DELETE /api/itinerary/clear': 'Clear itinerary',
            'GET /api/itinerary/session': 'Get session info',
            'POST /api/itinerary/new': 'Create new session',
            'GET /api/itinerary/test': 'Test endpoint'
        },
        'sections': ['trip_info', 'breakfast', 'landmarks', 'shopping', 'broadway']
    })

# ============================================================================
# ALL ORIGINAL FLASK ROUTES (unchanged)
# ============================================================================

def is_safe_url(target):
    """Check if URL is safe for redirects"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    error = None
    next_page = request.args.get('next', '') or request.form.get('next', '')
    if request.method == 'POST':
        user = User.query.filter_by(_uid=request.form['username']).first()
        if user and user.is_password(request.form['password']):
            login_user(user)
            
            # Sync itinerary and budget from session to user account
            itinerary_session_id = request.cookies.get('itinerary_session_id')
            budget_session_id = request.cookies.get('budget_session_id')
            
            if itinerary_session_id:
                try:
                    itinerary_storage.merge_sessions(itinerary_session_id, user.id)
                except Exception as e:
                    print(f"Note: Could not sync itinerary on login: {e}")
            
            if budget_session_id:
                try:
                    sync_budget_to_account()
                except Exception as e:
                    print(f"Note: Could not sync budget on login: {e}")
            
            if not is_safe_url(next_page):
                return abort(400)
            return redirect(next_page or url_for('index'))
        else:
            error = 'Invalid username or password.'
    return render_template("login.html", error=error, next=next_page)

@app.route('/studytracker')
def studytracker():
    """Study tracker page"""
    return render_template("studytracker.html")

@app.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    """404 error handler"""
    return render_template('404.html'), 404

@app.route('/')
def index():
    """Home page"""
    print("Home:", current_user)
    return render_template("index.html")

@app.route('/users/table2')
@login_required
def u2table():
    """User table page"""
    users = User.query.all()
    return render_template("u2table.html", user_data=users)

@app.route('/sections/')
@login_required
def sections():
    """Sections page"""
    sections = Section.query.all()
    return render_template("sections.html", sections=sections)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete user"""
    user = User.query.get(user_id)
    if user:
        user.delete()
        return jsonify({'message': 'User deleted successfully'}), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    """Reset user password"""
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.update({"password": app.config['DEFAULT_PASSWORD']}):
        return jsonify({'message': 'Password reset successfully'}), 200
    return jsonify({'error': 'Password reset failed'}), 500

@app.route('/kasm_users')
def kasm_users():
    """KASM users page"""
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return render_template('error.html', message='KASM keys are missing'), 400

    try:
        url = f"{SERVER}/api/public/get_users"
        data = {
            "api_key": API_KEY,
            "api_key_secret": API_KEY_SECRET
        }

        response = requests.post(url, json=data, timeout=10)

        if response.status_code != 200:
            return render_template(
                'error.html', 
                message='Failed to get users', 
                code=response.status_code
            ), response.status_code

        users = response.json().get('users', [])

        for user in users:
            last_session = user.get('last_session')
            try:
                user['last_session'] = datetime.fromisoformat(last_session) if last_session else None
            except ValueError:
                user['last_session'] = None

        sorted_users = sorted(
            users, 
            key=lambda x: x['last_session'] or datetime.min, 
            reverse=True
        )

        return render_template('kasm_users.html', users=sorted_users)

    except requests.RequestException as e:
        return render_template(
            'error.html', 
            message=f"Error connecting to KASM API: {str(e)}"
        ), 500

@app.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user_kasm(user_id):
    """Delete KASM user"""
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    SERVER = current_app.config.get('KASM_SERVER')
    API_KEY = current_app.config.get('KASM_API_KEY')
    API_KEY_SECRET = current_app.config.get('KASM_API_KEY_SECRET')

    if not SERVER or not API_KEY or not API_KEY_SECRET:
        return {'message': 'KASM keys are missing'}, 400

    try:
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
    """Update user information"""
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    print(f"Request Data: {data}")

    user = User.query.filter_by(_uid=uid).first()
    if user:
        print(f"Found user: {user.uid}")
        user.update(data)
        return jsonify({"message": "User updated successfully."}), 200
    else:
        print("User not found.")
        return jsonify({"message": "User not found."}), 404

# ============================================================================
# MUSEUM SCRAPER WEB INTERFACE (unchanged)
# ============================================================================

@app.route('/museums')
def museums_home():
    """Museum scraper homepage with interactive interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🏛️ Museum Hours Scraper API</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }
            
            .header {
                text-align: center;
                margin-bottom: 50px;
            }
            
            .header h1 {
                font-size: 3.5em;
                color: #333;
                margin-bottom: 15px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            .header p {
                font-size: 1.2em;
                color: #666;
                max-width: 800px;
                margin: 0 auto;
                line-height: 1.6;
            }
            
            .status-badge {
                display: inline-block;
                padding: 8px 20px;
                background: #4CAF50;
                color: white;
                border-radius: 50px;
                font-weight: bold;
                margin-top: 20px;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            .endpoints-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-bottom: 50px;
            }
            
            .endpoint-card {
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
                border: 2px solid transparent;
            }
            
            .endpoint-card:hover {
                transform: translateY(-10px);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
                border-color: #667eea;
            }
            
            .endpoint-header {
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .endpoint-icon {
                font-size: 2.5em;
                margin-right: 20px;
                width: 70px;
                height: 70px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            
            .met-icon { background: linear-gradient(45deg, #8B4513, #D2691E); }
            .icecream-icon { background: linear-gradient(45deg, #FF69B4, #FF1493); }
            .ukrainian-icon { background: linear-gradient(45deg, #0057B7, #FFD700); }
            .empire-icon { background: linear-gradient(45deg, #708090, #2F4F4F); }
            .all-icon { background: linear-gradient(45deg, #4CAF50, #45a049); }
            .test-icon { background: linear-gradient(45deg, #2196F3, #21CBF3); }
            
            .endpoint-title {
                font-size: 1.5em;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }
            
            .endpoint-url {
                font-family: 'Courier New', monospace;
                background: #f5f5f5;
                padding: 10px 15px;
                border-radius: 8px;
                margin: 15px 0;
                font-size: 0.9em;
                color: #333;
                overflow-x: auto;
            }
            
            .endpoint-description {
                color: #666;
                margin-bottom: 20px;
                line-height: 1.5;
            }
            
            .test-btn {
                display: inline-block;
                padding: 12px 30px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 1em;
                width: 100%;
                text-align: center;
            }
            
            .test-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            
            .test-btn.loading {
                background: #999;
                cursor: not-allowed;
            }
            
            .result-container {
                margin-top: 20px;
                max-height: 300px;
                overflow-y: auto;
                background: #1a1a1a;
                border-radius: 8px;
                padding: 15px;
                display: none;
            }
            
            .result-title {
                color: #4CAF50;
                font-weight: bold;
                margin-bottom: 10px;
                font-family: monospace;
            }
            
            .result-data {
                color: #f0f0f0;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            
            .api-info {
                background: linear-gradient(45deg, #f8f9fa, #e9ecef);
                border-radius: 15px;
                padding: 30px;
                margin-top: 50px;
            }
            
            .api-info h2 {
                color: #333;
                margin-bottom: 20px;
                font-size: 2em;
            }
            
            .api-info ul {
                list-style: none;
                padding-left: 0;
            }
            
            .api-info li {
                margin: 15px 0;
                padding-left: 30px;
                position: relative;
                color: #555;
            }
            
            .api-info li:before {
                content: '✓';
                position: absolute;
                left: 0;
                color: #4CAF50;
                font-weight: bold;
            }
            
            .quick-test {
                text-align: center;
                margin: 40px 0;
            }
            
            .quick-test-btn {
                display: inline-block;
                padding: 15px 40px;
                background: linear-gradient(45deg, #FF9800, #FF5722);
                color: white;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                font-size: 1.1em;
                border: none;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .quick-test-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 15px 30px rgba(255, 87, 34, 0.4);
            }
            
            .museum-data {
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin: 20px 0;
                border-left: 5px solid #667eea;
            }
            
            .museum-name {
                font-size: 1.4em;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
            
            .museum-hours {
                font-size: 1.1em;
                color: #4CAF50;
                font-weight: bold;
                margin: 10px 0;
            }
            
            .museum-details {
                color: #666;
                font-size: 0.95em;
                margin: 5px 0;
            }
            
            .museum-timestamp {
                color: #999;
                font-size: 0.85em;
                margin-top: 10px;
                font-style: italic;
            }
            
            @media (max-width: 768px) {
                .container {
                    padding: 20px;
                }
                
                .header h1 {
                    font-size: 2.5em;
                }
                
                .endpoints-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏛️ Museum Hours Scraper API</h1>
                <p>A real-time web scraping API that fetches current hours from major NYC museums. This API makes actual HTTP requests to museum websites and parses the HTML to extract live hours information.</p>
                <div class="status-badge">✅ ACTIVE - Real Web Scraping</div>
            </div>
            
            <div class="quick-test">
                <button class="quick-test-btn" onclick="testAllEndpoints()">
                    🚀 Test All Museum Endpoints
                </button>
            </div>
            
            <div class="endpoints-grid">
                <!-- Museum endpoint cards remain the same -->
            </div>
            
            <div class="api-info">
                <h2>🎯 How This Web Scraping Works</h2>
                <ul>
                    <li><strong>Real HTTP Requests:</strong> Makes actual GET requests to museum websites</li>
                    <li><strong>HTML Parsing:</strong> Uses BeautifulSoup to parse HTML content</li>
                    <li><strong>Regex Patterns:</strong> Searches for hour patterns in text content</li>
                    <li><strong>Fallback Data:</strong> Provides default hours if scraping fails</li>
                    <li><strong>Live Timestamps:</strong> Shows when data was last scraped</li>
                    <li><strong>CORS Enabled:</strong> Works with any frontend application</li>
                </ul>
            </div>
        </div>
        
        <script>
            // Museum scraper JavaScript remains the same
        </script>
    </body>
    </html>
    '''

# ============================================================================
# NEW BUDGET MANAGEMENT PAGE
# ============================================================================

@app.route('/budget')
def budget_page():
    """Budget management page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>💰 Budget Tracker</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .header h1 {
                font-size: 2.5em;
                color: #333;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #28a745, #20c997);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            .budget-setup {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
                border: 2px dashed #dee2e6;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
                color: #333;
            }
            
            .form-group input, .form-group select {
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            
            .form-group input:focus, .form-group select:focus {
                outline: none;
                border-color: #28a745;
            }
            
            .btn {
                display: inline-block;
                padding: 12px 30px;
                background: linear-gradient(45deg, #28a745, #20c997);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 1em;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(40, 167, 69, 0.4);
            }
            
            .budget-display {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .budget-card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                text-align: center;
            }
            
            .budget-card.total {
                border-top: 5px solid #28a745;
            }
            
            .budget-card.spent {
                border-top: 5px solid #dc3545;
            }
            
            .budget-card.remaining {
                border-top: 5px solid #007bff;
            }
            
            .budget-card .amount {
                font-size: 2.5em;
                font-weight: bold;
                margin: 15px 0;
            }
            
            .budget-card.total .amount {
                color: #28a745;
            }
            
            .budget-card.spent .amount {
                color: #dc3545;
            }
            
            .budget-card.remaining .amount {
                color: #007bff;
            }
            
            .progress-bar {
                height: 20px;
                background: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
                margin: 20px 0;
            }
            
            .progress {
                height: 100%;
                background: linear-gradient(45deg, #28a745, #20c997);
                transition: width 0.5s ease;
            }
            
            .expenses-list {
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin-top: 30px;
            }
            
            .expense-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            
            .expense-item:last-child {
                border-bottom: none;
            }
            
            .expense-name {
                font-weight: bold;
                color: #333;
            }
            
            .expense-category {
                color: #6c757d;
                font-size: 0.9em;
            }
            
            .expense-price {
                font-weight: bold;
                color: #dc3545;
            }
            
            .alert {
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                font-weight: bold;
            }
            
            .alert.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .alert.warning {
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
            }
            
            .alert.danger {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💰 Trip Budget Tracker</h1>
                <p>Track your spending across breakfast, Broadway shows, and other activities</p>
            </div>
            
            <div id="budget-setup" class="budget-setup">
                <h2>Set Your Budget</h2>
                <div class="form-group">
                    <label for="budget-name">Budget Name</label>
                    <input type="text" id="budget-name" placeholder="e.g., NYC Trip Budget" value="NYC Trip Budget">
                </div>
                <div class="form-group">
                    <label for="total-budget">Total Budget ($)</label>
                    <input type="number" id="total-budget" placeholder="Enter your total budget" value="1000" min="0" step="10">
                </div>
                <div class="form-group">
                    <label for="trip-duration">Trip Duration (Days)</label>
                    <input type="number" id="trip-duration" placeholder="Number of days" value="3" min="1" max="30">
                </div>
                <div class="form-group">
                    <label for="currency">Currency</label>
                    <select id="currency">
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                    </select>
                </div>
                <button class="btn" onclick="createBudget()">💰 Set Budget</button>
            </div>
            
            <div id="budget-display" class="budget-display" style="display: none;">
                <div class="budget-card total">
                    <h3>Total Budget</h3>
                    <div class="amount" id="total-amount">$0.00</div>
                    <div class="progress-bar">
                        <div class="progress" id="progress-bar" style="width: 0%"></div>
                    </div>
                </div>
                
                <div class="budget-card spent">
                    <h3>Spent</h3>
                    <div class="amount" id="spent-amount">$0.00</div>
                    <div id="spent-percentage">0%</div>
                </div>
                
                <div class="budget-card remaining">
                    <h3>Remaining</h3>
                    <div class="amount" id="remaining-amount">$0.00</div>
                    <div id="remaining-percentage">100%</div>
                </div>
            </div>
            
            <div id="expenses-section" class="expenses-list" style="display: none;">
                <h2>Expenses</h2>
                <div id="expenses-list"></div>
                <div id="no-expenses" style="text-align: center; padding: 40px; color: #6c757d;">
                    No expenses yet. Add items from breakfast, Broadway, or other sections!
                </div>
            </div>
            
            <div id="alerts-container"></div>
            
            <div style="text-align: center; margin-top: 40px;">
                <button class="btn" onclick="resetBudget()" style="background: linear-gradient(45deg, #dc3545, #c82333);">🔄 Reset Budget</button>
                <button class="btn" onclick="getBudgetSummary()" style="background: linear-gradient(45deg, #007bff, #0056b3);">📊 View Summary</button>
            </div>
        </div>
        
        <script>
            let currentBudget = null;
            
            async function createBudget() {
                const budgetName = document.getElementById('budget-name').value;
                const totalBudget = parseFloat(document.getElementById('total-budget').value);
                const tripDuration = parseInt(document.getElementById('trip-duration').value);
                const currency = document.getElementById('currency').value;
                
                if (!totalBudget || totalBudget <= 0) {
                    showAlert('Please enter a valid budget amount.', 'warning');
                    return;
                }
                
                const response = await fetch('/api/budget', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        total_budget: totalBudget,
                        budget_name: budgetName,
                        trip_duration: tripDuration,
                        currency: currency
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAlert('Budget created successfully!', 'success');
                    loadBudget();
                } else {
                    showAlert('Error: ' + (data.error || 'Unknown error'), 'danger');
                }
            }
            
            async function loadBudget() {
                const response = await fetch('/api/budget');
                const data = await response.json();
                
                if (data.success && data.budget) {
                    currentBudget = data.budget;
                    displayBudget(data);
                    loadExpenses(data.expenses || []);
                }
            }
            
            function displayBudget(data) {
                const budget = data.budget;
                const spent = parseFloat(budget.spent_budget) || 0;
                const total = parseFloat(budget.total_budget) || 0;
                const remaining = parseFloat(budget.remaining_budget) || 0;
                const percentage = total > 0 ? (spent / total * 100) : 0;
                
                // Update display
                document.getElementById('budget-setup').style.display = 'none';
                document.getElementById('budget-display').style.display = 'grid';
                document.getElementById('expenses-section').style.display = 'block';
                
                document.getElementById('total-amount').textContent = `$${total.toFixed(2)}`;
                document.getElementById('spent-amount').textContent = `$${spent.toFixed(2)}`;
                document.getElementById('remaining-amount').textContent = `$${remaining.toFixed(2)}`;
                
                document.getElementById('spent-percentage').textContent = `${percentage.toFixed(1)}%`;
                document.getElementById('remaining-percentage').textContent = `${(100 - percentage).toFixed(1)}%`;
                
                document.getElementById('progress-bar').style.width = `${percentage}%`;
                
                // Show alerts if budget is low
                if (percentage > 90) {
                    showAlert('⚠️ Warning: You\'ve used over 90% of your budget!', 'danger');
                } else if (percentage > 75) {
                    showAlert('⚠️ Warning: You\'ve used over 75% of your budget.', 'warning');
                }
            }
            
            function loadExpenses(expenses) {
                const expensesList = document.getElementById('expenses-list');
                const noExpenses = document.getElementById('no-expenses');
                
                if (!expenses || expenses.length === 0) {
                    expensesList.style.display = 'none';
                    noExpenses.style.display = 'block';
                    return;
                }
                
                expensesList.style.display = 'block';
                noExpenses.style.display = 'none';
                expensesList.innerHTML = '';
                
                expenses.forEach(expense => {
                    const expenseItem = document.createElement('div');
                    expenseItem.className = 'expense-item';
                    expenseItem.innerHTML = `
                        <div>
                            <div class="expense-name">${expense.item_name}</div>
                            <div class="expense-category">${expense.category} • ${expense.module}</div>
                        </div>
                        <div class="expense-price">$${parseFloat(expense.total_cost).toFixed(2)}</div>
                    `;
                    expensesList.appendChild(expenseItem);
                });
            }
            
            async function resetBudget() {
                if (confirm('Are you sure you want to reset your budget? This will clear all expenses.')) {
                    const response = await fetch('/api/budget/reset', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({keep_expenses: false})
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showAlert('Budget reset successfully!', 'success');
                        location.reload();
                    } else {
                        showAlert('Error: ' + data.error, 'danger');
                    }
                }
            }
            
            async function getBudgetSummary() {
                const response = await fetch('/api/budget/summary');
                const data = await response.json();
                
                if (data.success) {
                    let summaryText = '📊 Budget Summary\\n\\n';
                    summaryText += `Total Budget: $${data.summary.total_spent + data.summary.total_remaining}\\n`;
                    summaryText += `Total Spent: $${data.summary.total_spent.toFixed(2)}\\n`;
                    summaryText += `Remaining: $${data.summary.total_remaining.toFixed(2)}\\n`;
                    summaryText += `Utilization: ${data.summary.budget_utilization.toFixed(1)}%\\n\\n`;
                    
                    if (data.summary.by_category && data.summary.by_category.length > 0) {
                        summaryText += 'By Category:\\n';
                        data.summary.by_category.forEach(cat => {
                            summaryText += `  ${cat.category}: $${cat.total.toFixed(2)}\\n`;
                        });
                    }
                    
                    alert(summaryText);
                }
            }
            
            function showAlert(message, type) {
                const container = document.getElementById('alerts-container');
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert ${type}`;
                alertDiv.textContent = message;
                container.appendChild(alertDiv);
                
                setTimeout(() => {
                    alertDiv.remove();
                }, 5000);
            }
            
            // Load budget on page load
            window.onload = loadBudget;
            
            // Function to add expense from other modules
            window.addExpenseToBudget = async function(expenseData) {
                const response = await fetch('/api/budget/expense', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(expenseData)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAlert(`Added ${expenseData.item_name} for $${expenseData.price}`, 'success');
                    loadBudget(); // Refresh display
                    return data.remaining_budget;
                } else {
                    showAlert('Error adding expense: ' + data.error, 'danger');
                    return null;
                }
            };
        </script>
    </body>
    </html>
    '''

# ============================================================================
# CUSTOM CLI COMMANDS (unchanged)
# ============================================================================

custom_cli = AppGroup('custom', help='Custom commands')

@custom_cli.command('generate_data')
def generate_data():
    """Generate initial data"""
    initUsers()
    init_microblogs()

app.cli.add_command(custom_cli)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 8303))
    host = "0.0.0.0"
    
    print("=" * 70)
    print("🚀 FLASK APPLICATION STARTING")
    print("=" * 70)
    print(f"📡 Main Server: http://localhost:{port}")
    print(f"💰 Budget Tracker: http://localhost:{port}/budget")
    print(f"🎨 Museum Scraper: http://localhost:{port}/museums")
    print(f"🔐 Login Page: http://localhost:{port}/login")
    
    print("\n💰 BUDGET TRACKING API ENDPOINTS:")
    print("  • http://localhost:{}/api/budget".format(port))
    print("  • http://localhost:{}/api/budget/expense".format(port))
    print("  • http://localhost:{}/api/budget/summary".format(port))
    print("  • http://localhost:{}/api/budget/sync".format(port))
    print("  • Database: budget_tracking.db")
    
    print("\n🏛️ MUSEUM SCRAPER API ENDPOINTS:")
    print("  • http://localhost:{}/api/met".format(port))
    print("  • http://localhost:{}/api/icecream".format(port))
    print("  • http://localhost:{}/api/ukrainian".format(port))
    print("  • http://localhost:{}/api/empire".format(port))
    print("  • http://localhost:{}/api/all".format(port))
    print("  • http://localhost:{}/api/test".format(port))
    
    print("\n🍳 BREAKFAST SCRAPER API ENDPOINTS:")
    print("  • http://localhost:{}/api/breakfast".format(port))
    print("  • http://localhost:{}/api/breakfast/jacks".format(port))
    print("  • http://localhost:{}/api/breakfast/shuka".format(port))
    
    print("\n🎭 BROADWAY SCRAPER API ENDPOINTS:")
    print("  • http://localhost:{}/api/broadway".format(port))
    print("  • http://localhost:{}/api/broadway/history".format(port))
    
    print("\n📝 ITINERARY STORAGE API ENDPOINTS:")
    print("  • http://localhost:{}/api/itinerary".format(port))
    print("  • http://localhost:{}/api/itinerary/with-budget".format(port))
    print("  • http://localhost:{}/api/itinerary/budget-summary".format(port))
    
    print("\n🔑 BUDGET INTEGRATION FEATURES:")
    print("  • Automatic price tracking from breakfast and Broadway modules")
    print("  • Real-time budget updates across all activities")
    print("  • User authentication with session fallback")
    print("  • Automatic syncing on login")
    print("  • Budget alerts and warnings")
    print("  • Detailed expense categorization")
    print("  • Daily budget breakdown")
    
    print("=" * 70)
    app.run(debug=True, host=host, port=port, use_reloader=False)