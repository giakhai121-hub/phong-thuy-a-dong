// Global Application State
const state = {
    currentPage: 1,
    limit: 20,
    search: '',
    dayMaster: '',
    gender: '',
    stats: null
};

// Elements Matching Table (Vietnamese Can Chi to Element)
function getElementInfo(name) {
    if (!name) return { className: '', label: 'Chưa rõ' };
    const cleanName = name.trim();
    
    const moc = ['Giáp', 'Ất', 'Dần', 'Mão'];
    const hoa = ['Bính', 'Đinh', 'Tỵ', 'Ngọ'];
    const tho = ['Mậu', 'Kỷ', 'Thìn', 'Tuất', 'Sửu', 'Mùi'];
    const kim = ['Canh', 'Tân', 'Thân', 'Dậu'];
    const thuy = ['Nhâm', 'Quý', 'Hợi', 'Tý'];
    
    if (moc.includes(cleanName)) return { className: 'el-moc', label: 'Mộc' };
    if (hoa.includes(cleanName)) return { className: 'el-hoa', label: 'Hỏa' };
    if (tho.includes(cleanName)) return { className: 'el-tho', label: 'Thổ' };
    if (kim.includes(cleanName)) return { className: 'el-kim', label: 'Kim' };
    if (thuy.includes(cleanName)) return { className: 'el-thuy', label: 'Thủy' };
    
    return { className: '', label: 'Khác' };
}

// Init & Load Data
document.addEventListener('DOMContentLoaded', () => {
    initFormSelects();
    loadStats();
    loadProfiles();
    setupEventListeners();
});

// Populate dropdown select options for calculator form
function initFormSelects() {
    // Populate Days datalist (01-31)
    const daysList = document.getElementById('days-list');
    if (daysList) {
        daysList.innerHTML = '';
        for (let i = 1; i <= 31; i++) {
            const val = i.toString().padStart(2, '0');
            const opt = document.createElement('option');
            opt.value = val;
            daysList.appendChild(opt);
        }
    }
    const dayInput = document.getElementById('calc-day');
    if (dayInput) dayInput.value = "15";

    // Populate Months datalist (01-12)
    const monthsList = document.getElementById('months-list');
    if (monthsList) {
        monthsList.innerHTML = '';
        for (let i = 1; i <= 12; i++) {
            const val = i.toString().padStart(2, '0');
            const opt = document.createElement('option');
            opt.value = val;
            monthsList.appendChild(opt);
        }
    }
    const monthInput = document.getElementById('calc-month');
    if (monthInput) monthInput.value = "06";

    // Populate Years datalist (2030 down to 1900)
    const yearsList = document.getElementById('years-list');
    if (yearsList) {
        yearsList.innerHTML = '';
        for (let i = 2030; i >= 1900; i--) {
            const opt = document.createElement('option');
            opt.value = i.toString();
            yearsList.appendChild(opt);
        }
    }
    const yearInput = document.getElementById('calc-year');
    if (yearInput) yearInput.value = "1990";

    // Hours (0-23)
    const hourSelect = document.getElementById('calc-hour');
    for (let i = 0; i < 24; i++) {
        const val = i.toString().padStart(2, '0');
        hourSelect.add(new Option(val + " Giờ", val));
    }
    hourSelect.value = "12"; // default middle

    // Minutes (0-59)
    const minuteSelect = document.getElementById('calc-minute');
    for (let i = 0; i < 60; i++) {
        const val = i.toString().padStart(2, '0');
        minuteSelect.add(new Option(val + " Phút", val));
    }
    minuteSelect.value = "00"; // default

    // Focus Year (Năm tính: 1900-2056)
    const focusYearSelect = document.getElementById('calc-focus-year');
    for (let i = 2026; i >= 1900; i--) {
        focusYearSelect.add(new Option(i.toString(), i.toString()));
    }
    for (let i = 2027; i <= 2056; i++) {
        focusYearSelect.add(new Option(i.toString(), i.toString()));
    }
    focusYearSelect.value = "2026"; // default
}

