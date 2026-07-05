import os
import sqlite3
import json
import time
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

app = FastAPI(title="Bazi Interpretation Viewer & Calculator API")

DB_PATH = os.path.join(os.path.dirname(__file__), "bazi_interpretations.db")

class BirthProfile(BaseModel):
    name: str
    dob: str  # DD/MM/YYYY
    hour: str  # HH:MM
    gender: str  # Nam or Nữ
    focus_year: int = 2026
    one_hundred_years: bool = True

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Helper: Extract section text
def extract_section_text(soup, keywords):
    for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b']):
        header_text = header.get_text().lower()
        if any(kw.lower() in header_text for kw in keywords):
            content = []
            sibling = header.next_sibling
            while sibling:
                if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                    break
                if sibling.name in ['p', 'div', 'span'] or isinstance(sibling, str):
                    text = sibling.get_text(strip=True) if not isinstance(sibling, str) else sibling.strip()
                    if text and not text.startswith("Quảng cáo") and not text.startswith("Đăng ký"):
                        content.append(text)
                sibling = sibling.next_sibling
            return "\n".join(content)
    return ""

# Helper: Parse nguhanh.net HTML results
def parse_nguhanh_result(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
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
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for r in rows:
            cols = [td.get_text(strip=True) for td in r.find_all(['td', 'th'])]
            if len(cols) >= 5:
                label = "".join(cols[0].split()).lower()
                if "báttự" in label or "báttu" in label or "battu" in label:
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
            data["elements"]["text"] = parent.get_text(separator=' | ', strip=True)

    # 3. Extract text sections by keywords only from the result container
    result_container = soup.find(class_="result-lasotutru") or soup
    data["texts"]["personality"] = extract_section_text(result_container, ["tính cách", "tinh cach", "tính tình"])
    data["texts"]["wealth"] = extract_section_text(result_container, ["tài lộc", "tai loc", "công danh", "sự nghiệp", "su nghiep"])
    data["texts"]["relationship"] = extract_section_text(result_container, ["tình duyên", "tinh duyen", "gia đạo", "gia dao", "hôn nhân", "hon nhan"])
    data["texts"]["health"] = extract_section_text(result_container, ["sức khỏe", "suc khoe", "bệnh tật"])
    data["texts"]["elements_advice"] = extract_section_text(result_container, ["bổ khuyết", "cải vận", "vật phẩm"])
    
    # Save raw chart HTML (from main result container) with absolute image URLs
    la_so_container = soup.find(id="prtLaSoTuTru")
    if la_so_container:
        raw_html = str(la_so_container)
        # Fix relative image paths to absolute ones (e.g. for the logo and layout assets)
        raw_html = raw_html.replace('src="/', 'src="https://nguhanh.net/')
        raw_html = raw_html.replace("src='/", "src='https://nguhanh.net/")
        data["texts"]["raw_content"] = raw_html

    return data

# Helper: Crawl profile on demand from nguhanh.net
def crawl_profile_on_demand(profile: dict, focus_year: int, one_hundred_years: bool):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # PREVENT DOM WIPEOUT: Mock html2canvas
        page.add_init_script("""
            Object.defineProperty(window, 'html2canvas', {
                value: () => new Promise(() => {}),
                writable: false,
                configurable: false
            });
        """)
        
        day, month, year = map(int, profile["dob"].split("/"))
        hour, minute = map(int, profile["hour"].split(":"))
        gender_val = profile["gender"]
        
        page.goto("https://nguhanh.net/la-so-bat-tu", timeout=30000)
        page.wait_for_selector("#Fullname", timeout=15000)
        
        # Fill form
        page.fill("#Fullname", profile["name"])
        page.select_option("#Day", value=str(day))
        page.select_option("#Month", value=str(month))
        page.select_option("#Year", value=str(year))
        page.select_option("#Hour", value=str(hour))
        page.select_option("#Minutes", value=str(minute))
        page.select_option("#FocusYear", value=str(focus_year))
        
        gender_radio = page.locator("input[type='radio'][value*='Nam'], label:has-text('Nam')").first
        if gender_val == "Nữ":
            gender_radio = page.locator("input[type='radio'][value*='Nữ'], label:has-text('Nữ'), label:has-text('Nu')").first
        if gender_radio.count() > 0:
            gender_radio.click()
            
        one_hundred_years_cb = page.locator("#OneHundredYears").first
        if one_hundred_years_cb.count() > 0:
            if one_hundred_years:
                one_hundred_years_cb.check()
            else:
                one_hundred_years_cb.uncheck()
            
        # Submit
        submit_btn = page.locator("#btnCreateLaSoTuTru").first
        if submit_btn.count() > 0:
            submit_btn.click()
        else:
            page.locator("form[data-selector='lasotutru-form']").first.evaluate("form => form.submit()")
            
        # Wait for AJAX to complete and render the result form
        page.wait_for_selector(f"form.form-result-lasotutru input[value='{profile['name']}']", state="attached", timeout=25000)
        
        html = page.content()
        browser.close()
        return html

# Helper: Save crawled results to database
def save_crawled_to_db(profile: dict, result: dict):
    conn = get_db_connection()
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
        json.dumps(result["pillars"].get("Can", {})),
        json.dumps(result["pillars"].get("Chi", {})),
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
    conn.close()
    return profile_id

# API Endpoint: Calculate Bazi and save
@app.post("/api/calculate")
def calculate_bazi(profile: BirthProfile):
    try:
        profile_dict = {
            "name": profile.name,
            "dob": profile.dob,
            "hour": profile.hour,
            "gender": profile.gender
        }
        
        # 1. Crawl Bazi HTML
        html = crawl_profile_on_demand(profile_dict, profile.focus_year, profile.one_hundred_years)
        
        # 2. Parse result
        result = parse_nguhanh_result(html)
        
        if not result["day_master"]:
            raise HTTPException(status_code=400, detail="Could not calculate Bazi. Day Master not found in result.")
            
        # 3. Save to database
        profile_id = save_crawled_to_db(profile_dict, result)
        
        # 4. Format return object
        return {
            "profile": {
                "id": profile_id,
                **profile_dict,
                "day_master": result["day_master"],
                "year_pillar": result["pillars"].get("Can", {}),
                "month_pillar": result["pillars"].get("Chi", {}),
                "elements": result["elements"]
            },
            "interpretations": result["texts"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawling/Calculation failed: {str(e)}")

# API Endpoint: Get stats
@app.get("/api/stats")
def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM profiles")
        total_profiles = cursor.fetchone()[0]
        
        # Day Master distribution
        cursor.execute("SELECT day_master, COUNT(*) as count FROM profiles WHERE day_master IS NOT NULL AND day_master != '' GROUP BY day_master")
        day_master_counts = {row["day_master"]: row["count"] for row in cursor.fetchall()}
        
        # Gender distribution
        cursor.execute("SELECT gender, COUNT(*) as count FROM profiles GROUP BY gender")
        gender_counts = {row["gender"]: row["count"] for row in cursor.fetchall()}
        
        conn.close()
        return {
            "total_profiles": total_profiles,
            "day_master_distribution": day_master_counts,
            "gender_distribution": gender_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Endpoint: List profiles with pagination, search, and filters
@app.get("/api/profiles")
def list_profiles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: str = Query(None),
    day_master: str = Query(None),
    gender: str = Query(None)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM profiles WHERE 1=1"
        count_query = "SELECT COUNT(*) FROM profiles WHERE 1=1"
        params = []
        
        if q:
            query += " AND (name LIKE ? OR dob LIKE ?)"
            count_query += " AND (name LIKE ? OR dob LIKE ?)"
            params.extend([f"%{q}%", f"%{q}%"])
            
        if day_master:
            query += " AND day_master = ?"
            count_query += " AND day_master = ?"
            params.append(day_master)
            
        if gender:
            query += " AND gender = ?"
            count_query += " AND gender = ?"
            params.append(gender)
            
        # Get total count
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated data (ordered by id desc to show newest first)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        offset = (page - 1) * limit
        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall()
        
        profiles = []
        for row in rows:
            try:
                year_pillar = json.loads(row["year_pillar"]) if row["year_pillar"] else {}
            except:
                year_pillar = row["year_pillar"]
                
            try:
                month_pillar = json.loads(row["month_pillar"]) if row["month_pillar"] else {}
            except:
                month_pillar = row["month_pillar"]
                
            try:
                day_pillar = json.loads(row["day_pillar"]) if row["day_pillar"] else {}
            except:
                day_pillar = row["day_pillar"]
                
            try:
                hour_pillar = json.loads(row["hour_pillar"]) if row["hour_pillar"] else {}
            except:
                hour_pillar = row["hour_pillar"]
                
            try:
                elements = json.loads(row["elements_json"]) if row["elements_json"] else {}
            except:
                elements = {"text": row["elements_json"]} if row["elements_json"] else {}
                
            profiles.append({
                "id": row["id"],
                "name": row["name"],
                "dob": row["dob"],
                "hour": row["hour"],
                "gender": row["gender"],
                "day_master": row["day_master"],
                "year_pillar": year_pillar,
                "month_pillar": month_pillar,
                "day_pillar": day_pillar,
                "hour_pillar": hour_pillar,
                "elements": elements,
                "crawled_at": row["crawled_at"]
            })
            
        conn.close()
        
        return {
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit,
            "data": profiles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Endpoint: Get profile details and interpretations
@app.get("/api/profiles/{profile_id}")
def get_profile_details(profile_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get profile
        cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        p_row = cursor.fetchone()
        if not p_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Profile not found")
            
        try:
            year_pillar = json.loads(p_row["year_pillar"]) if p_row["year_pillar"] else {}
        except:
            year_pillar = p_row["year_pillar"]
            
        try:
            month_pillar = json.loads(p_row["month_pillar"]) if p_row["month_pillar"] else {}
        except:
            month_pillar = p_row["month_pillar"]
            
        try:
            day_pillar = json.loads(p_row["day_pillar"]) if p_row["day_pillar"] else {}
        except:
            day_pillar = p_row["day_pillar"]
            
        try:
            hour_pillar = json.loads(p_row["hour_pillar"]) if p_row["hour_pillar"] else {}
        except:
            hour_pillar = p_row["hour_pillar"]
            
        try:
            elements = json.loads(p_row["elements_json"]) if p_row["elements_json"] else {}
        except:
            elements = {"text": p_row["elements_json"]} if p_row["elements_json"] else {}
            
        profile = {
            "id": p_row["id"],
            "name": p_row["name"],
            "dob": p_row["dob"],
            "hour": p_row["hour"],
            "gender": p_row["gender"],
            "day_master": p_row["day_master"],
            "year_pillar": year_pillar,
            "month_pillar": month_pillar,
            "day_pillar": day_pillar,
            "hour_pillar": hour_pillar,
            "elements": elements,
            "crawled_at": p_row["crawled_at"]
        }
        
        # Get interpretations
        cursor.execute("SELECT * FROM interpretations WHERE profile_id = ?", (profile_id,))
        i_row = cursor.fetchone()
        interpretations = {}
        if i_row:
            interpretations = {
                "personality": i_row["personality_text"],
                "wealth": i_row["wealth_text"],
                "relationship": i_row["relationship_text"],
                "health": i_row["health_text"],
                "elements_advice": i_row["elements_advice_text"],
                "raw_content": i_row["raw_content_text"]
            }
            
        conn.close()
        return {
            "profile": profile,
            "interpretations": interpretations
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files folder
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "web")), name="static")

# Catch-all endpoint to serve index.html for frontend routing
@app.get("/")
def read_root():
    index_path = os.path.join(os.path.dirname(__file__), "web", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Bazi Web Viewer Server is running. Frontend not found yet."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
