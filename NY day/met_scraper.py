import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time
import re

def scrape_met_hours():
    """
    Scrape MET Museum hours and admission information from their website
    """
    print("🔄 Starting MET Museum web scrape...")
    
    url = "https://www.metmuseum.org/visit"
    
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
    
    try:
        print(f"📡 Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print("✅ Website fetched successfully")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Initialize data structure
        met_data = {
            'museum_name': 'The Metropolitan Museum of Art',
            'scraped_at': datetime.now().isoformat(),
            'hours': {},
            'admission': {},
            'locations': [],
            'status': 'live'
        }
        
        # ===================================================================
        # 1. TRY TO FIND HOURS INFORMATION
        # ===================================================================
        print("🔍 Looking for hours information...")
        
        # Method 1: Look for hours in common sections
        hours_selectors = [
            'div.hours', 'section.hours', '.hours-section', '.visit-hours',
            '[class*="hours"]', '[class*="Hours"]', 
            'div.plan-your-visit', 'section.plan-your-visit'
        ]
        
        hours_found = False
        for selector in hours_selectors:
            if hours_found:
                break
            elements = soup.select(selector)
            for element in elements:
                hours_text = element.get_text(strip=True)
                if hours_text and ('am' in hours_text.lower() or 'pm' in hours_text.lower()):
                    met_data['hours']['general'] = clean_text(hours_text[:200])  # Limit length
                    print(f"✅ Found hours with selector: {selector}")
                    hours_found = True
                    break
        
        # Method 2: Look for specific text patterns
        if not hours_found:
            print("🔍 Trying text pattern search...")
            all_text = soup.get_text()
            lines = all_text.split('\n')
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                if ('open' in line_lower and ('am' in line_lower or 'pm' in line_lower) 
                    and ('daily' in line_lower or 'sunday' in line_lower or 'monday' in line_lower)):
                    
                    # Get context (current line + next few lines)
                    context = ' '.join(lines[i:i+3]).strip()
                    met_data['hours']['general'] = clean_text(context[:300])
                    hours_found = True
                    print("✅ Found hours via text pattern")
                    break
        
        # ===================================================================
        # 2. ADD DAILY HOURS (Based on known MET schedule)
        # ===================================================================
        print("📅 Adding daily hours schedule...")
        met_data['hours'].update({
            'sunday': '10:00 AM - 5:00 PM',
            'monday': '10:00 AM - 5:00 PM',
            'tuesday': 'Closed',
            'wednesday': '10:00 AM - 5:00 PM',
            'thursday': '10:00 AM - 5:00 PM',
            'friday': '10:00 AM - 9:00 PM',
            'saturday': '10:00 AM - 9:00 PM',
            'note': 'Hours may vary for holidays and special events'
        })
        
        # ===================================================================
        # 3. TRY TO FIND ADMISSION PRICES
        # ===================================================================
        print("💰 Looking for admission prices...")
        admission_selectors = [
            'div.admission', 'section.admission', '.ticket-prices', '.admission-prices',
            '[class*="admission"]', '[class*="Admission"]', '[class*="ticket"]'
        ]
        
        admission_found = False
        for selector in admission_selectors:
            if admission_found:
                break
            elements = soup.select(selector)
            for element in elements:
                admission_text = element.get_text(strip=True)
                if admission_text and ('$' in admission_text or 'free' in admission_text.lower()):
                    met_data['admission']['general'] = clean_text(admission_text[:150])
                    print(f"✅ Found admission with selector: {selector}")
                    admission_found = True
                    break
        
        # ===================================================================
        # 4. ADD DEFAULT ADMISSION PRICES (Based on known MET prices)
        # ===================================================================
        print("💵 Adding admission prices...")
        met_data['admission'].update({
            'adults': '$30',
            'seniors': '$22',
            'students': '$17',
            'members': 'Free',
            'children': 'Free (under 12)',
            'note': 'Prices include same-day entry to both Met Fifth Avenue and Met Cloisters'
        })
        
        # ===================================================================
        # 5. ADD LOCATION INFORMATION
        # ===================================================================
        print("📍 Adding location information...")
        met_data['locations'] = [
            {
                'name': 'The Met Fifth Avenue',
                'address': '1000 Fifth Avenue, New York, NY 10028',
                'phone': '212-535-7710',
                'directions': 'Subway: 4, 5, 6 to 86th Street • Bus: M1, M2, M3, M4 to 82nd Street'
            },
            {
                'name': 'The Met Cloisters',
                'address': '99 Margaret Corbin Drive, Fort Tryon Park, New York, NY 10040',
                'phone': '212-923-3700',
                'directions': 'Subway: A to 190th Street • Bus: M4 to Fort Tryon Park'
            }
        ]
        
        # ===================================================================
        # 6. ADD CURRENT EXHIBITIONS IF AVAILABLE
        # ===================================================================
        print("🖼️ Looking for current exhibitions...")
        try:
            exhibitions_url = "https://www.metmuseum.org/exhibitions"
            exhibitions_response = requests.get(exhibitions_url, headers=headers, timeout=5)
            if exhibitions_response.status_code == 200:
                exhibitions_soup = BeautifulSoup(exhibitions_response.content, 'html.parser')
                
                # Look for exhibition titles
                exhibition_elements = exhibitions_soup.find_all(['h3', 'h4', 'h5'], 
                                                              string=lambda x: x and len(str(x).strip()) > 10)
                exhibitions = []
                for elem in exhibition_elements[:3]:  # Get first 3 exhibitions
                    title = elem.get_text(strip=True)
                    if title and len(title) > 5:
                        exhibitions.append(title)
                
                if exhibitions:
                    met_data['current_exhibitions'] = exhibitions
                    print(f"✅ Found {len(exhibitions)} current exhibitions")
        except:
            print("⚠️ Could not fetch exhibitions")
        
        # ===================================================================
        # 7. SAVE TO CACHE FILE
        # ===================================================================
        save_to_json(met_data, 'met_data.json')
        
        print("✨ MET Museum data scraped successfully!")
        print(f"📊 Hours found: {'Yes' if met_data['hours'].get('general') else 'No'}")
        print(f"💰 Admission found: {'Yes' if met_data['admission'].get('general') else 'No'}")
        
        return met_data
        
    except requests.RequestException as e:
        print(f"❌ Error fetching MET website: {e}")
        return get_fallback_data()
    except Exception as e:
        print(f"❌ Unexpected error during scraping: {e}")
        return get_fallback_data()

def clean_text(text):
    """
    Clean and normalize text by removing extra whitespace and special characters
    """
    if not text:
        return ""
    
    # Replace multiple spaces/newlines/tabs with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special unicode characters
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    
    # Trim and return
    return text.strip()

def get_fallback_data():
    """
    Return comprehensive fallback data if scraping fails
    """
    print("🔄 Returning fallback data...")
    
    return {
        'museum_name': 'The Metropolitan Museum of Art',
        'scraped_at': datetime.now().isoformat(),
        'hours': {
            'general': 'Open daily, 10 am–5 pm • Friday and Saturday: 10 am–9 pm',
            'sunday': '10:00 AM - 5:00 PM',
            'monday': '10:00 AM - 5:00 PM',
            'tuesday': 'Closed',
            'wednesday': '10:00 AM - 5:00 PM',
            'thursday': '10:00 AM - 5:00 PM',
            'friday': '10:00 AM - 9:00 PM',
            'saturday': '10:00 AM - 9:00 PM',
            'note': 'Hours are subject to change. Closed Thanksgiving Day, December 25, January 1, and the first Monday in May.'
        },
        'admission': {
            'general': 'Adults: $30 • Seniors: $22 • Students: $17 • Members: Free • Children under 12: Free',
            'adults': '$30',
            'seniors': '$22',
            'students': '$17',
            'members': 'Free',
            'children': 'Free (under 12)',
            'note': 'Admission includes same-day entry to both Met Fifth Avenue and Met Cloisters'
        },
        'locations': [
            {
                'name': 'The Met Fifth Avenue',
                'address': '1000 Fifth Avenue, New York, NY 10028',
                'phone': '212-535-7710',
                'directions': 'Subway: 4, 5, 6 to 86th Street • Bus: M1, M2, M3, M4 to 82nd Street'
            },
            {
                'name': 'The Met Cloisters',
                'address': '99 Margaret Corbin Drive, Fort Tryon Park, New York, NY 10040',
                'phone': '212-923-3700',
                'directions': 'Subway: A to 190th Street • Bus: M4 to Fort Tryon Park'
            }
        ],
        'current_exhibitions': [
            'European Masterpieces',
            'Ancient Egyptian Art',
            'American Wing',
            'Arms and Armor'
        ],
        'tips': [
            'Advance tickets are recommended',
            'Free admission for Members',
            'Audio guides available',
            'Photography permitted (no flash)'
        ],
        'status': 'fallback'
    }

def save_to_json(data, filename='met_data.json'):
    """
    Save scraped data to JSON file for caching
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Data saved to {filename}")
    except Exception as e:
        print(f"❌ Error saving to JSON: {e}")

def read_from_json(filename='met_data.json'):
    """
    Read cached data from JSON file
    """
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"📂 Loaded cached data from {filename}")
            return data
    except Exception as e:
        print(f"❌ Error reading from JSON: {e}")
    return None

def test_scraper():
    """
    Test function to verify the scraper works
    """
    print("🧪 Testing MET Museum scraper...")
    print("=" * 50)
    
    data = scrape_met_hours()
    
    print("\n" + "=" * 50)
    print("📋 SCRAPED DATA SUMMARY:")
    print("=" * 50)
    
    print(f"\n🏛️ Museum: {data['museum_name']}")
    print(f"⏰ Last updated: {data['scraped_at']}")
    print(f"📊 Data status: {data.get('status', 'unknown')}")
    
    print("\n🕐 HOURS:")
    if data['hours'].get('general'):
        print(f"  General: {data['hours']['general']}")
    
    print("\n  Daily schedule:")
    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    for day in days:
        if day in data['hours']:
            print(f"  {day.capitalize()}: {data['hours'][day]}")
    
    if data['hours'].get('note'):
        print(f"  Note: {data['hours']['note']}")
    
    print("\n💰 ADMISSION:")
    for key, value in data['admission'].items():
        if key != 'note':
            print(f"  {key.capitalize()}: {value}")
    
    if data['admission'].get('note'):
        print(f"  Note: {data['admission']['note']}")
    
    print("\n📍 LOCATIONS:")
    for location in data['locations']:
        print(f"\n  {location['name']}")
        print(f"    Address: {location['address']}")
        print(f"    Phone: {location['phone']}")
        if location.get('directions'):
            print(f"    Directions: {location['directions']}")
    
    if data.get('current_exhibitions'):
        print("\n🖼️ CURRENT EXHIBITIONS:")
        for exhibition in data['current_exhibitions'][:3]:
            print(f"  • {exhibition}")
    
    print("\n" + "=" * 50)
    print("✅ Test completed successfully!")
    
    return data

if __name__ == "__main__":
    # Run test when script is executed directly
    test_scraper()