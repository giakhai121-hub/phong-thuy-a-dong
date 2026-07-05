#!/usr/bin/env python3
"""
Bazi Offline Calculation Engine - Formulas & Database Schema Demo
This script demonstrates the exact mathematical formulas, rules, and mappings 
required to calculate a Bazi (Four Pillars of Destiny) chart offline.
"""

import json

# =====================================================================
# 1. BAZI CORE DATABASE (Stems, Branches, Hidden Stems, Ten Deities)
# =====================================================================

# 10 Heavenly Stems (Thiên Can)
STEMS = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
STEM_ELEMENTS = {
    "Giáp": "Mộc (Dương)", "Ất": "Mộc (Âm)",
    "Bính": "Hỏa (Dương)", "Đinh": "Hỏa (Âm)",
    "Mậu": "Thổ (Dương)", "Kỷ": "Thổ (Âm)",
    "Canh": "Kim (Dương)", "Tân": "Kim (Âm)",
    "Nhâm": "Thủy (Dương)", "Quý": "Thủy (Âm)"
}

# 12 Earthly Branches (Địa Chi)
BRANCHES = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]
BRANCH_ANIMALS = {
    "Tý": "Chuột", "Sửu": "Trâu", "Dần": "Hổ", "Mão": "Mèo",
    "Thìn": "Rồng", "Tỵ": "Rắn", "Ngọ": "Ngựa", "Mùi": "Dê",
    "Thân": "Khỉ", "Dậu": "Gà", "Tuất": "Chó", "Hợi": "Lợn"
}

# Earthly Branches Hidden Stems (Địa Chi Tàng Can) - Fixed Standard Mapping
HIDDEN_STEMS = {
    "Tý": [("Quý", 100)],
    "Sửu": [("Kỷ", 60), ("Tân", 30), ("Quý", 10)],
    "Dần": [("Giáp", 60), ("Bính", 30), ("Mậu", 10)],
    "Mão": [("Ất", 100)],
    "Thìn": [("Mậu", 60), ("Ất", 30), ("Quý", 10)],
    "Tỵ": [("Bính", 60), ("Canh", 30), ("Mậu", 10)],
    "Ngọ": [("Đinh", 70), ("Kỷ", 30)],
    "Mùi": [("Kỷ", 60), ("Ất", 30), ("Đinh", 10)],
    "Thân": [("Canh", 60), ("Nhâm", 30), ("Mậu", 10)],
    "Dậu": [("Tân", 100)],
    "Tuất": [("Mậu", 60), ("Tân", 30), ("Đinh", 10)],
    "Hợi": [("Nhâm", 70), ("Giáp", 30)]
}

# 60 Jiazhi Cycle (Lục Thập Hoa Giáp)
JIAZHI_CYCLE = []
s_idx, b_idx = 0, 0
for _ in range(60):
    JIAZHI_CYCLE.append(f"{STEMS[s_idx]} {BRANCHES[b_idx]}")
    s_idx = (s_idx + 1) % 10
    b_idx = (b_idx + 1) % 12

# Elements relationships (Ngũ Hành Tương Sinh Tương Khắc)
ELEMENT_RELATIONS = {
    # (Day Master Element, Other Element) -> Relation Type
    # Types: Same (Tỷ Kiếp), Produces (Thực Thương), Produced By (Kiêu Ấn), Controlled By (Tài Tinh), Controls (Quan Sát)
    ("Mộc", "Mộc"): "Same", ("Mộc", "Hỏa"): "Produces", ("Mộc", "Thổ"): "Controlled By", ("Mộc", "Kim"): "Controls", ("Mộc", "Thủy"): "Produced By",
    ("Hỏa", "Hỏa"): "Same", ("Hỏa", "Thổ"): "Produces", ("Hỏa", "Kim"): "Controlled By", ("Hỏa", "Thủy"): "Controls", ("Hỏa", "Mộc"): "Produced By",
    ("Thổ", "Thổ"): "Same", ("Thổ", "Kim"): "Produces", ("Thổ", "Thủy"): "Controlled By", ("Thổ", "Mộc"): "Controls", ("Thổ", "Hỏa"): "Produced By",
    ("Kim", "Kim"): "Same", ("Kim", "Thủy"): "Produces", ("Kim", "Mộc"): "Controlled By", ("Kim", "Hỏa"): "Controls", ("Kim", "Thổ"): "Produced By",
    ("Thủy", "Thủy"): "Same", ("Thủy", "Mộc"): "Produces", ("Thủy", "Hỏa"): "Controlled By", ("Thủy", "Kim"): "Controls", ("Thủy", "Hỏa"): "Produced By",  # Fix Thủy - Thổ
}
# Correct relationship definitions helper
ELEMENTS = ["Mộc", "Hỏa", "Thổ", "Kim", "Thủy"]

def get_element_relation(dm_elem, other_elem):
    """
    Get relationship between Day Master Element and another Element.
    """
    dm_idx = ELEMENTS.index(dm_elem)
    other_idx = ELEMENTS.index(other_elem)
    
    diff = (other_idx - dm_idx) % 5
    if diff == 0:
        return "Same"          # Tỷ Kiếp
    elif diff == 1:
        return "Produces"      # Thực Thương
    elif diff == 2:
        return "Controlled By" # Tài Tinh (DM controls other)
    elif diff == 3:
        return "Controls"      # Quan Sát (Other controls DM)
    else:
        return "Produced By"   # Kiêu Ấn (Other produces DM)