// Switch between panels (Calculator and Explorer)
window.switchView = function(viewName) {
    document.querySelectorAll('.nav-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));

    if (viewName === 'calculator') {
        document.getElementById('tab-btn-calculator').classList.add('active');
        document.getElementById('panel-calculator').classList.add('active');
    } else {
        document.getElementById('tab-btn-explorer').classList.add('active');
        document.getElementById('panel-explorer').classList.add('active');
        // Refresh explorer values
        loadStats();
        loadProfiles();
    }
};

// Setup Listeners
function setupEventListeners() {
    // Search input (with 350ms debounce)
    let searchTimeout;
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                state.search = e.target.value.trim();
                state.currentPage = 1;
                loadProfiles();
            }, 350);
        });
    }

    // Day Master filter dropdown
    const filterDayMaster = document.getElementById('filter-day-master');
    if (filterDayMaster) {
        filterDayMaster.addEventListener('change', (e) => {
            state.dayMaster = e.target.value;
            state.currentPage = 1;
            loadProfiles();
        });
    }

    // Gender filter dropdown
    const filterGender = document.getElementById('filter-gender');
    if (filterGender) {
        filterGender.addEventListener('change', (e) => {
            state.gender = e.target.value;
            state.currentPage = 1;
            loadProfiles();
        });
    }

    // Modal Close
    const closeModalBtn = document.getElementById('close-modal-btn');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }
    
    const profileModal = document.getElementById('profile-modal');
    if (profileModal) {
        profileModal.addEventListener('click', (e) => {
            if (e.target.id === 'profile-modal') closeModal();
        });
    }

    // Bazi calculator form submission
    const calcForm = document.getElementById('bazi-calc-form');
    if (calcForm) {
        calcForm.addEventListener('submit', handleCalculatorSubmit);
    }
}

// Handle Form Submission: POST /api/calculate
async function handleCalculatorSubmit(e) {
    e.preventDefault();
    const submitBtn = document.getElementById('submit-calc-btn');
    const resultArea = document.getElementById('calc-result-area');
    
    // Get form inputs
    const name = document.getElementById('calc-name').value.trim();
    const dayRaw = document.getElementById('calc-day').value.trim();
    const monthRaw = document.getElementById('calc-month').value.trim();
    const yearRaw = document.getElementById('calc-year').value.trim();
    if (!dayRaw || !monthRaw || !yearRaw) return;
    
    // Pad values properly (e.g. if they typed "5" instead of "05")
    const day = dayRaw.padStart(2, '0');
    const month = monthRaw.padStart(2, '0');
    const year = yearRaw;
    const dob = `${day}/${month}/${year}`;
    
    const hour = document.getElementById('calc-hour').value;
    const minute = document.getElementById('calc-minute').value;
    const gender = document.querySelector('input[name="calc-gender"]:checked').value;
    const focus_year = parseInt(document.getElementById('calc-focus-year').value);
    const one_hundred_years = document.getElementById('calc-one-hundred-years').checked;
    
    const birthHour = `${hour}:${minute}`;

    // Show loading spinner with cycling messages
    submitBtn.disabled = true;
    resultArea.innerHTML = `
        <div class="loading-state">
            <i class="fa-solid fa-circle-notch fa-spin"></i>
            <h3 style="margin-top: 15px; color: #fff;">Đang kết nối ngầm...</h3>
            <p id="loading-msg" style="font-size: 0.85rem; color: var(--text-muted); margin-top: 5px;">Đang gửi thông tin biểu mẫu sang nguhanh.net...</p>
        </div>
    `;

    // Rotate loading sub-messages to look premium
    const loadingMsgs = [
        "Đang điền thông tin và bấm 'Mở lá số'...",
        "Đang phân tích cấu trúc bảng Bát Tự...",
        "Đang bóc tách Thiên Can và Địa Chi...",
        "Đang tính toán tỷ lệ phân phối Ngũ Hành...",
        "Đang lưu thông tin lá số vào SQLite database..."
    ];
    let msgIdx = 0;
    const msgInterval = setInterval(() => {
        const msgEl = document.getElementById('loading-msg');
        if (msgEl) {
            msgEl.textContent = loadingMsgs[msgIdx % loadingMsgs.length];
            msgIdx++;
        }
    }, 2500);

    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, dob, hour: birthHour, gender, focus_year, one_hundred_years })
        });
        
        clearInterval(msgInterval);
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Cào thông tin thất bại.");
        }
        
        const data = await response.json();
        
        // Render Bazi result scroll on screen!
        renderCalculatorResult(data, resultArea);
        
        // Smoothly scroll down to the result area
        resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Update stats badge
        loadStats();
        
    } catch (error) {
        clearInterval(msgInterval);
        console.error("Calculation error:", error);
        resultArea.innerHTML = `
            <div class="result-placeholder" style="color: var(--element-hoa);">
                <i class="fa-solid fa-circle-exclamation placeholder-icon" style="color: var(--element-hoa);"></i>
                <h3 style="color: var(--element-hoa);">Lập Lá Số Thất Bại</h3>
                <p>${error.message || "Đã xảy ra lỗi trong quá trình cào thông tin. Vui lòng kiểm tra lại kết nối mạng hoặc thử lại sau."}</p>
            </div>
        `;
    } finally {
        submitBtn.disabled = false;
    }
}

