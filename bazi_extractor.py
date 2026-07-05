#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
import time
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: The 'playwright' library is not installed.")
    print("Please install it using: pip install playwright && playwright install")
    sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Extract Bazi chart data from bazi.vn/bzchart or nguhanh.net/la-so-bat-tu")
    
    # Input source
    parser.add_argument("--source", type=str, choices=["bazi.vn", "nguhanh.net"], default="bazi.vn",
                        help="The source website to scrape from (default: bazi.vn)")
    
    # Bulk input option
    parser.add_argument("--csv", type=str, help="Path to CSV file containing profiles for bulk processing")
    
    # Single profile options (fallback if --csv is not provided)
    parser.add_argument("--name", type=str, default="Nguyen Van A", help="Full Name (Họ tên)")
    parser.add_argument("--dob", type=str, default="15/05/1990", help="Date of Birth in DD/MM/YYYY format")
    parser.add_argument("--hour", type=str, default="08:30", help="Time of Birth in HH:MM format (24h)")
    parser.add_argument("--gender", type=str, choices=["Nam", "Nữ", "nam", "nữ"], default="Nam", help="Gender (Nam/Nữ)")
    
    # Output and execution settings
    parser.add_argument("--output", type=str, help="Path to save output JSON data (default auto-generated based on source)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (no GUI)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay in seconds between requests in bulk mode")
    parser.add_argument("--debug", action="store_true", help="Save page HTML for debugging")
    return parser.parse_args()

def extract_bazi_chart_bazi_vn(soup, debug=False, profile_index=0):
    """
    Parse bazi.vn chart result page HTML using BeautifulSoup.
    """
    if debug:
        filename = f"result_bazi_vn_{profile_index}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print(f"[DEBUG] Saved result page HTML to {filename}")

    data = {"four_pillars": {}, "luck_pillars": [], "raw_chart_text": ""}
    pillars = ["Giờ", "Ngày", "Tháng", "Năm"]
    
    # Locate Bazi grid table
    tables = soup.find_all('table')
    for table in tables:
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if any(p in "".join(headers) for p in pillars) or len(headers) >= 4:
            rows = table.find_all('tr')
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if not cols:
                    continue
                row_label = cols[0]
                row_values = cols[1:]
                if len(row_values) >= 4:
                    data["four_pillars"][row_label] = {
                        "Hour": row_values[0] if len(row_values) > 0 else "",
                        "Day": row_values[1] if len(row_values) > 1 else "",
                        "Month": row_values[2] if len(row_values) > 2 else "",
                        "Year": row_values[3] if len(row_values) > 3 else ""
                    }
            break

    # Scrape Luck Pillars (Đại Vận)
    luck_section = soup.find(lambda tag: tag.name in ['h2', 'h3', 'div', 'p'] and "Đại Vận" in tag.get_text())
    if luck_section:
        parent = luck_section.parent
        luck_tables = parent.find_all('table') if parent else []
        for lt in luck_tables:
            rows = lt.find_all('tr')
            for r in rows:
                cols = [td.get_text(strip=True) for td in r.find_all(['td', 'th'])]
                if len(cols) > 2:
                    data["luck_pillars"].append(cols)

    chart_container = soup.find(id="chart-container") or soup.find(class_="chart") or soup.find(class_="la-so")
    if chart_container:
        data["raw_chart_text"] = chart_container.get_text(separator='\n', strip=True)
        
    return data