# =====================================================================
# 2. BAZI CALCULATION FORMULAS
# =====================================================================

def calculate_julian_day(day, month, year):
    """
    Formula to convert Gregorian date to Julian Day Number (JDN).
    """
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = a // 4
    c = 2 - a + b
    d = int(365.25 * (year + 4716))
    e = int(30.6001 * (month + 1))
    jdn = c + d + e + day - 1524.5
    return int(jdn + 0.5)

def get_day_pillar_index(day, month, year):
    """
    Formula: Day Jiazhi Index = (JDN + 25) % 60
    Returns index from 0 to 59 representing the Day Pillar.
    """
    jdn = calculate_julian_day(day, month, year)
    return (jdn + 25) % 60

def get_month_stem_index(year_stem_idx, month_branch_idx):
    """
    Formula (Ngũ Hổ Độn): Month Stem Index = (Year Stem Index * 2 + Month Branch Index) % 10
    Note: Month Branch index is 2 for Dần, 3 for Mão, etc.
    """
    return (year_stem_idx * 2 + month_branch_idx) % 10

def get_hour_stem_index(day_stem_idx, hour_branch_idx):
    """
    Formula (Ngũ Tý Độn): Hour Stem Index = (Day Stem Index * 2 + Hour_Branch_Index) % 10
    Note: Hour Branch index is 0 for Tý, 1 for Sửu, etc.
    """
    return (day_stem_idx * 2 + hour_branch_idx) % 10

def get_hour_branch_index(hour_24h):
    """
    Maps 24h hour of birth to 12 Earthly Branches.
    """
    # 23:00 - 01:00 is Tý (0)
    if hour_24h >= 23 or hour_24h < 1:
        return 0
    return (hour_24h + 1) // 2

# =====================================================================
# 3. TEN DEITIES (THẬP THẦN) DETERMINATION
# =====================================================================

def determine_deity(day_master, other_stem):
    """
    Determine the Deity (Thập Thần) based on Day Master stem and another stem.
    """
    dm_desc = STEM_ELEMENTS[day_master] # e.g. "Mộc (Dương)"
    other_desc = STEM_ELEMENTS[other_stem] # e.g. "Kim (Âm)"
    
    dm_elem, dm_polar = dm_desc.split(" ")
    other_elem, other_polar = other_desc.split(" ")
    
    relation = get_element_relation(dm_elem, other_elem)
    same_polar = (dm_polar == other_polar)
    
    if relation == "Same":
        return "Tỷ Kiên" if same_polar else "Kiếp Tài"
    elif relation == "Produces":
        return "Thực Thần" if same_polar else "Thương Quan"
    elif relation == "Controlled By":
        return "Thiên Tài" if same_polar else "Chính Tài"
    elif relation == "Controls":
        return "Thất Sát" if same_polar else "Chính Quan"
    else: # Produced By
        return "Thiên Ấn" if same_polar else "Chính Ấn"

# =====================================================================
# 4. OFFLINE BAZI CHART BUILDER DEMO
# =====================================================================

def build_bazi_chart(year_pillar, month_pillar, day_pillar, hour_pillar):
    """
    Build complete Bazi metadata chart offline.
    """
    # Extract stems and branches
    y_stem, y_branch = year_pillar.split(" ")
    m_stem, m_branch = month_pillar.split(" ")
    d_stem, d_branch = day_pillar.split(" ")
    h_stem, h_branch = hour_pillar.split(" ")
    
    day_master = d_stem
    
    chart = {
        "Pillars": {
            "Year": year_pillar,
            "Month": month_pillar,
            "Day": day_pillar,
            "Hour": hour_pillar
        },
        "Day Master (Nhật Chủ)": day_master,
        "Stems Deities (Thập Thần Thiên Can)": {
            "Year Stem": determine_deity(day_master, y_stem),
            "Month Stem": determine_deity(day_master, m_stem),
            "Hour Stem": determine_deity(day_master, h_stem),
        },
        "Hidden Stems (Địa Chi Tàng Can)": {
            "Year Branch": HIDDEN_STEMS[y_branch],
            "Month Branch": HIDDEN_STEMS[m_branch],
            "Day Branch": HIDDEN_STEMS[d_branch],
            "Hour Branch": HIDDEN_STEMS[h_branch],
        },
        "Branch Deities (Thập Thần Địa Chi)": {}
    }
    
    # Calculate Deities for all Hidden Stems
    for branch_key, hidden_list in chart["Hidden Stems"].items():
        chart["Branch Deities"][branch_key] = [
            (stem, weight, determine_deity(day_master, stem))
            for stem, weight in hidden_list
        ]
        
    return chart

if __name__ == "__main__":
    # Test calculations for: 15/05/1990 at 08:30 (Day: Giáp Ngọ, Month: Tân Tỵ, Year: Canh Ngọ, Hour: Mậu Thìn)
    print("--- Bazi Offline Engine Formulas Demo ---")
    
    # Can Chi pillars mapping
    y_pillar = "Canh Ngọ"
    m_pillar = "Tân Tỵ"
    d_pillar = "Giáp Ngọ"
    h_pillar = "Mậu Thìn"
    
    chart = build_bazi_chart(y_pillar, m_pillar, d_pillar, h_pillar)
    print(json.dumps(chart, indent=2, ensure_ascii=False))
