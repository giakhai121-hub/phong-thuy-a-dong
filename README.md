# Bazi.vn & Nguhanh.net Chart Data Extractor & Offline Calculator

This project provides tools to build your own standalone Bazi (Four Pillars of Destiny) software. It is split into two components:

1.  **Online Data Scrapers & SQLite Database Builder:** Scripts to automatically query birth details from `bazi.vn` and `nguhanh.net` and build a structured offline interpretations database.
2.  **Offline Bazi Calculation Engine:** A Python demo containing the astronomical formulas and Bazi rules (Stems, Branches, Hidden Stems, and Ten Deities) to calculate Bazi charts completely offline without internet.

---

## Prerequisites

Make sure you have Python 3 installed on your Mac.

---

## Setup Instructions

1. Open your terminal application on macOS.
2. Navigate to this project directory:
   ```bash
   cd "/Users/khaimac/.gemini/antigravity/scratch/bazi-extractor"
   ```
3. (Optional but recommended) Create and activate a python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install the required python libraries:
   ```bash
   pip install -r requirements.txt
   ```
5. Install Playwright browser engines:
   ```bash
   playwright install chromium
   ```

---

## Tools Included

### 1. Offline Bazi Calculator (`bazi_calculator_offline.py`)
This script contains the core formulas for Bazi chart calculations (Julian Day conversion, Day Jiazhi, Ngũ Hổ Độn, Ngũ Tý Độn, Hidden Stems, and Ten Deities).

To run the calculation demo offline:
```bash
python3 bazi_calculator_offline.py
```

### 2. SQLite Interpretation Database Builder (`bazi_database_builder.py`)
This tool generates random diverse profiles, inputs them to `nguhanh.net/la-so-bat-tu`, parses their text interpretations (Personality, Career, Health, Marriage, and Ngũ Hành elements), and saves them into a structured SQLite database (`bazi_interpretations.db`).

To build the database with 30 sample profiles:
```bash
python3 bazi_database_builder.py --count 30 --db bazi_interpretations.db
```
*Options:*
- `--count`: Number of profile variations to crawl.
- `--db`: SQLite database file path (default: `bazi_interpretations.db`).
- `--delay`: Seconds to wait between pages (default: `3.0` to avoid blocking).
- `--headless`: Run the browser in headless mode.

To query the scraped data from your SQLite file:
```bash
sqlite3 bazi_interpretations.db "SELECT day_master, personality_text FROM interpretations LIMIT 3;"
```

### 3. Profile Scraper & CSV Bulk Scraper (`bazi_extractor.py`)
This script runs a bulk or single profile extraction and outputs the Bazi data in a structured JSON file.

*Run single profile extraction:*
```bash
python3 bazi_extractor.py --source nguhanh.net --name "Nguyen Van A" --dob "15/05/1990" --hour "08:30" --gender "Nam"
```

*Run bulk extraction from CSV file:*
```bash
python3 bazi_extractor.py --csv sample_profiles.csv --source nguhanh.net --output nguhanh_results.json
```

---

> [!TIP]
> **Active Workspace Recommendation**: We recommend setting `/Users/khaimac/.gemini/antigravity/scratch/bazi-extractor` as your active workspace in Antigravity. This will allow you to easily view, edit, and manage these project files within your IDE.
