#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: The 'playwright' library is not installed.")
    print("Please install it using: pip install playwright && playwright install")
    sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scrape and build an offline SQLite database of Bazi interpretations from nguhanh.net")
    parser.add_argument("--db", type=str, default="bazi_interpretations.db", help="Path to output SQLite database")
    parser.add_argument("--count", type=int, default=30, help="Number of test profiles to crawl (default: 30)")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay in seconds between requests")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--debug", action="store_true", help="Save debug HTML files")
    return parser.parse_args()

def init_db(db_path):
    """
    Initialize SQLite database and create necessary tables.
    """
    print(f"Initializing SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table to store unique profiles and their calculated pillars
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            dob TEXT,
            hour TEXT,
            gender TEXT,
            day_master TEXT,
            year_pillar TEXT,
            month_pillar TEXT,
            day_pillar TEXT,
            hour_pillar TEXT,
            elements_json TEXT,
            crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table to store interpretations mapped by Day Master and categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interpretations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            day_master TEXT,
            personality_text TEXT,
            wealth_text TEXT,
            relationship_text TEXT,
            health_text TEXT,
            elements_advice_text TEXT,
            raw_content_text TEXT,
            FOREIGN KEY(profile_id) REFERENCES profiles(id)
        )
    ''')
    
    conn.commit()
    return conn

def get_existing_count(conn):
    """
    Get the number of profiles already successfully saved in the database.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM profiles")
        return cursor.fetchone()[0]
    except sqlite3.Error:
        return 0

def generate_random_birth_profiles(count):
    """
    Generate a diverse set of birth dates to cover different Bazi combinations (Day Masters, elements).
    We sample dates across 1900 - 2027.
    """
    profiles = []
    base_date = datetime(1900, 1, 1)
    
    # We step by 31 days (a prime number coprime to 60) to get a diverse spread of Day stems, Month branches, etc.
    for i in range(count):
        profile_date = base_date + timedelta(days=i * 31, hours=i * 5 % 24)
        dob_str = profile_date.strftime("%d/%m/%Y")
        hour_str = profile_date.strftime("%H:%M")
        gender = "Nam" if i % 2 == 0 else "Nữ"
        profiles.append({
            "name": f"Test Profile {i+1}",
            "dob": dob_str,
            "hour": hour_str,
            "gender": gender
        })
    return profiles

def extract_section_text(soup, keywords):
    """
    Extract paragraphs of text following a heading containing specific keywords.
    """
    for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b']):
        header_text = header.get_text().lower()
        if any(kw.lower() in header_text for kw in keywords):
            content = []
            sibling = header.next_sibling
            while sibling:
                # Stop if we hit another header
                if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                    break
                if sibling.name in ['p', 'div', 'span'] or isinstance(sibling, str):
                    text = sibling.get_text(strip=True) if not isinstance(sibling, str) else sibling.strip()
                    if text and not text.startswith("Quảng cáo") and not text.startswith("Đăng ký"):
                        content.append(text)
                sibling = sibling.next_sibling
            return "\n".join(content)
    return ""

def parse_nguhanh_result(html_content, profile, profile_index, debug=False):
    """
    Extract calculation results and text interpretations from the HTML.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    if debug:
        filename = f"db_debug_{profile_index}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print(f"Saved debug page to {filename}")

    data = {
        "pillars": {"Year": "", "Month": "", "Day": "", "Hour": ""},
        "day_master": "",
        "elements": {},
        "texts": {
            "personality": "",
            "wealth": "",
            "relationship": "",
            "health": "",
            "elements_advice": "",
            "raw_content": ""
        }
    }

    # 1. Parse Bát Tự table
    # We find the table containing the row labeled "BÁT TỰ" (or "BÁT\nTỰ")
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for r in rows:
            cols = [td.get_text(strip=True) for td in r.find_all(['td', 'th'])]
            if len(cols) >= 5:
                label = "".join(cols[0].split()).lower()
                if "báttự" in label or "báttu" in label or "battu" in label:
                    # Column order on nguhanh.net: Label, Year (1), Month (2), Day (3), Hour (4)
                    tds = r.find_all('td')
                    
                    year_divs = [d.get_text(strip=True) for d in tds[1].find_all('div') if d.get_text(strip=True)]
                    month_divs = [d.get_text(strip=True) for d in tds[2].find_all('div') if d.get_text(strip=True)]
                    day_divs = [d.get_text(strip=True) for d in tds[3].find_all('div') if d.get_text(strip=True)]
                    hour_divs = [d.get_text(strip=True) for d in tds[4].find_all('div') if d.get_text(strip=True)]
                    
                    if len(day_divs) >= 1:
                        data["day_master"] = day_divs[0]
                    
                    data["pillars"] = {
                        "Can": {
                            "Year": year_divs[0] if len(year_divs) > 0 else "",
                            "Month": month_divs[0] if len(month_divs) > 0 else "",
                            "Day": day_divs[0] if len(day_divs) > 0 else "",
                            "Hour": hour_divs[0] if len(hour_divs) > 0 else ""
                        },
                        "Chi": {
                            "Year": year_divs[1] if len(year_divs) > 1 else "",
                            "Month": month_divs[1] if len(month_divs) > 1 else "",
                            "Day": day_divs[1] if len(day_divs) > 1 else "",
                            "Hour": hour_divs[1] if len(hour_divs) > 1 else ""
                        }
                    }
                    break

    # 2. Extract elements percentages (Ngũ Hành)
    elements_section = soup.find(lambda tag: tag.name in ['h3', 'h4', 'div', 'p'] and "Tỷ lệ ngũ hành" in tag.get_text())
    if elements_section:
        parent = elements_section.parent
        if parent:
            # Map percentages (Kim, Mộc, Thủy, Hỏa, Thổ)
            data["elements"]["text"] = parent.get_text(separator=' | ', strip=True)

    # 3. Extract text sections by keywords
    data["texts"]["personality"] = extract_section_text(soup, ["tính cách", "tinh cach", "tính tình"])
    data["texts"]["wealth"] = extract_section_text(soup, ["tài lộc", "tai loc", "công danh", "sự nghiệp", "su nghiep"])
    data["texts"]["relationship"] = extract_section_text(soup, ["tình duyên", "tinh duyen", "gia đạo", "gia dao", "hôn nhân", "hon nhan"])
    data["texts"]["health"] = extract_section_text(soup, ["sức khỏe", "suc khoe", "bệnh tật"])
    data["texts"]["elements_advice"] = extract_section_text(soup, ["bổ khuyết", "cải vận", "vật phẩm"])

    # Fallback raw content text
    la_so_container = soup.find(class_="la-so") or soup.find(id="lasotutru") or soup.find(class_="tracuu")
    if la_so_container:
        data["texts"]["raw_content"] = la_so_container.get_text(separator='\n', strip=True)

    return data

def save_to_db(conn, profile, result):
    """
    Save the scraped profile and interpretations into SQLite.
    """
    cursor = conn.cursor()
    
    # 1. Insert Profile
    cursor.execute('''
        INSERT INTO profiles (name, dob, hour, gender, day_master, year_pillar, month_pillar, day_pillar, hour_pillar, elements_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        profile["name"],
        profile["dob"],
        profile["hour"],
        profile["gender"],
        result["day_master"],
        json.dumps(result["pillars"].get("Thiên Can", {}) or result["pillars"].get("Can", {})),
        json.dumps(result["pillars"].get("Địa Chi", {}) or result["pillars"].get("Chi", {})),
        "", # Placeholder for other representations
        "", # Placeholder for other representations
        json.dumps(result["elements"])
    ))
    
    profile_id = cursor.lastrowid
    
    # 2. Insert Interpretations
    cursor.execute('''
        INSERT INTO interpretations (profile_id, day_master, personality_text, wealth_text, relationship_text, health_text, elements_advice_text, raw_content_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        profile_id,
        result["day_master"],
        result["texts"]["personality"],
        result["texts"]["wealth"],
        result["texts"]["relationship"],
        result["texts"]["health"],
        result["texts"]["elements_advice"],
        result["texts"]["raw_content"]
    ))
    
    conn.commit()

def main():
    args = parse_arguments()
    conn = init_db(args.db)
    
    # Check how many profiles are already crawled to support RESUMING
    start_index = get_existing_count(conn)
    
    # Generate profile dates to crawl
    profiles = generate_random_birth_profiles(args.count)
    print(f"Generated {len(profiles)} diverse profile combinations for crawling.")
    
    if start_index > 0:
        if start_index >= len(profiles):
            print(f"Database already contains {start_index} profiles. Target count is {len(profiles)}. Nothing to do!")
            conn.close()
            sys.exit(0)
        else:
            print(f"Database already contains {start_index} profiles. Resuming from profile #{start_index + 1}...")

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        # PREVENT DOM WIPEOUT: Mock html2canvas as a read-only pending promise so it cannot be overwritten
        # and prevents the client script from emptying the Bazi table container.
        page.add_init_script("""
            Object.defineProperty(window, 'html2canvas', {
                value: () => new Promise(() => {}),
                writable: false,
                configurable: false
            });
        """)

        for idx, profile in enumerate(profiles):
            # Skip already crawled profiles
            if idx < start_index:
                continue
                
            print(f"\n[{idx+1}/{len(profiles)}] Scraping: {profile['name']} ({profile['dob']} {profile['hour']} - {profile['gender']})")
            
            day, month, year = map(int, profile["dob"].split("/"))
            hour, minute = map(int, profile["hour"].split(":"))
            gender_val = profile["gender"]

            try:
                page.goto("https://nguhanh.net/la-so-bat-tu", timeout=30000)
                
                # HIGH-SPEED OPTIMIZATION: Wait for input selector instead of networkidle (avoids waiting for third-party ads)
                page.wait_for_selector("#Fullname", timeout=15000)

                # Fill form fields
                page.fill("#Fullname", profile["name"])
                page.select_option("#Day", value=str(day))
                page.select_option("#Month", value=str(month))
                page.select_option("#Year", value=str(year))
                page.select_option("#Hour", value=str(hour))
                page.select_option("#Minutes", value=str(minute))

                gender_radio = page.locator("input[type='radio'][value*='Nam'], label:has-text('Nam')").first
                if gender_val == "Nữ":
                    gender_radio = page.locator("input[type='radio'][value*='Nữ'], label:has-text('Nữ'), label:has-text('Nu')").first
                if gender_radio.count() > 0:
                    gender_radio.click()

                # Enable 100 years đại vận to get maximum data
                one_hundred_years_cb = page.locator("#OneHundredYears").first
                if one_hundred_years_cb.count() > 0:
                    one_hundred_years_cb.check()

                # Submit
                submit_btn = page.locator("#btnCreateLaSoTuTru").first
                if submit_btn.count() > 0:
                    submit_btn.click()
                else:
                    # Fallback to submit form directly via JS
                    page.locator("form[data-selector='lasotutru-form']").first.evaluate("form => form.submit()")
                
                # Wait for AJAX to complete and render the specific result form with our profile name (hidden input state must be "attached")
                page.wait_for_selector(f"form.form-result-lasotutru input[value='{profile['name']}']", state="attached", timeout=25000)

                # Parse and Save
                html = page.content()
                result = parse_nguhanh_result(html, profile, idx, debug=args.debug)
                
                if result["day_master"]:
                    save_to_db(conn, profile, result)
                    print(f"-> Saved interpretations for Day Master: {result['day_master']}")
                else:
                    print(f"-> Warning: Could not detect Day Master. Current URL: {page.url}")
                    with open("failed_page_debug.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("-> Saved failed page HTML to failed_page_debug.html for inspection.")
                    print("Skipping save.")

            except Exception as e:
                print(f"-> Error crawling profile {idx+1}: {e}")

            # Sleep between queries
            if idx < len(profiles) - 1:
                print(f"Sleeping for {args.delay}s...")
                time.sleep(args.delay)

        browser.close()
    
    # Query summary count
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM profiles")
    profiles_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT day_master, COUNT(*) FROM profiles GROUP BY day_master")
    groups = cursor.fetchall()
    
    conn.close()
    
    print("\n=========================================")
    print("Database construction complete!")
    print(f"SQLite file saved to: {args.db}")
    print(f"Total profiles saved: {profiles_count}")
    print("Day Masters distribution:")
    for gm, cnt in groups:
        print(f" - {gm}: {cnt} records")
    print("=========================================")

if __name__ == "__main__":
    main()
