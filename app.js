document.addEventListener('DOMContentLoaded', () => {
    const BASE_URL = window.location.origin;
    const minDaysTarget = 21; // THR completion threshold (21 days)
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('csv-file-input');

    const uploadSection = document.getElementById('upload-section');
    const loadingSection = document.getElementById('loading-section');
    const resultsSection = document.getElementById('results-section');

    const resetBtn = document.getElementById('reset-btn');

    // Main State
    let allLoadedData = []; // Store dataset globally in browser
    let currentIncompleteRows = []; // Store currently filtered rows for export
    let globalSectorName = "All Sectors";
    let activeReportType = "thr"; // "thr", "frs", "sam", "measuring", or "beneficiary"
    let activeBeneficiarySubTab = "mobile"; // "mobile", "aadhaar", or "abha"

    // Filter Elements (THR)
    const filterAwc = document.getElementById('filter-awc');
    const filterCategory = document.getElementById('filter-category');
    const filterStatus = document.getElementById('filter-status');
    const filterOptOut = document.getElementById('filter-optout');
    const filterThr = document.getElementById('filter-thr');
    const filterHcm = document.getElementById('filter-hcm');

    // Filter Elements (FRS)
    const filterFaceCaptured = document.getElementById('filter-face-captured');
    const filterEkycDone = document.getElementById('filter-ekyc-done');
    const filterAadhaarMatching = document.getElementById('filter-aadhaar-matching');

    // Filter Elements (Beneficiary)
    const filterSearch = document.getElementById('filter-search');
    const filterSector = document.getElementById('filter-sector');

    // Tab Elements
    const tabThr = document.querySelector('[data-tab="thr"]');
    const tabFrs = document.querySelector('[data-tab="frs"]');
    const tabBeneficiary = document.querySelector('[data-tab="beneficiary"]');
    const tabSam = document.querySelector('[data-tab="sam"]');
    const tabMeasuring = document.querySelector('[data-tab="measuring"]');
    const beneficiarySubTabsContainer = document.getElementById('beneficiary-sub-tabs');
    const beneficiarySubTabs = document.querySelectorAll('.sub-tab-btn');

    // Multi-Upload UI Elements
    const singleDropZone = document.getElementById('drop-zone');
    const multiUploadContainer = document.getElementById('multi-upload-container');

    // Tab Switching Logic
    function switchInfoCard(type) {
        const allInfoCards = document.querySelectorAll('.info-card');
        allInfoCards.forEach(c => c.classList.add('hidden'));
        const target = document.getElementById('info-' + type);
        if (target) target.classList.remove('hidden');
    }

    function switchTab(reportType) {
        if (activeReportType === reportType) return;
        activeReportType = reportType;
        switchInfoCard(reportType);

        // ── 1. Clear ALL tab active states in one sweep ─────────────────
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

        // ── 2. Reset shared UI ───────────────────────────────────────────
        resultsSection.classList.add('hidden');
        const sidebar = document.getElementById('app-sidebar');
        if (sidebar) sidebar.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        fileInput.value = '';
        allLoadedData = [];

        // Hide comparison panels by default (re-shown only for comparison tab)
        const _compUpload = document.getElementById('comparison-upload-container');
        const _compResults = document.getElementById('comparison-results');
        if (_compUpload) _compUpload.classList.add('hidden');
        if (_compResults) _compResults.classList.add('hidden');

        // Reset multi-files
        resetMultiFiles();

        // Hide all filter groups
        document.querySelectorAll('.thr-filter').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.frs-filter').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.beneficiary-filter').forEach(el => el.classList.add('hidden'));
        if (beneficiarySubTabsContainer) beneficiarySubTabsContainer.classList.add('hidden');

        // ── 3. Tab-specific setup ────────────────────────────────────────
        if (reportType === 'thr') {
            document.body.classList.remove('frs-theme');
            tabThr.classList.add('active');
            singleDropZone.classList.remove('hidden');
            multiUploadContainer.classList.add('hidden');
            document.querySelectorAll('.thr-filter').forEach(el => el.classList.remove('hidden'));
            document.querySelector('.title-area p').textContent = "Reviewing Incomplete THR Tasks";

        } else if (reportType === 'frs') {
            document.body.classList.add('frs-theme');
            tabFrs.classList.add('active');
            singleDropZone.classList.remove('hidden');
            multiUploadContainer.classList.add('hidden');
            document.querySelectorAll('.frs-filter').forEach(el => el.classList.remove('hidden'));
            document.querySelector('.title-area p').textContent = "Reviewing Facial Recognition System (FRS) Details";

        } else if (reportType === 'beneficiary') {
            document.body.classList.remove('frs-theme');
            if (tabBeneficiary) tabBeneficiary.classList.add('active');
            singleDropZone.classList.remove('hidden');
            multiUploadContainer.classList.add('hidden');
            if (beneficiarySubTabsContainer) beneficiarySubTabsContainer.classList.remove('hidden');
            document.querySelectorAll('.beneficiary-filter').forEach(el => el.classList.remove('hidden'));
            document.querySelector('.title-area p').textContent = "Reviewing Beneficiary Verification Status";
            updateBeneficiarySubTabsUI();

        } else if (reportType === 'sam') {
            document.body.classList.add('frs-theme');
            tabSam.classList.add('active');
            singleDropZone.classList.add('hidden');
            multiUploadContainer.classList.remove('hidden');
            document.querySelector('.title-area p').textContent = "Identifying Recurring Severe Children (3-Month Match)";

        } else if (reportType === 'measuring') {
            document.body.classList.remove('frs-theme');
            if (tabMeasuring) tabMeasuring.classList.add('active');
            singleDropZone.classList.remove('hidden');
            multiUploadContainer.classList.add('hidden');
            document.querySelector('.title-area p').textContent = "Measuring Efficiency Review (Filters Incomplete Records)";

        } else if (reportType === 'comparison') {
            document.body.classList.remove('frs-theme');
            const tabComparison = document.querySelector('[data-tab="comparison"]');
            if (tabComparison) tabComparison.classList.add('active');
            singleDropZone.classList.add('hidden');
            multiUploadContainer.classList.add('hidden');
            if (_compUpload) _compUpload.classList.remove('hidden');
            document.querySelector('.title-area p').textContent = "Compare Two Monthly Growth Monitoring Reports";
        }
    }

    tabThr.addEventListener('click', () => switchTab('thr'));
    tabFrs.addEventListener('click', () => switchTab('frs'));
    if (tabBeneficiary) tabBeneficiary.addEventListener('click', () => switchTab('beneficiary'));

    // Beneficiary Sub-Tab Switching
    beneficiarySubTabs.forEach(btn => {
        btn.addEventListener('click', () => {
            activeBeneficiarySubTab = btn.getAttribute('data-subtab');
            updateBeneficiarySubTabsUI();
            if (allLoadedData.length > 0) applyFilters();
        });
    });

    function updateBeneficiarySubTabsUI() {
        beneficiarySubTabs.forEach(btn => {
            const indicator = btn.querySelector('.active-indicator');
            if (btn.getAttribute('data-subtab') === activeBeneficiarySubTab) {
                btn.style.color = 'white';
                if (indicator) indicator.classList.remove('hidden');
            } else {
                btn.style.color = 'var(--text-muted)';
                if (indicator) indicator.classList.add('hidden');
            }
        });
    }

    tabSam.addEventListener('click', () => switchTab('sam'));
    if (tabMeasuring) tabMeasuring.addEventListener('click', () => switchTab('measuring'));

    // --- File Upload Handling (Single Files THR/FRS) ---
    singleDropZone.addEventListener('click', () => fileInput.click());

    singleDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        singleDropZone.classList.add('dragover');
    });

    singleDropZone.addEventListener('dragleave', () => {
        singleDropZone.classList.remove('dragover');
    });

    singleDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        singleDropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFile(e.target.files[0]);
        }
    });

    // --- Multi-File Upload Handling (SAM) ---
    const filesMulti = { m1: null, m2: null, m3: null };

    function resetMultiFiles() {
        filesMulti.m1 = null; filesMulti.m2 = null; filesMulti.m3 = null;
        ['1', '2', '3'].forEach(num => {
            const el = document.getElementById(`csv-m${num}`);
            if (el) el.value = '';
            const status = document.querySelector(`#drop-zone-m${num} .file-status`);
            if (status) status.textContent = '';
        });
    }

    ['1', '2', '3'].forEach(num => {
        const drop = document.getElementById(`drop-zone-m${num}`);
        const input = document.getElementById(`csv-m${num}`);
        const status = document.querySelector(`#drop-zone-m${num} .file-status`);

        drop.addEventListener('click', () => input.click());
        drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('dragover'); });
        drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));

        drop.addEventListener('drop', (e) => {
            e.preventDefault(); drop.classList.remove('dragover');
            if (e.dataTransfer.files.length) processMultiSelect(num, e.dataTransfer.files[0], status);
        });

        input.addEventListener('change', (e) => {
            if (e.target.files.length) processMultiSelect(num, e.target.files[0], status);
        });
    });

    function processMultiSelect(monthNum, file, statusEl) {
        if (file.type !== "text/csv" && !file.name.endsWith('.csv') && !file.name.endsWith('.xlsx')) {
            alert("Please upload a valid CSV or XLSX file.");
            return;
        }
        filesMulti[`m${monthNum}`] = file;
        statusEl.textContent = `✓ ${file.name}`;
    }

    document.getElementById('process-multi-btn').addEventListener('click', () => {
        if (!filesMulti.m1 || !filesMulti.m2 || !filesMulti.m3) {
            alert("Please select files for all 3 months before processing.");
            return;
        }

        uploadSection.classList.add('hidden');
        loadingSection.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file1', filesMulti.m1);
        formData.append('file2', filesMulti.m2);
        formData.append('file3', filesMulti.m3);

        fetch(BASE_URL + '/upload-multi', {
            method: 'POST',
            body: formData
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert("Error: " + data.error);
                    loadingSection.classList.add('hidden');
                    uploadSection.classList.remove('hidden');
                    return;
                }

                globalSectorName = data.sectorName || "Unknown Sector";
                currentIncompleteRows = data.intersectedData; // For SAM, intersected data IS what we render

                // Construct pseudo-stats for the dashboard UI
                const stdDash = document.getElementById('standard-dashboard');
                const samDash = document.getElementById('sam-dashboard');
                if (stdDash) stdDash.classList.add('hidden');
                if (samDash) samDash.classList.remove('hidden');

                if (data.stats) {
                    const calcPct = (sev, tot) => tot > 0 ? ` (${((sev / tot) * 100).toFixed(1)}%)` : '';

                    ['m1', 'm2', 'm3'].forEach(m => {
                        const s = data.stats[m];
                        document.getElementById(`stat-${m}-severe`).textContent = s.severe + calcPct(s.severe, s.total);
                        document.getElementById(`stat-${m}-total`).textContent = s.total + " Target Beneficiaries";

                        document.getElementById(`${m}-sam-only`).textContent = s.sam_only;
                        document.getElementById(`${m}-stunted-only`).textContent = s.stunted_only;
                        document.getElementById(`${m}-underweight-only`).textContent = s.underweight_only;
                        document.getElementById(`${m}-sam-stunted`).textContent = s.sam_stunted;
                        document.getElementById(`${m}-sam-underweight`).textContent = s.sam_underweight;
                        document.getElementById(`${m}-stunted-underweight`).textContent = s.stunted_underweight;
                        document.getElementById(`${m}-all-three`).textContent = s.all_three;
                    });

                    document.getElementById('stat-continuous-severe').textContent = data.stats.continuous;
                }

                const catStatsMap = {};
                currentIncompleteRows.forEach(r => {
                    if (!catStatsMap[r.category]) catStatsMap[r.category] = { total: 0, completed: 0 };
                    catStatsMap[r.category].total++;
                });

                // Hide sidebar since SAM does pure intersection, no sidebar filters
                const sidebar = document.getElementById('app-sidebar');
                if (sidebar) sidebar.classList.add('hidden');

                renderDashboard(0, 0, data.count, currentIncompleteRows, catStatsMap);
            })
            .catch(err => {
                alert("Failed to communicate with the server. Please ensure the Python backend is running.");
                loadingSection.classList.add('hidden');
                uploadSection.classList.remove('hidden');
                console.error(err);
            });
    });

    // --- Core File Logic Single ---
    function handleFile(file) {
        if (file.type !== "text/csv" && !file.name.endsWith('.csv') && !file.name.endsWith('.xlsx')) {
            alert("Please upload a valid CSV or XLSX file.");
            return;
        }

        uploadSection.classList.add('hidden');
        loadingSection.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);

        const endpoint = activeReportType === 'measuring' ? '/upload-measuring' : '/upload';

        fetch(BASE_URL + endpoint, {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error: " + data.error);
                    loadingSection.classList.add('hidden');
                    uploadSection.classList.remove('hidden');
                    return;
                }

                if (data.reportType) {
                    activeReportType = data.reportType;

                    // Reset all tabs
                    tabThr.classList.remove('active');
                    tabFrs.classList.remove('active');
                    if (tabSam) tabSam.classList.remove('active');
                    if (tabBeneficiary) tabBeneficiary.classList.remove('active');
                    if (tabMeasuring) tabMeasuring.classList.remove('active');

                    if (beneficiarySubTabsContainer) beneficiarySubTabsContainer.classList.add('hidden');
                    document.querySelectorAll('.thr-filter').forEach(el => el.classList.add('hidden'));
                    document.querySelectorAll('.frs-filter').forEach(el => el.classList.add('hidden'));
                    document.querySelectorAll('.beneficiary-filter').forEach(el => el.classList.add('hidden'));

                    if (activeReportType === 'thr') {
                        document.body.classList.remove('frs-theme');
                        tabThr.classList.add('active');
                        document.querySelectorAll('.thr-filter').forEach(el => el.classList.remove('hidden'));
                        document.querySelector('.title-area p').textContent = "Reviewing Incomplete THR Tasks";
                    } else if (activeReportType === 'frs') {
                        document.body.classList.add('frs-theme');
                        tabFrs.classList.add('active');
                        document.querySelectorAll('.frs-filter').forEach(el => el.classList.remove('hidden'));
                        document.querySelector('.title-area p').textContent = "Reviewing Facial Recognition System (FRS) Details";
                    } else if (activeReportType === 'beneficiary') {
                        document.body.classList.remove('frs-theme');
                        if (tabBeneficiary) tabBeneficiary.classList.add('active');
                        if (beneficiarySubTabsContainer) beneficiarySubTabsContainer.classList.remove('hidden');
                        document.querySelectorAll('.beneficiary-filter').forEach(el => el.classList.remove('hidden'));
                        document.querySelector('.title-area p').textContent = "Reviewing Beneficiary Verification Status";
                        updateBeneficiarySubTabsUI();
                    } else if (activeReportType === 'measuring') {
                        document.body.classList.remove('frs-theme');
                        if (tabMeasuring) tabMeasuring.classList.add('active');
                        document.querySelector('.title-area p').textContent = "Measuring Efficiency Review (Filters Incomplete Records)";
                        renderMeasuringDashboard(data);
                        return;
                    }
                }

                allLoadedData = data.allData;
                globalSectorName = data.sectorName || "Unknown Sector";
                populateFilterOptions(data.filters);
                applyFilters(); // Apply default filters and render dashboard

                // Show Sidebar
                const sidebar = document.getElementById('app-sidebar');
                if (sidebar) sidebar.classList.remove('hidden');
            })
            .catch(err => {
                alert("Failed to communicate with the server. Please ensure the Python backend is running.");
                loadingSection.classList.add('hidden');
                uploadSection.classList.remove('hidden');
                console.error(err);
            });
    }

    // --- Populate Dropdowns ---
    function populateFilterOptions(filters) {
        const buildOptions = (selectElem, optionsList, defaultVal, addAllOpt = false) => {
            selectElem.innerHTML = '';

            if (addAllOpt) {
                selectElem.innerHTML += `<option value="all">All</option>`;
            } else if (selectElem === filterThr || selectElem === filterHcm) {
                selectElem.innerHTML += `<option value="all">Any</option>`;
            }

            let hasDefaultInList = false;

            if (optionsList) {
                optionsList.forEach(opt => {
                    const isSelected = String(opt).toLowerCase() === defaultVal.toLowerCase() ? 'selected' : '';
                    if (isSelected) hasDefaultInList = true;
                    selectElem.innerHTML += `<option value="${opt}" ${isSelected}>${opt}</option>`;
                });
            }
        };

        const buildCheckboxes = (container, optionsList, defaultSelectedArr, mapPretty = null) => {
            container.innerHTML = '';
            container.innerHTML += `<label class="checkbox-item"><input type="checkbox" value="all" class="select-all-cb"> <strong>Select All</strong></label>`;

            if (optionsList) {
                optionsList.forEach(opt => {
                    const pretty = mapPretty ? (mapPretty[opt] || opt) : opt;
                    const isSel = defaultSelectedArr.includes(opt) || defaultSelectedArr.includes('all') ? 'checked' : '';
                    container.innerHTML += `<label class="checkbox-item"><input type="checkbox" value="${opt}" ${isSel} class="item-cb"> ${pretty}</label>`;
                });
            }

            const selectAllCb = container.querySelector('.select-all-cb');
            const itemCbs = container.querySelectorAll('.item-cb');

            const updateSelectAllState = () => {
                const allChecked = Array.from(itemCbs).every(cb => cb.checked);
                selectAllCb.checked = allChecked && itemCbs.length > 0;
            };
            updateSelectAllState();

            selectAllCb.addEventListener('change', (e) => {
                const isChecked = e.target.checked;
                itemCbs.forEach(cb => cb.checked = isChecked);
                applyFilters();
            });

            itemCbs.forEach(cb => {
                cb.addEventListener('change', () => {
                    updateSelectAllState();
                    applyFilters();
                });
            });
        };

        buildOptions(filterAwc, filters.awcNames, 'all', true);
        buildOptions(filterSector, filters.sectors || [], 'all', true);

        let defaultSelectedCats = [];
        if (activeReportType === 'thr') {
            defaultSelectedCats = ['pregnant_woman', 'lactating_mother', 'children_6m_3y'];
        } else {
            defaultSelectedCats = ['children_6m_3y', 'children_3y_6y', 'pregnant_woman', 'lactating_mother'];
        }

        const prettyNames = {
            'pregnant_woman': 'Pregnant Women',
            'lactating_mother': 'Lactating Mothers',
            'children_6m_3y': 'Children 6m-3y',
            'children_3y_6y': 'Children 3y-6y',
            'children_0m_6m': 'Children 0m-6m',
            'adolescent_girl': 'Adolescent Girl'
        };

        buildCheckboxes(filterCategory, filters.categories, defaultSelectedCats, prettyNames);

        if (activeReportType === 'thr') {
            buildOptions(filterStatus, filters.statuses, 'active');
            buildOptions(filterOptOut, filters.optOuts, 'no');
            buildOptions(filterThr, filters.thrDays, 'all');
            buildOptions(filterHcm, filters.hcmDays, 'all');
        } else if (activeReportType === 'frs') {
            buildCheckboxes(filterFaceCaptured, filters.faceCaptured, ['all']);
            buildCheckboxes(filterEkycDone, filters.ekycDone, ['all']);
            buildCheckboxes(filterAadhaarMatching, filters.aadhaarFaceMatching, ['all']);
        }

        const filterElements = [
            filterAwc, filterStatus, filterOptOut, filterThr, filterHcm,
            filterSector
        ];

        filterSearch.removeEventListener('input', applyFilters);
        filterSearch.addEventListener('input', applyFilters);

        filterElements.forEach(elem => {
            elem.removeEventListener('change', applyFilters);
            elem.addEventListener('change', applyFilters);
        });
    }

    // --- Apply Local JS Filters ---
    function applyFilters() {
        const selAwc = filterAwc.value;
        const selSector = filterSector.value;
        const searchText = filterSearch.value.trim().toLowerCase();
        const selCats = Array.from(filterCategory.querySelectorAll('input.item-cb:checked')).map(cb => cb.value);

        let filteredData = [];

        if (activeReportType === 'thr') {
            const selStatus = filterStatus.value.toLowerCase();
            const selOptOut = filterOptOut.value.toLowerCase();
            const selThr = filterThr.value;
            const selHcm = filterHcm.value;

            // 1. FILTERING
            filteredData = allLoadedData.filter(row => {
                if (selAwc !== 'all' && row.awcName !== selAwc) return false;
                if (selCats.length > 0 && !selCats.includes('all') && !selCats.includes(row.category)) return false;
                if (selStatus !== 'all' && row.status !== selStatus) return false;
                if (selOptOut !== 'all' && row.optout !== selOptOut) return false;
                if (selThr !== 'all' && row.thr !== parseInt(selThr)) return false;
                if (selHcm !== 'all' && row.hcm !== parseInt(selHcm)) return false;
                return true;
            });

            // 2. DASHBOARD MATH (Calculate based strictly on the filtered set)
            let totalTarget = filteredData.length;
            let givenCount = 0;
            let notGivenCount = 0;
            currentIncompleteRows = [];
            let catStatsMap = {};

            filteredData.forEach(row => {
                const isComplete = row.total >= minDaysTarget;
                if (isComplete) {
                    givenCount++;
                } else {
                    notGivenCount++;
                    currentIncompleteRows.push(row);
                }

                if (!catStatsMap[row.category]) {
                    catStatsMap[row.category] = { total: 0, completed: 0 };
                }
                catStatsMap[row.category].total++;
                if (isComplete) catStatsMap[row.category].completed++;
            });

            renderDashboard(totalTarget, givenCount, notGivenCount, currentIncompleteRows, catStatsMap);

        } else if (activeReportType === 'frs') {
            const selFace = Array.from(filterFaceCaptured.querySelectorAll('input.item-cb:checked')).map(cb => cb.value);
            const selEkyc = Array.from(filterEkycDone.querySelectorAll('input.item-cb:checked')).map(cb => cb.value);
            const selAadhaar = Array.from(filterAadhaarMatching.querySelectorAll('input.item-cb:checked')).map(cb => cb.value);

            // 1. FILTERING
            filteredData = allLoadedData.filter(row => {
                if (selAwc !== 'all' && row.awcName !== selAwc) return false;
                if (selCats.length > 0 && !selCats.includes('all') && !selCats.includes(row.category)) return false;

                if (selFace.length > 0 && !selFace.includes('all') && !selFace.includes(row.faceCaptured)) return false;
                if (selEkyc.length > 0 && !selEkyc.includes('all') && !selEkyc.includes(row.ekycDone)) return false;
                if (selAadhaar.length > 0 && !selAadhaar.includes('all') && !selAadhaar.includes(row.aadhaarFaceMatching)) return false;

                return true;
            });

            // 2. DASHBOARD MATH FOR FRS
            // FRS Completion Logic: Face, EKYC, and Aadhaar all MUST be "Yes"
            let totalTarget = filteredData.length;
            let givenCount = 0;
            let notGivenCount = 0;
            currentIncompleteRows = [];
            let catStatsMap = {};

            filteredData.forEach(row => {
                const isComplete = (row.faceCaptured.toLowerCase() === 'yes' &&
                    row.ekycDone.toLowerCase() === 'yes' &&
                    row.aadhaarFaceMatching.toLowerCase() === 'yes');

                if (isComplete) {
                    givenCount++;
                } else {
                    notGivenCount++;
                    currentIncompleteRows.push(row);
                }

                if (!catStatsMap[row.category]) {
                    catStatsMap[row.category] = { total: 0, completed: 0 };
                }
                catStatsMap[row.category].total++;
                if (isComplete) catStatsMap[row.category].completed++;
            });

            renderDashboard(totalTarget, givenCount, notGivenCount, currentIncompleteRows, catStatsMap);
        } else if (activeReportType === 'beneficiary') {
            filteredData = allLoadedData.filter(row => {
                if (selAwc !== 'all' && row.awcName !== selAwc) return false;
                if (selSector !== 'all' && row.sectorName !== selSector) return false;
                if (searchText && !row.name.toLowerCase().includes(searchText)) return false;
                return true;
            });

            let totalTarget = filteredData.length;
            let verifiedCount = 0;
            let unverifiedCount = 0;
            currentIncompleteRows = [];

            filteredData.forEach(row => {
                let isVerified = false;
                if (activeBeneficiarySubTab === 'mobile') {
                    isVerified = row.mobileStatus === 'verified';
                } else if (activeBeneficiarySubTab === 'aadhaar') {
                    isVerified = row.aadhaarStatus === 'verified_success';
                } else if (activeBeneficiarySubTab === 'abha') {
                    isVerified = row.abhaStatus !== 'not_verified'; // Covers anything except not_verified
                }

                if (isVerified) {
                    verifiedCount++;
                } else {
                    unverifiedCount++;
                    currentIncompleteRows.push(row);
                }
            });

            renderDashboard(totalTarget, verifiedCount, unverifiedCount, currentIncompleteRows, null);
        }
    }

    // --- Display Dashboard Function ---
    function renderDashboard(totalTarget, givenCount, notGivenCount, incompleteRowsToRender, catStatsMap) {
        loadingSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        const stdDash = document.getElementById('standard-dashboard');
        const samDash = document.getElementById('sam-dashboard');
        const benDash = document.getElementById('beneficiary-dashboard');
        const catBreakdown = document.querySelector('.category-breakdown');

        if (activeReportType === 'sam') {
            if (stdDash) stdDash.classList.add('hidden');
            if (samDash) samDash.classList.remove('hidden');
            if (benDash) benDash.classList.add('hidden');
            if (catBreakdown) catBreakdown.classList.add('hidden');
        } else if (activeReportType === 'beneficiary') {
            if (stdDash) stdDash.classList.add('hidden');
            if (samDash) samDash.classList.add('hidden');
            if (benDash) benDash.classList.remove('hidden');
            if (catBreakdown) catBreakdown.classList.add('hidden');

            document.getElementById('stat-ben-total').textContent = totalTarget;
            document.getElementById('stat-ben-verified').textContent = givenCount;
            document.getElementById('stat-ben-unverified').textContent = notGivenCount;

            // Adjust Titles based on sub-tab
            const vTitle = document.getElementById('stat-ben-verified-title');
            const uvTitle = document.getElementById('stat-ben-unverified-title');
            if (activeBeneficiarySubTab === 'mobile') {
                vTitle.textContent = "Mobile Verified";
                uvTitle.textContent = "Mobile Not Verified";
            } else if (activeBeneficiarySubTab === 'aadhaar') {
                vTitle.textContent = "Aadhaar Verified";
                uvTitle.textContent = "Aadhaar Not Verified";
            } else if (activeBeneficiarySubTab === 'abha') {
                vTitle.textContent = "ABHA ID Verified";
                uvTitle.textContent = "ABHA ID Not Verified";
            }

            let percent = totalTarget === 0 ? 0 : Math.round((givenCount / totalTarget) * 100);
            document.getElementById('stat-ben-percent').textContent = `${percent}%`;

        } else {
            if (stdDash) stdDash.classList.remove('hidden');
            if (samDash) samDash.classList.add('hidden');
            if (benDash) benDash.classList.add('hidden');
            if (catBreakdown) catBreakdown.classList.remove('hidden');

            // Update Overall Stats for Standard View
            document.getElementById('stat-total').textContent = totalTarget;
            document.getElementById('stat-given').textContent = givenCount;
            document.getElementById('stat-not-given').textContent = notGivenCount;

            let percent = "0";
            if (totalTarget > 0) {
                percent = Math.round((givenCount / totalTarget) * 100);
            }
            document.getElementById('stat-percent').textContent = `${percent}%`;
        }

        // Render Category Breakdown
        const catContainer = document.getElementById('category-stats-container');
        catContainer.innerHTML = '';

        const catDisplayNames = {
            'pregnant_woman': 'Pregnant Women',
            'lactating_mother': 'Lactating Mothers',
            'children_6m_3y': 'Children 6m-3y',
            'children_3y_6y': 'Children 3y-6y'
        };

        const sortedCatKeys = Object.keys(catStatsMap).sort();
        sortedCatKeys.forEach(catKey => {
            if (!catKey || catKey.trim() === '') return;
            const stats = catStatsMap[catKey];
            const name = catDisplayNames[catKey] || catKey.replace(/_/g, ' ');
            let catPercent = 0;
            if (stats.total > 0) {
                catPercent = Math.round((stats.completed / stats.total) * 100);
            }

            const div = document.createElement('div');
            div.className = 'cat-stat-card';
            div.innerHTML = `
                <h4>${name}</h4>
                <div class="progress-container">
                    <span>${stats.completed} / ${stats.total} Completed</span>
                    <strong>${catPercent}%</strong>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: ${catPercent}%"></div>
                </div>
            `;
            catContainer.appendChild(div);
        });

        // Update Table Headers
        const thead = document.getElementById('table-head');
        if (activeReportType === 'thr') {
            thead.innerHTML = `
                <th>AWC CODE</th>
                <th>AWC NAME</th>
                <th>BENEFICIARY NAME</th>
                <th>CATEGORY</th>
                <th>THR DAYS</th>
                <th>HCM DAYS</th>
                <th>TOTAL</th>
            `;
        } else if (activeReportType === 'frs') {
            thead.innerHTML = `
                <th>AWC CODE</th>
                <th>AWC NAME</th>
                <th>BENEFICIARY NAME</th>
                <th>CATEGORY</th>
                <th>FACE CAPTURED</th>
                <th>EKYC DONE</th>
                <th>AADHAAR MATCH</th>
            `;
        } else if (activeReportType === 'sam') {
            thead.innerHTML = `
                <th>SECTOR NAME</th>
                <th>AWC NAME</th>
                <th>AWC CODE</th>
                <th>BENEFICIARY NAME</th>
                <th>MOTHER NAME</th>
                <th>DOB</th>
                <th>GENDER</th>
                <th>M1 STATUS</th>
                <th>M2 STATUS</th>
                <th>M3 STATUS</th>
                <th>SEVERE CATEGORY</th>
            `;
        } else if (activeReportType === 'beneficiary') {
            if (activeBeneficiarySubTab === 'mobile') {
                thead.innerHTML = `
                    <th>S.NO</th>
                    <th>AWC NAME</th>
                    <th>AWC CODE</th>
                    <th>BENEFICIARY NAME</th>
                    <th>CATEGORY</th>
                    <th>MOBILE NUMBER</th>
                    <th>MOBILE STATUS</th>
                `;
            } else if (activeBeneficiarySubTab === 'aadhaar') {
                thead.innerHTML = `
                    <th>S.NO</th>
                    <th>AWC NAME</th>
                    <th>AWC CODE</th>
                    <th>BENEFICIARY NAME</th>
                    <th>CATEGORY</th>
                    <th>AADHAAR NUMBER</th>
                    <th>AADHAAR STATUS</th>
                `;
            } else if (activeBeneficiarySubTab === 'abha') {
                thead.innerHTML = `
                    <th>S.NO</th>
                    <th>AWC NAME</th>
                    <th>AWC CODE</th>
                    <th>BENEFICIARY NAME</th>
                    <th>CATEGORY</th>
                    <th>ABHA STATUS</th>
                `;
            }
        }

        // Render Table (Showing incomplete rows corresponding to the filters applied)
        const tbody = document.getElementById('table-body');
        tbody.innerHTML = '';

        if (incompleteRowsToRender.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;">No targets matching your criteria. 🎉</td></tr>';
            return;
        }

        incompleteRowsToRender.forEach(row => {
            const tr = document.createElement('tr');

            // Prettify the Output
            let prettyCat = row.category;
            if (prettyCat === 'pregnant_woman') prettyCat = 'Pregnant Woman';
            else if (prettyCat === 'lactating_mother') prettyCat = 'Lactating Mother';
            else if (prettyCat === 'children_6m_3y') prettyCat = 'Child 6m-3y';
            else if (prettyCat === 'children_3y_6y') prettyCat = 'Child 3y-6y';

            if (activeReportType === 'thr') {
                tr.innerHTML = `
                    <td><strong>${row.awcCode}</strong></td>
                    <td>${row.awcName}</td>
                    <td><strong>${row.name}</strong></td>
                    <td><span style="opacity: 0.8; font-size: 0.9em;">${prettyCat}</span></td>
                    <td style="color: var(--error);">${row.thr}</td>
                    <td style="color: var(--error);">${row.hcm}</td>
                    <td><strong style="color: var(--error);">${row.total}</strong></td>
                `;
            } else if (activeReportType === 'frs') {
                tr.innerHTML = `
                    <td><strong>${row.awcCode}</strong></td>
                    <td>${row.awcName}</td>
                    <td><strong>${row.name}</strong></td>
                    <td><span style="opacity: 0.8; font-size: 0.9em;">${prettyCat}</span></td>
                    <td style="color: ${row.faceCaptured.toLowerCase() === 'yes' ? 'var(--success)' : 'var(--error)'};">${row.faceCaptured}</td>
                    <td style="color: ${row.ekycDone.toLowerCase() === 'yes' ? 'var(--success)' : 'var(--error)'};">${row.ekycDone}</td>
                    <td style="color: ${row.aadhaarFaceMatching.toLowerCase() === 'yes' ? 'var(--success)' : 'var(--error)'};">${row.aadhaarFaceMatching}</td>
                `;
            } else if (activeReportType === 'sam') {
                tr.innerHTML = `
                    <td style="font-size:0.8rem">${row.sectorName}</td>
                    <td style="font-size:0.8rem">${row.awcName}</td>
                    <td><strong>${row.awcCode}</strong></td>
                    <td><strong style="color:var(--blob-3);">${row.name}</strong></td>
                    <td>${row.motherName}</td>
                    <td>${row.dob}</td>
                    <td>${row.gender}</td>
                    <td style="color:var(--error); font-size:0.8rem; font-weight:600">${row.m1Status}</td>
                    <td style="color:var(--error); font-size:0.8rem; font-weight:600">${row.m2Status}</td>
                    <td style="color:var(--error); font-size:0.8rem; font-weight:600">${row.m3Status}</td>
                    <td><span style="background: rgba(239, 68, 68, 0.2); color: var(--error); padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 700;">${row.severeCategory}</span></td>
                `;
            } else if (activeReportType === 'beneficiary') {
                let slNoElement = `<td>${tbody.children.length + 1}</td>`;
                let prettyCatSpan = `<span style="opacity: 0.8; font-size: 0.9em;">${prettyCat}</span>`;
                if (activeBeneficiarySubTab === 'mobile') {
                    tr.innerHTML = `
                        ${slNoElement}
                        <td>${row.awcName}</td>
                        <td><strong>${row.awcCode}</strong></td>
                        <td><strong>${row.name}</strong></td>
                        <td>${prettyCatSpan}</td>
                        <td>${row.mobileNumber}</td>
                        <td><span class="status-badge inactive">${row.mobileStatus}</span></td>
                    `;
                } else if (activeBeneficiarySubTab === 'aadhaar') {
                    tr.innerHTML = `
                        ${slNoElement}
                        <td>${row.awcName}</td>
                        <td><strong>${row.awcCode}</strong></td>
                        <td><strong>${row.name}</strong></td>
                        <td>${prettyCatSpan}</td>
                        <td>${row.aadhaarNumber}</td>
                        <td><span class="status-badge inactive">${row.aadhaarStatus}</span></td>
                    `;
                } else if (activeBeneficiarySubTab === 'abha') {
                    tr.innerHTML = `
                        ${slNoElement}
                        <td>${row.awcName}</td>
                        <td><strong>${row.awcCode}</strong></td>
                        <td><strong>${row.name}</strong></td>
                        <td>${prettyCatSpan}</td>
                        <td><span class="status-badge inactive">${row.abhaStatus}</span></td>
                    `;
                }
            }
            tbody.appendChild(tr);
        });

        // --- Render Top 10 AWC List ---
        const topAwcContainer = document.getElementById('top-awc-container');
        const topAwcHeading = document.getElementById('top-awc-heading');
        const topAwcList = document.getElementById('top-awc-list');

        if (incompleteRowsToRender.length > 0) {
            topAwcContainer.classList.remove('hidden');
            let headingText = 'Top 10 AWC with Pending THR/HCM';
            if (activeReportType === 'frs') headingText = 'Top 10 AWC with Pending FRS Data';
            if (activeReportType === 'sam') headingText = 'Top 10 AWC with Recurring SAM Children';
            if (activeReportType === 'beneficiary') headingText = 'Top 10 AWC with Unverified Beneficiaries';
            topAwcHeading.textContent = headingText;

            // Group by AWC code/name
            const awcMap = {};
            incompleteRowsToRender.forEach(row => {
                const key = row.awcCode + '|' + row.awcName;
                if (!awcMap[key]) awcMap[key] = { code: row.awcCode, name: row.awcName, count: 0 };
                awcMap[key].count++;
            });

            // Sort and grab top 10
            const sortedAwc = Object.values(awcMap).sort((a, b) => b.count - a.count).slice(0, 10);

            topAwcList.innerHTML = '';
            sortedAwc.forEach((awc, index) => {
                const li = document.createElement('li');
                li.className = 'top-awc-item';
                li.innerHTML = `
                    <div class="top-awc-rank">#${index + 1}</div>
                    <div class="top-awc-info">
                        <h4>${awc.name}</h4>
                        <p>Code: ${awc.code}</p>
                    </div>
                    <div class="top-awc-count">${awc.count}</div>
                `;
                topAwcList.appendChild(li);
            });
        } else {
            topAwcContainer.classList.add('hidden');
        }
    }

    // --- Display Measuring Dashboard ---
    function renderMeasuringDashboard(data) {
        loadingSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        const stdDash = document.getElementById('standard-dashboard');
        const samDash = document.getElementById('sam-dashboard');
        const benDash = document.getElementById('beneficiary-dashboard');
        const catBreakdown = document.querySelector('.category-breakdown');

        if (stdDash) stdDash.classList.remove('hidden');
        if (samDash) samDash.classList.add('hidden');
        if (benDash) benDash.classList.add('hidden');
        if (catBreakdown) catBreakdown.classList.add('hidden');

        let totalChildren = 0;
        let totalMeasured = 0;
        let totalRemaining = 0;

        if (data.globalStats) {
            totalChildren = data.globalStats.totalChildren;
            totalMeasured = data.globalStats.totalMeasured;
            totalRemaining = data.globalStats.totalRemaining;
        } else {
            // Fallback for unexpected missing data
            data.tableData.forEach(r => {
                totalChildren += r.totalChildCount;
                totalMeasured += r.weightTakenCount;
                totalRemaining += r.needToTakeWeight;
            });
        }

        document.getElementById('stat-total').textContent = totalChildren;
        document.getElementById('stat-given').textContent = totalMeasured;
        document.getElementById('stat-not-given').textContent = totalRemaining;

        let percent = totalChildren > 0 ? Math.round((totalMeasured / totalChildren) * 100) : 0;
        document.getElementById('stat-percent').textContent = `${percent}%`;

        const tableHead = document.getElementById('table-head');
        const tableBody = document.getElementById('table-body');

        tableHead.innerHTML = `
            <th>S.No</th>
            <th>AWC Name</th>
            <th>Total Child Count</th>
            <th>Weight Taken Count</th>
            <th>Need to Take Weight</th>
            <th>Completion %</th>
        `;

        tableBody.innerHTML = '';

        if (data.tableData.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">All AWC completed 100% measuring!</td></tr>';
        } else {
            data.tableData.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.sNo}</td>
                    <td>${row.awcName}</td>
                    <td style="text-align:center;">${row.totalChildCount}</td>
                    <td style="text-align:center;">${row.weightTakenCount}</td>
                    <td style="text-align:center; color: var(--error); font-weight: bold;">${row.needToTakeWeight}</td>
                    <td style="text-align:center;">
                        <span class="status-badge ${row.completionPercent >= 80 ? 'active' : 'inactive'}">
                            ${row.completionPercent}%
                        </span>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        }

        const topAwcContainer = document.getElementById('top-awc-container');
        if (topAwcContainer) topAwcContainer.classList.add('hidden');

        if (data.metadata) {
            document.getElementById('pdf-district-name').textContent = data.metadata.district;
            document.getElementById('pdf-project-name').textContent = data.metadata.project;
            document.getElementById('pdf-sector-name').textContent = data.metadata.sector;
            document.getElementById('pdf-report-date').textContent = data.metadata.date;
        }

        currentIncompleteRows = data.tableData;
    }

    // --- Helper function: Export to PDF ---
    document.getElementById('download-btn').addEventListener('click', () => {
        exportToPDF(`poshan_report_${globalSectorName.replace(/\\s+/g, '_')}.pdf`, currentIncompleteRows);
    });

    function exportToPDF(filename, rows) {
        if (!rows || !rows.length) {
            alert('No data to export!');
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('landscape'); // Landscape is better for 7 columns

        const currentAwc = document.getElementById('filter-awc') ? document.getElementById('filter-awc').value : 'all';
        let subtitleText = currentAwc === 'all' ? `Sector: ${globalSectorName}` : `Sector: ${globalSectorName} | AWC: ${currentAwc}`;

        if (activeReportType === 'measuring') {
            const projName = document.getElementById('pdf-project-name') ? document.getElementById('pdf-project-name').textContent.trim() : '';
            const sectName = document.getElementById('pdf-sector-name') ? document.getElementById('pdf-sector-name').textContent.trim() : '';
            let subtitleParts = [];
            if (projName && projName !== 'Unknown') subtitleParts.push(`Project: ${projName}`);
            if (sectName && sectName !== 'Unknown') subtitleParts.push(`Sector: ${sectName}`);
            subtitleText = subtitleParts.length > 0 ? subtitleParts.join('  |  ') : '';
        }

        // Add Header Texts
        doc.setFontSize(18);
        doc.setTextColor(40, 40, 40);
        let titleText = 'THR/HCM Pending Details';
        if (activeReportType === 'frs') titleText = 'FRS Pending Details';
        if (activeReportType === 'sam') titleText = 'SAM/MAM 3-Month Intersect Record';
        if (activeReportType === 'measuring') titleText = 'Measuring Efficiency Report';
        if (activeReportType === 'beneficiary') {
            if (activeBeneficiarySubTab === 'mobile') titleText = 'Beneficiary Mobile Unverified Report';
            if (activeBeneficiarySubTab === 'aadhaar') titleText = 'Beneficiary Aadhaar Unverified Report';
            if (activeBeneficiarySubTab === 'abha') titleText = 'Beneficiary ABHA ID Unverified Report';
        }
        doc.text(titleText, 14, 22);

        doc.setFontSize(11);
        doc.setTextColor(100, 100, 100);
        doc.text(subtitleText, 14, 30);

        // Prepare Table Data
        let headers = [['AWC CODE', 'AWC NAME', 'BENEFICIARY NAME', 'CATEGORY', 'THR DAYS', 'HCM DAYS', 'TOTAL']];
        if (activeReportType === 'frs') {
            headers = [['AWC CODE', 'AWC NAME', 'BENEFICIARY NAME', 'CATEGORY', 'FACE CAPTURED', 'EKYC DONE', 'AADHAAR MATCH']];
        } else if (activeReportType === 'sam') {
            headers = [['SECTOR NAME', 'AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'MOTHER NAME', 'DOB', 'GENDER', 'M1 STATUS', 'M2 STATUS', 'M3 STATUS', 'SEVERE CATEGORY']];
        } else if (activeReportType === 'measuring') {
            headers = [['S.No', 'AWC NAME', 'TOTAL ACTIVE', 'MEASURED', 'PENDING', 'COMPLETION %']];
        } else if (activeReportType === 'beneficiary') {
            if (activeBeneficiarySubTab === 'mobile') headers = [['S.NO', 'AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'CATEGORY', 'MOBILE NUMBER', 'MOBILE STATUS']];
            if (activeBeneficiarySubTab === 'aadhaar') headers = [['S.NO', 'AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'CATEGORY', 'AADHAAR NUMBER', 'AADHAAR STATUS']];
            if (activeBeneficiarySubTab === 'abha') headers = [['S.NO', 'AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'CATEGORY', 'ABHA STATUS']];
        }

        const data = rows.map(r => {
            if (activeReportType === 'measuring') {
                return [
                    r.sNo.toString(),
                    r.awcName,
                    r.totalChildCount.toString(),
                    r.weightTakenCount.toString(),
                    r.needToTakeWeight.toString(),
                    r.completionPercent.toString() + '%'
                ];
            }

            let prettyCat = r.category;
            if (prettyCat === 'pregnant_woman') prettyCat = 'Pregnant Woman';
            else if (prettyCat === 'lactating_mother') prettyCat = 'Lactating Mother';
            else if (prettyCat === 'children_6m_3y') prettyCat = 'Child 6m-3y';
            else if (prettyCat === 'children_3y_6y') prettyCat = 'Child 3y-6y';

            if (activeReportType === 'thr') {
                return [
                    r.awcCode,
                    r.awcName,
                    r.name,
                    prettyCat,
                    r.thr.toString(),
                    r.hcm.toString(),
                    r.total.toString()
                ];
            } else if (activeReportType === 'frs') {
                return [
                    r.awcCode,
                    r.awcName,
                    r.name,
                    prettyCat,
                    r.faceCaptured,
                    r.ekycDone,
                    r.aadhaarFaceMatching
                ];
            } else if (activeReportType === 'sam') {
                return [
                    r.sectorName,
                    r.awcName,
                    r.awcCode,
                    r.name,
                    r.motherName,
                    r.dob,
                    r.gender,
                    r.m1Status,
                    r.m2Status,
                    r.m3Status,
                    r.severeCategory
                ];
            } else if (activeReportType === 'beneficiary') {
                const slNo = (rows.indexOf(r) + 1).toString();
                if (activeBeneficiarySubTab === 'mobile') {
                    return [slNo, r.awcName, r.awcCode, r.name, prettyCat, r.mobileNumber, r.mobileStatus];
                } else if (activeBeneficiarySubTab === 'aadhaar') {
                    return [slNo, r.awcName, r.awcCode, r.name, prettyCat, r.aadhaarNumber, r.aadhaarStatus];
                } else if (activeBeneficiarySubTab === 'abha') {
                    return [slNo, r.awcName, r.awcCode, r.name, prettyCat, r.abhaStatus];
                }
            }
        });

        // Generate Table
        let colStyles = {};
        if (activeReportType === 'measuring') {
            colStyles = {
                0: { cellWidth: 15, halign: 'center' },
                1: { cellWidth: 60 },
                2: { halign: 'center' },
                3: { halign: 'center' },
                4: { halign: 'center', textColor: [220, 38, 38] },
                5: { halign: 'center', fontStyle: 'bold' }
            };
        } else if (activeReportType === 'beneficiary') {
            if (activeBeneficiarySubTab === 'mobile' || activeBeneficiarySubTab === 'aadhaar') {
                colStyles = {
                    0: { cellWidth: 15, halign: 'center' },
                    1: { cellWidth: 40 },
                    2: { cellWidth: 30 },
                    3: { cellWidth: 45 },
                    4: { cellWidth: 35 },
                    5: { halign: 'center' },
                    6: { halign: 'center', textColor: [220, 38, 38] }
                };
            } else if (activeBeneficiarySubTab === 'abha') {
                colStyles = {
                    0: { cellWidth: 15, halign: 'center' },
                    1: { cellWidth: 45 },
                    2: { cellWidth: 35 },
                    3: { cellWidth: 55 },
                    4: { cellWidth: 40 },
                    5: { halign: 'center', textColor: [220, 38, 38] }
                };
            }
        } else if (activeReportType !== 'sam') {
            colStyles = {
                0: { cellWidth: 25 },
                1: { cellWidth: 40 },
                2: { cellWidth: 50 },
                3: { cellWidth: 35 },
                4: { halign: 'center' },
                5: { halign: 'center' },
                6: { halign: 'center', fontStyle: activeReportType === 'thr' ? 'bold' : 'normal' }
            };
        }

        doc.autoTable({
            head: headers,
            body: data,
            startY: 40,
            theme: 'grid',
            headStyles: { fillColor: [15, 23, 42], textColor: 255 },
            styles: {
                fontSize: activeReportType === 'sam' ? 6 : (activeReportType === 'beneficiary' ? 11 : 9),
                cellPadding: activeReportType === 'beneficiary' ? 3 : 2
            },
            columnStyles: colStyles
        });

        doc.save(filename);
    }

    // --- Reset ---
    resetBtn.addEventListener('click', () => {
        resultsSection.classList.add('hidden');
        const sidebar = document.getElementById('app-sidebar');
        if (sidebar) sidebar.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        fileInput.value = ''; // clear input
        allLoadedData = [];
        // Also hide comparison section if visible
        document.getElementById('comparison-results').classList.add('hidden');
        document.getElementById('comparison-upload-container').classList.add('hidden');
        // Restore normal single drop zone when resetting from comparison tab
        if (activeReportType === 'comparison') {
            document.getElementById('drop-zone').classList.remove('hidden');
        }
    });

    // ============================================================
    // COMPARISON REPORT - New Feature (added without modifying above)
    // ============================================================
    const tabComparison = document.querySelector('[data-tab="comparison"]');
    const compUploadContainer = document.getElementById('comparison-upload-container');
    const compResults = document.getElementById('comparison-results');
    const compOldInput = document.getElementById('csv-comp-old');
    const compNewInput = document.getElementById('csv-comp-new');
    const compOldZone = document.getElementById('drop-zone-comp-old');
    const compNewZone = document.getElementById('drop-zone-comp-new');
    const compOldStatus = document.getElementById('comp-old-status');
    const compNewStatus = document.getElementById('comp-new-status');
    const processCompBtn = document.getElementById('process-comp-btn');
    const compDownloadBtn = document.getElementById('comp-download-btn');

    let compOldFile = null;
    let compNewFile = null;
    let compTableData = [];

    if (tabComparison) {
        tabComparison.addEventListener('click', () => switchTab('comparison'));
    }

    // File selection helpers
    function setupCompZone(zone, input, statusEl, slot) {
        zone.addEventListener('click', () => input.click());
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', e => {
            e.preventDefault(); zone.classList.remove('dragover');
            const f = e.dataTransfer.files[0];
            if (f) assignCompFile(f, statusEl, slot);
        });
        input.addEventListener('change', e => {
            if (e.target.files[0]) assignCompFile(e.target.files[0], statusEl, slot);
        });
    }

    function assignCompFile(file, statusEl, slot) {
        if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.csv')) {
            alert('Please upload a valid .xlsx or .csv file.');
            return;
        }
        if (slot === 'old') compOldFile = file;
        else compNewFile = file;
        statusEl.textContent = '✓ ' + file.name;
        statusEl.style.color = '#10b981';
    }

    if (compOldZone) setupCompZone(compOldZone, compOldInput, compOldStatus, 'old');
    if (compNewZone) setupCompZone(compNewZone, compNewInput, compNewStatus, 'new');

    // Run comparison
    if (processCompBtn) {
        processCompBtn.addEventListener('click', () => {
            if (!compOldFile || !compNewFile) {
                alert('Please select both Old Month and New Month Excel files before running.');
                return;
            }

            uploadSection.classList.add('hidden');
            loadingSection.classList.remove('hidden');

            const fd = new FormData();
            fd.append('file_old', compOldFile);
            fd.append('file_new', compNewFile);

            fetch(BASE_URL + '/upload-comparison', { method: 'POST', body: fd })
                .then(r => r.json())
                .then(data => {
                    loadingSection.classList.add('hidden');
                    if (data.error) {
                        alert('Error: ' + data.error);
                        uploadSection.classList.remove('hidden');
                        return;
                    }

                    // Show stats
                    document.getElementById('stat-comp-old').textContent = data.stats.totalOld;
                    document.getElementById('stat-comp-new').textContent = data.stats.totalNew;
                    document.getElementById('stat-comp-matched').textContent = data.stats.matched;
                    document.getElementById('stat-comp-updated').textContent = data.stats.updated;

                    // Render table
                    compTableData = data.tableData || [];
                    renderCompTable(compTableData);

                    // Show comparison results (its own isolated section, NOT results-section)
                    compResults.classList.remove('hidden');
                    // Also show upload section again so user can upload another pair if needed
                    compUploadContainer.classList.remove('hidden');
                    uploadSection.classList.remove('hidden');
                })
                .catch(err => {
                    loadingSection.classList.add('hidden');
                    uploadSection.classList.remove('hidden');
                    alert('Failed to communicate with the server. Please ensure the Python backend is running.');
                    console.error(err);
                });
        });
    }

    function renderCompTable(rows) {
        const tbody = document.getElementById('comparison-table-body');
        if (!tbody) return;

        if (!rows || !rows.length) {
            tbody.innerHTML = '<tr><td colspan="13" style="text-align:center; padding: 2rem; color: var(--text-muted);">No matching children found between the two files.</td></tr>';
            return;
        }

        // Show row count badge
        const heading = document.querySelector('#comparison-results h3');
        if (heading) heading.textContent = `📊 Comparison Report — ${rows.length} Matched Children`;

        // Cap at 500 rows to prevent browser freeze on huge files
        const MAX_ROWS = 500;
        const displayRows = rows.slice(0, MAX_ROWS);

        // Build full HTML as ONE string, then set innerHTML once (no += per row)
        const parts = [];
        displayRows.forEach((row, i) => {
            const catColor = !row.nutritionCategory || row.nutritionCategory === 'Normal' ? '#10b981'
                : row.nutritionCategory.includes('Severe') || row.nutritionCategory.includes('SAM') ? '#ef4444'
                    : '#f59e0b';
            parts.push(`<tr>
                <td>${i + 1}</td>
                <td>${row.awcName || ''}</td>
                <td>${row.awcCode || ''}</td>
                <td><strong>${row.name || ''}</strong></td>
                <td>${row.motherName || ''}</td>
                <td>${row.dob || ''}</td>
                <td>${row.oldWeight || '-'}</td>
                <td>${row.oldHeight || '-'}</td>
                <td><strong>${row.newWeight || '-'}</strong></td>
                <td><strong>${row.newHeight || '-'}</strong></td>
                <td><span style="color:${catColor}; font-weight:600;">${row.nutritionCategory || '-'}</span></td>
            </tr>`);
        });

        if (rows.length > MAX_ROWS) {
            parts.push(`<tr><td colspan="11" style="text-align:center; padding: 1rem; color: #f59e0b; font-weight:600;">
                Showing first ${MAX_ROWS} of ${rows.length} matched records. Download PDF to see all.
            </td></tr>`);
        }

        tbody.innerHTML = parts.join('');
    }

    // Download PDF for comparison
    if (compDownloadBtn) {
        compDownloadBtn.addEventListener('click', () => {
            if (!compTableData.length) { alert('No data to download.'); return; }
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
            doc.setFontSize(14);
            doc.text('Growth Monitoring Comparison Report', 148, 15, { align: 'center' });
            doc.setFontSize(10);
            doc.text(`Old Month vs New Month  |  Matched Children: ${compTableData.length}`, 148, 22, { align: 'center' });

            const headers = [['#', 'Sector', 'AWC Name', 'AWC Code', 'Child Name', 'Mother Name', 'DOB', 'Gender', 'Old Wt', 'Old Ht', 'New Wt', 'New Ht', 'Category']];
            const body = compTableData.map((r, i) => [
                i + 1, r.sectorName, r.awcName, r.awcCode, r.name, r.motherName, r.dob, r.gender,
                r.oldWeight || '-', r.oldHeight || '-', r.newWeight || '-', r.newHeight || '-', r.nutritionCategory
            ]);

            doc.autoTable({
                startY: 28,
                head: headers,
                body: body,
                styles: { fontSize: 7, cellPadding: 2 },
                headStyles: { fillColor: [99, 102, 241], textColor: 255, fontStyle: 'bold' },
                alternateRowStyles: { fillColor: [245, 245, 255] },
                margin: { top: 28, left: 10, right: 10 }
            });

            doc.save('Comparison_Report.pdf');
        });
    }

});