// Fetch stats and render chart
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        state.stats = stats;

        // Render Stats Badge
        const badge = document.getElementById('total-count-badge');
        if (badge) {
            badge.textContent = stats.total_profiles.toLocaleString();
        }

        // Render Bar Chart
        renderStatsChart(stats.day_master_distribution);
    } catch (error) {
        console.error("Error loading stats:", error);
    }
}

// Render dynamic animated stats chart
function renderStatsChart(distribution) {
    const chartContainer = document.getElementById('day-master-chart');
    if (!chartContainer) return;
    chartContainer.innerHTML = '';

    const entries = Object.entries(distribution);
    if (entries.length === 0) {
        chartContainer.innerHTML = '<div class="empty-state">Không có dữ liệu phân tích</div>';
        return;
    }

    const maxCount = Math.max(...entries.map(([_, count]) => count));

    entries.forEach(([dayMaster, count]) => {
        const heightPercent = maxCount > 0 ? (count / maxCount) * 100 : 0;
        const elInfo = getElementInfo(dayMaster);

        const barWrapper = document.createElement('div');
        barWrapper.className = 'chart-bar-wrapper';

        barWrapper.innerHTML = `
            <div class="chart-bar-fill ${elInfo.className}" style="height: ${heightPercent}%" onclick="selectDayMaster('${dayMaster}')">
                <span class="chart-bar-value">${count}</span>
            </div>
            <span class="chart-bar-label">${dayMaster}</span>
        `;
        chartContainer.appendChild(barWrapper);
    });
}

// Helper to filter stats by clicking a bar chart
window.selectDayMaster = function(dayMaster) {
    document.getElementById('filter-day-master').value = dayMaster;
    state.dayMaster = dayMaster;
    state.currentPage = 1;
    loadProfiles();
};

// Fetch and load profiles grid
async function loadProfiles() {
    const gridContainer = document.getElementById('profiles-grid');
    if (!gridContainer) return;
    gridContainer.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải dữ liệu hồ sơ...</div>';

    try {
        const params = new URLSearchParams({
            page: state.currentPage,
            limit: state.limit
        });
        if (state.search) params.append('q', state.search);
        if (state.dayMaster) params.append('day_master', state.dayMaster);
        if (state.gender) params.append('gender', state.gender);

        const response = await fetch(`/api/profiles?${params.toString()}`);
        const result = await response.json();

        renderProfiles(result.data);
        renderPagination(result);
    } catch (error) {
        console.error("Error loading profiles:", error);
        gridContainer.innerHTML = '<div class="empty-state"><i class="fa-solid fa-circle-exclamation text-danger"></i> Lỗi tải dữ liệu. Vui lòng thử lại.</div>';
    }
}