def extract_bazi_chart_nguhanh_net(soup, debug=False, profile_index=0):
    """
    Parse nguhanh.net chart result page HTML using BeautifulSoup.
    """
    if debug:
        filename = f"result_nguhanh_net_{profile_index}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print(f"[DEBUG] Saved result page HTML to {filename}")

    data = {"four_pillars": {}, "luck_pillars": [], "elements": {}, "raw_chart_text": ""}
    
    # 1. Parse Tứ Trụ Table (usually the first main table on result page)
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
                    
                    data["four_pillars"] = {
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
    
    # 2. Parse Elements (Ngũ Hành bổ khuyết)
    # nguhanh.net has a section showing percentages or weights of Kim, Mộc, Thủy, Hỏa, Thổ
    elements_section = soup.find(lambda tag: tag.name in ['h3', 'h4', 'div', 'p'] and "Tỷ lệ ngũ hành" in tag.get_text())
    if elements_section:
        parent = elements_section.parent
        if parent:
            # Look for progress bars or texts containing elements percentages
            data["elements"]["raw_text"] = parent.get_text(separator=' | ', strip=True)
            
    # 3. Parse Luck Pillars (Đại Vận)
    for table in tables:
        text = table.get_text()
        if "Đại Vận" in text and "Tuổi" in text:
            rows = table.find_all('tr')
            for row in rows:
                cols = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if len(cols) >= 2:
                    data["luck_pillars"].append(cols)

    # General info backup - just extract all text of the chart container
    la_so_container = soup.find(class_="la-so") or soup.find(id="lasotutru") or soup.find(class_="tracuu")
    if la_so_container:
        data["raw_chart_text"] = la_so_container.get_text(separator='\n', strip=True)
    else:
        main_content = soup.find(id="main") or soup.body
        if main_content:
            text_lines = [line.strip() for line in main_content.get_text(separator='\n').splitlines() if line.strip()]
            data["raw_chart_text"] = "\n".join(text_lines[:150])

    return data

def scrape_bazi_vn(page, name, dob, hour, gender, index=0, debug=False):
    """
    Scrape single profile from bazi.vn/bzchart.
    """
    day_str, month_str, year_str = dob.split("/")
    day, month, year = int(day_str), int(month_str), int(year_str)
    hour_str, min_str = hour.split(":")
    birth_hour, birth_min = int(hour_str), int(min_str)
    gender_val = gender.strip().capitalize()

    page.goto("https://bazi.vn/bzchart", timeout=30000)
    page.wait_for_load_state("networkidle")

    # Name
    name_input = page.locator("input[name*='name'], input[name*='ten'], input[name*='ho_ten']").first
    if name_input.count() > 0:
        name_input.fill(name)

    # DOB
    date_input = page.locator("input[type='date']").first
    if date_input.count() > 0:
        date_input.fill(f"{year:04d}-{month:02d}-{day:02d}")
    else:
        day_select = page.locator("select[name*='ngay'], select[id*='ngay']").first
        month_select = page.locator("select[name*='thang'], select[id*='thang']").first
        year_select = page.locator("select[name*='nam'], select[id*='nam']").first
        if day_select.count() > 0:
            day_select.select_option(value=str(day))
            month_select.select_option(value=str(month))
            year_select.select_option(value=str(year))

    # Time
    hour_select = page.locator("select[name*='gio'], select[id*='gio']").first
    min_select = page.locator("select[name*='phut'], select[id*='phut']").first
    if hour_select.count() > 0:
        try:
            hour_select.select_option(value=str(birth_hour))
        except Exception:
            hour_select.select_option(value=f"{birth_hour:02d}")
        if min_select.count() > 0:
            try:
                min_select.select_option(value=str(birth_min))
            except Exception:
                min_select.select_option(value=f"{birth_min:02d}")

    # Gender
    gender_select = page.locator("select[name*='gioi_tinh'], select[id*='gioi_tinh']").first
    if gender_select.count() > 0:
        try:
            gender_select.select_option(label=gender_val)
        except Exception:
            gender_select.select_option(value="1" if gender_val == "Nam" else "0")
    else:
        gender_radio = page.locator(f"input[type='radio'][value*='{gender_val.lower()}']").first
        if gender_radio.count() > 0:
            gender_radio.click()

    # Submit
    submit_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Lập lá số')").first
    if submit_btn.count() > 0:
        submit_btn.click()
    else:
        page.keyboard.press("Enter")

    page.wait_for_load_state("networkidle")
    time.sleep(2)

    soup = BeautifulSoup(page.content(), 'html.parser')
    result = extract_bazi_chart_bazi_vn(soup, debug=debug, profile_index=index)
    result["profile"] = {"name": name, "dob": dob, "hour": hour, "gender": gender_val}
    return result

def scrape_nguhanh_net(page, name, dob, hour, gender, index=0, debug=False):
    """
    Scrape single profile from nguhanh.net/la-so-bat-tu.
    """
    day_str, month_str, year_str = dob.split("/")
    day, month, year = int(day_str), int(month_str), int(year_str)
    hour_str, min_str = hour.split(":")
    birth_hour, birth_min = int(hour_str), int(min_str)
    gender_val = gender.strip().capitalize()

    page.goto("https://nguhanh.net/la-so-bat-tu", timeout=30000)
    page.wait_for_load_state("networkidle")

    # Name
    fullname_input = page.locator("#Fullname, input[name='Fullname']").first
    if fullname_input.count() > 0:
        fullname_input.fill(name)

    # DOB Selectors
    day_select = page.locator("#Day, select[name='Day']").first
    month_select = page.locator("#Month, select[name='Month']").first
    year_select = page.locator("#Year, select[name='Year']").first

    if day_select.count() > 0:
        day_select.select_option(value=str(day))
        month_select.select_option(value=str(month))
        year_select.select_option(value=str(year))

    # Time Selectors
    hour_select = page.locator("#Hour, select[name='Hour']").first
    min_select = page.locator("#Minutes, select[name='Minutes']").first
    if hour_select.count() > 0:
        hour_select.select_option(value=str(birth_hour))
        min_select.select_option(value=str(birth_min))

    # Gender Selectors
    # In nguhanh.net, gender is often selected via Nam/Nữ buttons or a specific select.
    # We locate any element containing Nam or Nữ options
    gender_radio = page.locator("input[type='radio'][value*='Nam'], input[type='radio'][id*='Nam'], label:has-text('Nam')").first
    if gender_val == "Nữ":
        gender_radio = page.locator("input[type='radio'][value*='Nữ'], input[type='radio'][id*='Nữ'], label:has-text('Nữ'), label:has-text('Nu')").first
    
    if gender_radio.count() > 0:
        gender_radio.click()

    # Opt-in for 100 years of luck pillars (OneHundredYears checkbox)
    one_hundred_years_cb = page.locator("#OneHundredYears").first
    if one_hundred_years_cb.count() > 0:
        one_hundred_years_cb.check()

    # Submit
    submit_btn = page.locator("#btnCreateLaSoTuTru").first
    if submit_btn.count() > 0:
        submit_btn.click()
    else:
        # Submit the form directly
        page.locator("form[data-selector='lasotutru-form']").first.evaluate("form => form.submit()")

    # Wait for AJAX to complete and render the specific result form with our profile name (hidden input state must be "attached")
    page.wait_for_selector(f"form.form-result-lasotutru input[value='{name}']", state="attached", timeout=25000)

    soup = BeautifulSoup(page.content(), 'html.parser')
    result = extract_bazi_chart_nguhanh_net(soup, debug=debug, profile_index=index)
    result["profile"] = {"name": name, "dob": dob, "hour": hour, "gender": gender_val}
    return result

def main():
    args = parse_arguments()
    profiles = []

    # Read profiles from CSV if specified
    if args.csv:
        if not os.path.exists(args.csv):
            print(f"Error: CSV file not found: {args.csv}")
            sys.exit(1)
        
        print(f"Reading profiles from CSV: {args.csv}")
        with open(args.csv, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                profiles.append({
                    "name": cleaned_row.get("name", "Unknown"),
                    "dob": cleaned_row.get("dob", ""),
                    "hour": cleaned_row.get("hour", "00:00"),
                    "gender": cleaned_row.get("gender", "Nam")
                })
        print(f"Loaded {len(profiles)} profiles for bulk Bazi extraction.")
    else:
        profiles.append({
            "name": args.name,
            "dob": args.dob,
            "hour": args.hour,
            "gender": args.gender
        })
        print(f"Running in single-profile mode for: {args.name}")

    # Set default output name based on source if not provided
    output_filename = args.output
    if not output_filename:
        suffix = "bazi_vn" if args.source == "bazi.vn" else "nguhanh_net"
        output_filename = f"bazi_{suffix}_results.json"

    results = []

    with sync_playwright() as p:
        print(f"Launching browser targeting source: {args.source}...")
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
            print(f"\n[{idx+1}/{len(profiles)}] Processing: {profile['name']} ({profile['dob']} {profile['hour']})")
            
            try:
                if args.source == "bazi.vn":
                    res = scrape_bazi_vn(
                        page=page,
                        name=profile["name"],
                        dob=profile["dob"],
                        hour=profile["hour"],
                        gender=profile["gender"],
                        index=idx,
                        debug=args.debug
                    )
                else:
                    res = scrape_nguhanh_net(
                        page=page,
                        name=profile["name"],
                        dob=profile["dob"],
                        hour=profile["hour"],
                        gender=profile["gender"],
                        index=idx,
                        debug=args.debug
                    )
                
                if res:
                    results.append(res)
                    print(f"-> Successfully extracted Bazi for {profile['name']}")
            except Exception as e:
                print(f"-> Error scraping {profile['name']}: {e}")
                results.append({
                    "profile": profile,
                    "error": str(e)
                })
            
            # Rate limit delay
            if idx < len(profiles) - 1:
                print(f"Sleeping for {args.delay}s...")
                time.sleep(args.delay)

        browser.close()

    output_data = {
        "metadata": {
            "source": args.source,
            "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_profiles": len(profiles),
            "successful": sum(1 for r in results if "error" not in r)
        },
        "results": results
    }

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print("\n=========================================")
    print(f"Extraction complete! Saved to: {output_filename}")
    print(f"Successfully processed {output_data['metadata']['successful']}/{len(profiles)} profiles.")
    print("=========================================")

if __name__ == "__main__":
    main()