// Render profile cards in grid
function renderProfiles(profiles) {
    const gridContainer = document.getElementById('profiles-grid');
    gridContainer.innerHTML = '';

    if (!profiles || profiles.length === 0) {
        gridContainer.innerHTML = '<div class="empty-state"><i class="fa-solid fa-folder-open"></i> Không tìm thấy hồ sơ nào phù hợp.</div>';
        return;
    }

    profiles.forEach(profile => {
        const elInfo = getElementInfo(profile.day_master);
        const card = document.createElement('div');
        card.className = 'profile-card card-glass';
        card.onclick = () => showProfileDetails(profile.id);

        const genderIcon = profile.gender === 'Nam' 
            ? '<i class="fa-solid fa-mars gender-icon nam" title="Nam"></i>' 
            : '<i class="fa-solid fa-venus gender-icon nu" title="Nữ"></i>';

        card.innerHTML = `
            <div class="profile-header">
                <span class="profile-name">${profile.name}</span>
                ${genderIcon}
            </div>
            <div class="profile-info-row">
                <i class="fa-regular fa-calendar"></i>
                <span>${profile.dob}</span>
            </div>
            <div class="profile-info-row">
                <i class="fa-regular fa-clock"></i>
                <span>${profile.hour}</span>
            </div>
            <span class="day-master-tag ${elInfo.className}">Nhật Chủ: ${profile.day_master || 'Chưa rõ'}</span>
        `;
        gridContainer.appendChild(card);
    });
}

// Render pagination buttons
function renderPagination(result) {
    const controls = document.getElementById('pagination-controls');
    controls.innerHTML = '';

    if (result.pages <= 1) return;

    const prevBtn = document.createElement('button');
    prevBtn.className = 'pag-btn';
    prevBtn.disabled = result.page === 1;
    prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
    prevBtn.onclick = () => {
        state.currentPage--;
        loadProfiles();
    };
    controls.appendChild(prevBtn);

    const info = document.createElement('span');
    info.className = 'pag-info';
    info.textContent = `Trang ${result.page} / ${result.pages} (Tổng ${result.total} dòng)`;
    controls.appendChild(info);

    const nextBtn = document.createElement('button');
    nextBtn.className = 'pag-btn';
    nextBtn.disabled = result.page === result.pages;
    nextBtn.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
    nextBtn.onclick = () => {
        state.currentPage++;
        loadProfiles();
    };
    controls.appendChild(nextBtn);
}

// Load and show details in modal
async function showProfileDetails(profileId) {
    const modal = document.getElementById('profile-modal');
    const content = document.getElementById('modal-content');
    content.innerHTML = '<div class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải thông tin chi tiết...</div>';
    
    modal.classList.add('active');

    try {
        const response = await fetch(`/api/profiles/${profileId}`);
        const data = await response.json();
        
        // Render Bazi content inside modal
        renderProfileModalContent(data, content);
    } catch (error) {
        console.error("Error loading profile details:", error);
        content.innerHTML = '<div class="empty-state">Không thể tải chi tiết hồ sơ.</div>';
    }
}

// Helper: Remove nguhanh.net branding and personalize Bazi table
function personalizeBaziTable(rawHtml) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(rawHtml, 'text/html');
    
    // 1. Remove logo image
    const logoImg = doc.querySelector('.ls-logo');
    if (logoImg) logoImg.remove();
    
    // 2. Personalize header info section (top-left box)
    const headerInfo = doc.querySelector('.header-info');
    if (headerInfo) {
        headerInfo.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; padding: 5px;">
                <i class="fa-solid fa-yin-yang" style="font-size: 2.8rem; color: #b8911c; animation: rotateSlow 20s linear infinite;"></i>
                <div style="text-align: left;">
                    <h4 style="color: #b8911c; font-family: 'Outfit', sans-serif; font-size: 1.25rem; font-weight: 800; margin: 0; line-height: 1.1; letter-spacing: 0.5px;">PHONG THỦY</h4>
                    <span style="color: rgba(255, 255, 255, 0.6); font-family: 'Inter', sans-serif; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Á Đông</span>
                </div>
            </div>
        `;
    }
    
    // 3. Remove logo td cell styling backgrounds if any
    const parentCell = doc.querySelector('.header-info')?.closest('td');
    if (parentCell) {
        parentCell.removeAttribute('style');
    }
    
    // 4. Wipe out any other texts referencing nguhanh.net and replace with Phong Thủy Á Đông
    const allElements = doc.getElementsByTagName('*');
    for (let el of allElements) {
        if (el.children.length === 0 && (el.textContent.includes('Nguhanh.net') || el.textContent.includes('nguhanh.net'))) {
            el.innerHTML = el.innerHTML.replace(/Nguhanh\.net/gi, 'Phong Thủy Á Đông');
        }
    }
    
    // 5. Remove footer text (Liên hệ với thầy Đoàn / Lá số lập tại) completely
    const textNodes = [];
    const walk = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while (node = walk.nextNode()) {
        const text = node.nodeValue;
        if (text.includes("Liên hệ với thầy Đoàn") || text.includes("Lá số lập tại")) {
            textNodes.push(node);
        }
    }
    
    textNodes.forEach(tNode => {
        const parent = tNode.parentElement;
        if (parent) {
            const tr = parent.closest('tr');
            if (tr) {
                tr.remove(); // Remove the entire table row holding the contact info
            } else {
                parent.remove(); // Otherwise just remove the parent element itself
            }
        }
    });
    
    const container = doc.getElementById('prtLaSoTuTru') || doc.body;
    return container.innerHTML;
}

// Render Bazi Scroll card & details modal
function renderProfileModalContent(data, targetContainer) {
    const profile = data.profile;
    const interpretations = data.interpretations;

    // Check if we have the raw HTML content of the Bazi table from nguhanh.net
    if (interpretations && interpretations.raw_content && interpretations.raw_content.trim().startsWith('<')) {
        const cleanedTableHtml = personalizeBaziTable(interpretations.raw_content);
        
        let html = `
            <div class="modal-title-section" style="border-bottom: 1px solid var(--border-glass); padding-bottom: 20px; margin-bottom: 25px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 class="modal-title" style="font-family: 'Outfit', sans-serif; font-size: 1.8rem; font-weight: 800; color: #fff; margin-bottom: 6px;">${profile.name}</h3>
                    <span class="day-master-tag el-tho" style="margin-top:0; font-size: 0.8rem; border-color: var(--accent-gold); color: #fff; background: var(--accent-gold);"><i class="fa-solid fa-cloud-arrow-down"></i> Đã lưu Database</span>
                </div>
                <div class="modal-subtitle" style="margin-top: 10px; font-size: 0.9rem; color: var(--text-muted); display: flex; gap: 15px;">
                    <span><i class="fa-solid fa-venus-mars"></i> Giới tính: <strong>${profile.gender}</strong></span>
                    <span><i class="fa-regular fa-calendar"></i> Sinh ngày: <strong>${profile.dob}</strong></span>
                    <span><i class="fa-regular fa-clock"></i> Giờ sinh: <strong>${profile.hour}</strong></span>
                </div>
            </div>
            
            <div class="nguhanh-table-wrapper" style="overflow-x: auto; border-radius: 12px; padding: 25px; margin-bottom: 30px;">
                <div id="prtLaSoTuTru" class="lasotutru">
                    ${cleanedTableHtml}
                </div>
            </div>
        `;

        // Render Elements Percentages
        let elementsHtml = '';
        const rawElementsText = profile.elements?.text || profile.elements?.raw_text || '';
        if (rawElementsText) {
            const parts = rawElementsText.split('|');
            if (parts.length >= 2) {
                elementsHtml += `<div class="elements-summary-grid">`;
                parts.forEach(part => {
                    const subParts = part.split(':');
                    if (subParts.length === 2) {
                        const elName = subParts[0].trim();
                        const elVal = subParts[1].trim();
                        const elInfo = getElementInfo(elName);
                        elementsHtml += `
                            <div class="el-bar-card">
                                <span class="el-name ${elInfo.className}-text" style="color: var(--element-${elInfo.className.replace('el-', '')})">${elName}</span>
                                <span class="el-percent">${elVal}</span>
                            </div>
                        `;
                    }
                });
                elementsHtml += `</div>`;
            } else {
                elementsHtml = `<div class="card-glass" style="padding: 15px; margin-top: 15px; font-size: 0.9rem; color: var(--text-muted);">${rawElementsText}</div>`;
            }
        }

        if (elementsHtml) {
            html += `
                <h4 class="section-title" style="margin-top: 30px;"><i class="fa-solid fa-chart-simple"></i> Cân Bằng Ngũ Hành</h4>
                ${elementsHtml}
            `;
        }

        // Render Interpretations Tabs
        let hasInterp = false;
        let interpTabsHtml = '';
        
        if (interpretations && Object.keys(interpretations).length > 0) {
            const categories = {
                "personality": { label: "Tính cách", icon: "fa-user-astronaut" },
                "wealth": { label: "Tài lộc", icon: "fa-briefcase" },
                "relationship": { label: "Tình duyên", icon: "fa-heart" },
                "health": { label: "Sức khỏe", icon: "fa-heart-pulse" },
                "elements_advice": { label: "Cải vận", icon: "fa-wand-magic-sparkles" }
            };

            let activeTabClass = 'active';
            let tabHeaders = '<div class="tab-headers">';
            let tabContents = '<div class="tab-contents">';

            Object.entries(categories).forEach(([key, val]) => {
                const contentText = interpretations[key];
                if (contentText && contentText.trim()) {
                    // Check if it's the broken form text dump from nguhanh.net header match
                    if (contentText.includes('010203040506070809') || contentText.includes('190019011902')) {
                        return; // Skip rendering this broken section
                    }
                    hasInterp = true;
                    tabHeaders += `<button class="tab-nav-btn ${activeTabClass}" onclick="switchTab(event, '${key}')"><i class="fa-solid ${val.icon}"></i> ${val.label}</button>`;
                    tabContents += `
                        <div class="tab-panel-content ${activeTabClass}" id="tab-panel-${key}">
                            <p class="interp-text-content">${contentText.replace(/\n/g, '<br>')}</p>
                        </div>
                    `;
                    activeTabClass = '';
                }
            });

            tabHeaders += '</div>';
            tabContents += '</div>';

            if (hasInterp) {
                interpTabsHtml = `
                    <h4 class="section-title" style="margin-top: 35px;"><i class="fa-solid fa-book-open"></i> Luận Giải Chi Tiết</h4>
                    <div class="interpretations-tabs-wrapper card-glass">
                        ${tabHeaders}
                        ${tabContents}
                    </div>
                `;
            }
        }

        html += interpTabsHtml;
        targetContainer.innerHTML = html;
        return;
    }

    // Database structure mapping (Fallback scrolls for older plain-text profiles):
    const can = profile.year_pillar && typeof profile.year_pillar === 'object' ? profile.year_pillar : {};
    const chi = profile.month_pillar && typeof profile.month_pillar === 'object' ? profile.month_pillar : {};

    const hour = { can: can.Hour || '', chi: chi.Hour || '' };
    const day = { can: can.Day || '', chi: chi.Day || '' };
    const month = { can: can.Month || '', chi: chi.Month || '' };
    const year = { can: can.Year || '', chi: chi.Year || '' };

    const hourCanInfo = getElementInfo(hour.can);
    const hourChiInfo = getElementInfo(hour.chi);
    const dayCanInfo = getElementInfo(day.can);
    const dayChiInfo = getElementInfo(day.chi);
    const monthCanInfo = getElementInfo(month.can);
    const monthChiInfo = getElementInfo(month.chi);
    const yearCanInfo = getElementInfo(year.can);
    const yearChiInfo = getElementInfo(year.chi);

    let html = `
        <div class="modal-title-section">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 class="modal-title">${profile.name}</h3>
                <span class="day-master-tag el-tho" style="margin-top:0; font-size: 0.8rem; border-color: var(--accent-gold); color: #fff; background: var(--accent-gold);"><i class="fa-solid fa-cloud-arrow-down"></i> Đã lưu Database</span>
            </div>
            <div class="modal-subtitle" style="margin-top: 10px;">
                <span><i class="fa-solid fa-venus-mars"></i> Giới tính: <strong>${profile.gender}</strong></span>
                <span><i class="fa-regular fa-calendar"></i> Sinh ngày: <strong>${profile.dob}</strong></span>
                <span><i class="fa-regular fa-clock"></i> Giờ sinh: <strong>${profile.hour}</strong></span>
            </div>
        </div>
    `;

    // Render Bazi Pillars Scrolls
    html += `
        <h4 class="section-title"><i class="fa-solid fa-scroll"></i> Bản Đồ Bát Tự (Tứ Trụ)</h4>
        <div class="pillars-container">
            <div class="pillar-scroll">
                <div class="pillar-label">Thời Trụ</div>
                <div class="pillar-val-box">
                    <div class="p-stem ${hourCanInfo.className}" title="Thiên Can: ${hourCanInfo.label}">${hour.can || '-'}</div>
                    <div class="p-branch ${hourChiInfo.className}" title="Địa Chi: ${hourChiInfo.label}">${hour.chi || '-'}</div>
                </div>
                <div class="pillar-indicator">Trụ Giờ</div>
            </div>

            <div class="pillar-scroll" style="box-shadow: 0 0 15px var(--accent-gold-glow); border-color: var(--accent-gold);">
                <div class="pillar-label" style="color: var(--accent-gold);">Nhật Trụ</div>
                <div class="pillar-val-box">
                    <div class="p-stem ${dayCanInfo.className}" title="Thiên Can (Nhật Chủ): ${dayCanInfo.label}" style="border: 2px solid var(--accent-gold);">${day.can || '-'}</div>
                    <div class="p-branch ${dayChiInfo.className}" title="Địa Chi: ${dayChiInfo.label}">${day.chi || '-'}</div>
                </div>
                <div class="pillar-indicator" style="color: var(--accent-gold); font-weight: 700;">Nhật Chủ (Mệnh)</div>
            </div>

            <div class="pillar-scroll">
                <div class="pillar-label">Nguyệt Trụ</div>
                <div class="pillar-val-box">
                    <div class="p-stem ${monthCanInfo.className}" title="Thiên Can: ${monthCanInfo.label}">${month.can || '-'}</div>
                    <div class="p-branch ${monthChiInfo.className}" title="Địa Chi: ${monthChiInfo.label}">${month.chi || '-'}</div>
                </div>
                <div class="pillar-indicator">Trụ Tháng</div>
            </div>

            <div class="pillar-scroll">
                <div class="pillar-label">Niên Trụ</div>
                <div class="pillar-val-box">
                    <div class="p-stem ${yearCanInfo.className}" title="Thiên Can: ${yearCanInfo.label}">${year.can || '-'}</div>
                    <div class="p-branch ${yearChiInfo.className}" title="Địa Chi: ${yearChiInfo.label}">${year.chi || '-'}</div>
                </div>
                <div class="pillar-indicator">Trụ Năm</div>
            </div>
        </div>
    `;

    // Render Elements Percentages
    let elementsHtml = '';
    const rawElementsText = profile.elements?.text || profile.elements?.raw_text || '';
    if (rawElementsText) {
        const parts = rawElementsText.split('|');
        if (parts.length >= 2) {
            elementsHtml += `<div class="elements-summary-grid">`;
            parts.forEach(part => {
                const subParts = part.split(':');
                if (subParts.length === 2) {
                    const elName = subParts[0].trim();
                    const elVal = subParts[1].trim();
                    const elInfo = getElementInfo(elName);
                    elementsHtml += `
                        <div class="el-bar-card">
                            <span class="el-name ${elInfo.className}-text" style="color: var(--element-${elInfo.className.replace('el-', '')})">${elName}</span>
                            <span class="el-percent">${elVal}</span>
                        </div>
                    `;
                }
            });
            elementsHtml += `</div>`;
        } else {
            elementsHtml = `<div class="card-glass" style="padding: 15px; margin-top: 15px; font-size: 0.9rem; color: var(--text-muted);">${rawElementsText}</div>`;
        }
    }

    if (elementsHtml) {
        html += `
            <h4 class="section-title" style="margin-top: 30px;"><i class="fa-solid fa-chart-simple"></i> Cân Bằng Ngũ Hành</h4>
            ${elementsHtml}
        `;
    }

    // Render Interpretations Tabs
    let hasInterp = false;
    let interpTabsHtml = '';
    
    if (interpretations && Object.keys(interpretations).length > 0) {
        const categories = {
            "personality": { label: "Tính cách", icon: "fa-user-astronaut" },
            "wealth": { label: "Tài lộc", icon: "fa-briefcase" },
            "relationship": { label: "Tình duyên", icon: "fa-heart" },
            "health": { label: "Sức khỏe", icon: "fa-heart-pulse" },
            "elements_advice": { label: "Cải vận", icon: "fa-wand-magic-sparkles" }
        };

        let activeTabClass = 'active';
        let tabHeaders = '<div class="tab-headers">';
        let tabContents = '<div class="tab-contents">';

        Object.entries(categories).forEach(([key, val]) => {
            const contentText = interpretations[key];
            if (contentText && contentText.trim()) {
                // Check if it's the broken form text dump from nguhanh.net header match
                if (contentText.includes('010203040506070809') || contentText.includes('190019011902')) {
                    return; // Skip rendering this broken section
                }
                hasInterp = true;
                tabHeaders += `<button class="tab-nav-btn ${activeTabClass}" onclick="switchTab(event, '${key}')"><i class="fa-solid ${val.icon}"></i> ${val.label}</button>`;
                tabContents += `
                    <div class="tab-panel-content ${activeTabClass}" id="tab-panel-${key}">
                        <p class="interp-text-content">${contentText.replace(/\n/g, '<br>')}</p>
                    </div>
                `;
                activeTabClass = '';
            }
        });

        tabHeaders += '</div>';
        tabContents += '</div>';

        if (hasInterp) {
            interpTabsHtml = `
                <h4 class="section-title" style="margin-top: 35px;"><i class="fa-solid fa-book-open"></i> Luận Giải Chi Tiết</h4>
                <div class="interpretations-tabs-wrapper card-glass">
                    ${tabHeaders}
                    ${tabContents}
                </div>
            `;
        }
    }

    html += interpTabsHtml;
    targetContainer.innerHTML = html;
}

// Render calculated result directly on calculator page
function renderCalculatorResult(data, targetContainer) {
    targetContainer.innerHTML = '';
    
    // Create layout container inside result area
    const resultWrapper = document.createElement('div');
    resultWrapper.className = 'calculator-visual-result';
    
    // Render
    renderProfileModalContent(data, resultWrapper);
    
    targetContainer.appendChild(resultWrapper);
}

// Tab Switching Utility Inside Modal / Calculator
window.switchTab = function(event, tabId) {
    const parent = event.currentTarget.closest('.interpretations-tabs-wrapper');
    
    parent.querySelectorAll('.tab-nav-btn').forEach(btn => btn.classList.remove('active'));
    parent.querySelectorAll('.tab-panel-content').forEach(panel => panel.classList.remove('active'));
    
    event.currentTarget.classList.add('active');
    parent.querySelector(`#tab-panel-${tabId}`).classList.add('active');
};

// Close modal
function closeModal() {
    const modal = document.getElementById('profile-modal');
    modal.classList.remove('active');
}
