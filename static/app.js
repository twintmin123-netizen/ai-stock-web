// ==========================================
// Configuration
// ==========================================
const API_BASE = '/api';
const DEBOUNCE_DELAY = 500;

// ==========================================
// State Management
// ==========================================
const state = {
    currentTab: 'dashboard',
    chatbotOpen: false,
    chatMessages: [],
    voiceEnabled: false,
    currentAnalysis: null,
    priceChart: null,
    fullChartData: null, // Store full chart data for period filtering
    marketIndicators: null, // Store market data
    portfolio: [] // Portfolio stocks
};

// ==========================================
// Utility Functions
// ==========================================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return 'N/A';
    return num.toFixed(decimals);
}

function formatPercent(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return 'N/A';
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(decimals)}%`;
}

function getChangeClass(value) {
    if (value > 0) return 'positive';
    if (value < 0) return 'negative';
    return 'neutral';
}

function getScoreColor(score) {
    if (score <= 2) return '#ef4444';
    if (score <= 4) return '#f59e0b';
    if (score <= 5) return '#fbbf24';
    if (score <= 7) return '#10b981';
    return '#059669';
}

function getScoreLevel(score) {
    if (score <= 2) return '매우 부정적';
    if (score <= 4) return '부정적';
    if (score <= 5) return '중립';
    if (score <= 7) return '우호적';
    return '매우 우호적';
}

// ==========================================
// Tab Navigation
// ==========================================
function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            // Update active states
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.dataset.tabContent === tabName) {
                    content.classList.add('active');
                }
            });

            state.currentTab = tabName;

            // Load data when switching to dashboard
            if (tabName === 'dashboard') {
                loadMarketIndicators();
            }
        });
    });
}

// ==========================================
// Market Indicators
// ==========================================
async function loadMarketIndicators() {
    try {
        const response = await fetch(`${API_BASE}/market-status`);
        const data = await response.json();

        state.marketIndicators = data; // Save to state

        renderUSIndicators(data.us);
        renderKoreaIndicators(data.korea);

        // Update timestamp
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString('ko-KR');
    } catch (error) {
        console.error('Failed to load market indicators:', error);
    }
}

function renderUSIndicators(us) {
    const container = document.getElementById('usIndicators');

    const indicators = [
        {
            icon: '🇺🇸',
            label: 'S&P 500 (SPY)',
            value: us.spy_3m_ret,
            isPercent: true,
            badge: '3개월',
            tooltip: '미국 대형주 전체 흐름을 보여주는 대표 지수입니다.\n3개월 상승률이 높을수록 시장 전반의 위험선호가 강화된 것으로 해석합니다.'
        },
        {
            icon: '',
            label: 'NASDAQ (QQQ)',
            value: us.qqq_3m_ret,
            isPercent: true,
            badge: '3개월',
            tooltip: '미국 기술·성장주의 방향성을 나타내는 주요 지수입니다.\n금리가 낮거나 유동성이 확대될 때 강세가 나타나는 경향이 있습니다.'
        },
        {
            icon: '',
            label: 'VIX (공포지수)',
            value: us.vix_current,
            isPercent: false,
            badge: '현재',
            tooltip: '옵션 가격 기반으로 산출되는 시장 변동성·불안도 지표입니다.\n20 이상이면 불안 확대, 15 미만이면 안정 구간으로 봅니다.'
        },
        {
            icon: '',
            label: 'US 10Y 국채',
            value: us.tnx_current,
            isPercent: false,
            badge: '수익률',
            suffix: '%',
            tooltip: '미국 10년물 국채 수익률로 글로벌 금리 환경을 판단하는 핵심 지표입니다.\n4% 이상이면 긴축 부담, 3% 이하이면 완화적 환경으로 봅니다.'
        },
        {
            icon: '',
            label: 'DXY (달러인덱스)',
            value: us.dxy_current,
            isPercent: false,
            badge: '현재',
            tooltip: '주요 통화 대비 달러의 강도를 나타내는 지표입니다.\n100 이상이면 강달러로 위험자산에 부담, 100 이하이면 완화적 환경으로 해석합니다.'
        },
        {
            icon: '',
            label: 'Fear & Greed',
            value: us.fgi_score,
            isPercent: false,
            badge: '0-100',
            tooltip: 'CNN이 제공하는 투자 심리지표입니다.\n0~25 극단적 공포, 25~45 공포, 45~55 중립, 55~75 탐욕, 75~100 극단적 탐욕으로 해석합니다.'
        }
    ];

    container.innerHTML = indicators.map(ind => createIndicatorCard(ind)).join('');
}

function renderKoreaIndicators(korea) {
    const container = document.getElementById('koreaIndicators');

    if (!korea || !korea.equity) {
        container.innerHTML = '<p class="text-muted">국내 시장 데이터를 불러올 수 없습니다.</p>';
        return;
    }

    const equity = korea.equity || {};
    const volatility = korea.volatility || {};
    const macro = korea.macro || {};
    const valuation = korea.valuation || {};
    const fx = korea.fx || {};

    const indicators = [];

    // KOSPI
    if (equity.KOSPI) {
        const kospi = equity.KOSPI;
        indicators.push({
            icon: '🇰🇷',
            label: 'KOSPI',
            value: kospi.ret_3m?.value,
            isPercent: true,
            badge: '3개월',
            tooltip: '한국 대형주의 전반적 흐름을 나타내는 대표 지수입니다.\n외국인 수급이 개선될수록 상승 흐름이 강해지는 경향이 있습니다.'
        });
    }

    // KOSDAQ
    if (equity.KOSDAQ) {
        const kosdaq = equity.KOSDAQ;
        indicators.push({
            icon: '',
            label: 'KOSDAQ',
            value: kosdaq.ret_3m?.value,
            isPercent: true,
            badge: '3개월',
            tooltip: '국내 기술·바이오 등 성장주 중심의 지표입니다.\n금리와 유동성 변화에 민감하게 반응합니다.'
        });
    }

    // VKOSPI
    if (volatility.VKOSPI) {
        const vkospi = volatility.VKOSPI;
        indicators.push({
            icon: '',
            label: 'VKOSPI',
            value: vkospi.value,
            isPercent: false,
            badge: '변동성',
            tooltip: 'KOSPI200 옵션 기반의 국내 변동성·공포 지표입니다.\n25 이상이면 변동성 확대, 20 이하이면 안정 구간으로 해석합니다.'
        });
    }

    // Korean 10Y Bond
    if (macro.KR10Y) {
        const kr10y = macro.KR10Y;
        indicators.push({
            icon: '',
            label: '국내 국채 (10Y)',
            value: kr10y.value,
            isPercent: false,
            badge: '수익률',
            suffix: '%',
            tooltip: '한국 10년물 국채 수익률로 국내 금리·유동성 환경을 판단하는 지표입니다.\n4% 이상 긴축 부담, 3% 이하 완화적 환경으로 해석합니다.'
        });
    }

    // KOSPI PBR
    if (valuation.KOSPI_PBR) {
        const kpbr = valuation.KOSPI_PBR;
        indicators.push({
            icon: '',
            label: 'KOSPI PBR',
            value: kpbr.value,
            isPercent: false,
            badge: '밸류에이션',
            prefix: 'x',
            tooltip: '한국 시장의 저평가·고평가 수준을 나타내는 지표입니다.\n1.0 이하 저평가, 1.0~1.5 중립, 1.5 이상 고평가로 해석합니다.'
        });
    }

    // USD/KRW Exchange Rate
    if (fx.USDKRW) {
        const usdkrw = fx.USDKRW;
        indicators.push({
            icon: '',
            label: '환율 (USD/KRW)',
            value: usdkrw.value,
            isPercent: false,
            badge: '현재',
            prefix: '₩',
            tooltip: '원·달러 환율로 원화의 강·약세를 판단하는 핵심 지표입니다.\n상승 시 외국인 매도 압력, 하락 시 위험자산 선호가 강화되는 경향이 있습니다.'
        });
    }

    container.innerHTML = indicators.map(ind => createIndicatorCard(ind)).join('');
}

function createIndicatorCard(ind) {
    const value = ind.value;
    let displayValue;

    if (ind.isPercent) {
        displayValue = formatPercent(value);
    } else {
        const numValue = formatNumber(value, 2);
        const prefix = ind.prefix || '';
        const suffix = ind.suffix || '';
        displayValue = prefix + numValue + suffix;
    }

    const changeClass = ind.isPercent ? getChangeClass(value) : 'neutral';

    return `
        <div class="indicator-card">
            <div class="indicator-header">
                <div class="indicator-label">
                    <span class="indicator-icon">${ind.icon}</span>
                    ${ind.label}
                </div>
                <span class="indicator-badge">${ind.badge}</span>
            </div>
            <div class="indicator-value">${displayValue}</div>
            <div class="indicator-change ${changeClass}">
                ${ind.isPercent ? (value > 0 ? '▲' : value < 0 ? '▼' : '–') : ''}
            </div>
            ${ind.tooltip ? `<div class="indicator-tooltip">${ind.tooltip}</div>` : ''}
        </div>
    `;
}

// ==========================================
// Stock Search
// ==========================================
function initSearch() {
    const searchInput = document.getElementById('stockSearch');
    const searchClear = document.getElementById('searchClear');
    const searchResults = document.getElementById('searchResults');

    const debouncedSearch = debounce(async (query) => {
        if (!query || query.length < 1) {
            searchResults.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.results && data.results.length > 0) {
                renderSearchResults(data.results);
                searchResults.style.display = 'block';
            } else {
                searchResults.innerHTML = '<div class="search-result-item"><p class="text-muted">검색 결과가 없습니다.</p></div>';
                searchResults.style.display = 'block';
            }
        } catch (error) {
            console.error('Search failed:', error);
        }
    }, DEBOUNCE_DELAY);

    searchInput.addEventListener('input', (e) => {
        const value = e.target.value;
        searchClear.style.display = value ? 'flex' : 'none';
        debouncedSearch(value);
    });

    searchClear.addEventListener('click', () => {
        searchInput.value = '';
        searchClear.style.display = 'none';
        searchResults.style.display = 'none';
    });

    // Close results when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });
}

function renderSearchResults(results) {
    const searchResults = document.getElementById('searchResults');

    searchResults.innerHTML = results.slice(0, 10).map(result => `
        <div class="search-result-item" data-ticker="${result.symbol}">
            <div class="result-ticker">${result.symbol}</div>
            <div class="result-name">${result.name || result.symbol}</div>
        </div>
    `).join('');

    // Add click handlers
    searchResults.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const ticker = item.dataset.ticker;
            analyzeStock(ticker);
            searchResults.style.display = 'none';
        });
    });
}

// ==========================================
// Stock Analysis
// ==========================================
async function analyzeStock(ticker) {
    const container = document.getElementById('analysisContainer');
    const loading = document.getElementById('analysisLoading');
    const content = document.getElementById('analysisContent');
    const loadingStatus = document.getElementById('loadingStatus');

    container.style.display = 'block';
    loading.style.display = 'flex';
    content.style.display = 'none';

    // Switch to Analysis Tab (Main Navigation)
    const navTabs = document.querySelectorAll('.nav-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    navTabs.forEach(t => t.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));

    const analyticsTab = document.querySelector('.nav-tab[data-tab="analytics"]');
    const analyticsContent = document.querySelector('.tab-content[data-tab-content="analytics"]');

    if (analyticsTab) analyticsTab.classList.add('active');
    if (analyticsContent) {
        analyticsContent.classList.add('active');
        // Ensure display is correct if it was hidden manually
        analyticsContent.style.display = '';
    }

    // Analysis steps with descriptions
    const analysisSteps = [
        '시장 데이터를 수집하고 있습니다...',
        '종목 가격 정보를 분석하고 있습니다...',
        '기술적 지표를 계산하고 있습니다...',
        '재무 데이터를 조회하고 있습니다...',
        '관련 뉴스를 검색하고 있습니다...',
        'AI 에이전트가 종합 분석을 수행하고 있습니다...',
        '투자 의견을 생성하고 있습니다...'
    ];

    let currentStep = 0;

    // Update status message every 2 seconds
    const statusInterval = setInterval(() => {
        if (currentStep < analysisSteps.length) {
            loadingStatus.textContent = analysisSteps[currentStep];
            currentStep++;
        }
    }, 2000);

    try {
        const response = await fetch(`${API_BASE}/stock/${ticker}/analysis`);
        const data = await response.json();

        // Clear the interval
        clearInterval(statusInterval);

        // Show final status
        loadingStatus.textContent = '분석 완료! 결과를 표시하고 있습니다...';

        state.currentAnalysis = data;

        // Reset sub-tabs to first tab (Analysis)
        const subTabs = document.querySelectorAll('.sub-nav-tab');
        const subTabContents = document.querySelectorAll('.sub-tab-content');

        subTabs.forEach(t => t.classList.remove('active'));
        subTabContents.forEach(c => c.classList.remove('active'));

        // Activate 'analysis' tab
        const analysisTab = document.querySelector('.sub-nav-tab[data-sub-tab="analysis"]');
        const analysisContent = document.querySelector('.sub-tab-content[data-sub-tab-content="analysis"]');

        if (analysisTab) analysisTab.classList.add('active');
        if (analysisContent) analysisContent.classList.add('active');

        // Render all sections
        renderAnalysisTarget(data);
        renderActionCard(data.action);
        renderScoreCards(data);
        renderPriceChart(data.chart_data);
        renderMetrics(data);
        renderFundamentals(data.fundamentals);
        renderCommentary(data.overall_comment);
        renderNews(data.news);

        // Store logs globally for translation toggling
        currentLogs = data.agent_logs || [];
        renderAgentLogs(currentLogs);

        loading.style.display = 'none';
        content.style.display = 'block'; // Changed from grid to block because of sub-tabs
    } catch (error) {
        clearInterval(statusInterval);
        console.error('Analysis failed:', error);
        loading.innerHTML = `
            <div class="loading-text">분석 실패: ${error.message}</div>
        `;
    }
}

function renderAgentLogs(logs) {
    const container = document.getElementById('logsContainer');
    const pdfButton = document.getElementById('btnExportPDF');

    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="log-placeholder">분석 로그가 없습니다.</div>';
        if (pdfButton) pdfButton.style.display = 'none';
        return;
    }

    // Show PDF button when logs are available
    if (pdfButton) pdfButton.style.display = 'flex';

    container.innerHTML = logs.map((log, index) => {
        // Format the output text (simple markdown-like parsing)
        let content = log.output || '';

        // Convert newlines to <br>
        content = content.replace(/\n/g, '<br>');

        // Bold **text**
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Check if already translated
        const isTranslated = log.translated === true;
        const buttonText = isTranslated ? '원문 보기' : '한글 번역';
        const buttonIcon = isTranslated ? '🔤' : '🌐';

        return `
            <div class="log-item" data-log-index="${index}">
                <div class="log-header">
                    <div class="log-step-number">Step ${index + 1}</div>
                    <div class="log-agent-name">${log.step_name}</div>
                    <button class="translate-btn" onclick="toggleTranslation(${index})">
                        <span class="btn-icon">${buttonIcon}</span>
                        <span class="btn-text">${buttonText}</span>
                    </button>
                </div>
                <div class="log-content" id="log-content-${index}">${content}</div>
                <div class="log-loading" id="log-loading-${index}" style="display: none;">
                    <span class="loading-spinner-small"></span> 번역 중...
                </div>
            </div>
        `;
    }).join('');
}

// Global variable to store logs for translation toggling
let currentLogs = [];

async function toggleTranslation(logIndex) {
    const log = currentLogs[logIndex];
    if (!log) return;

    const contentElement = document.getElementById(`log-content-${logIndex}`);
    const loadingElement = document.getElementById(`log-loading-${logIndex}`);
    const logItem = document.querySelector(`[data-log-index="${logIndex}"]`);
    const button = logItem.querySelector('.translate-btn');

    // If already translated, show original
    if (log.translated === true) {
        // Restore original content
        let originalContent = log.original_output || log.output;
        originalContent = originalContent.replace(/\n/g, '<br>');
        originalContent = originalContent.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        contentElement.innerHTML = originalContent;
        log.translated = false;

        // Update button
        button.innerHTML = '<span class="btn-icon">🌐</span><span class="btn-text">한글 번역</span>';
        return;
    }

    // If not translated yet, translate it
    try {
        // Show loading
        contentElement.style.opacity = '0.5';
        loadingElement.style.display = 'flex';
        button.disabled = true;

        // Call translation API
        const response = await fetch(`${API_BASE}/translate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: log.output
            })
        });

        if (!response.ok) {
            throw new Error('Translation failed');
        }

        const data = await response.json();

        // Store original if not already stored
        if (!log.original_output) {
            log.original_output = log.output;
        }

        // Update with translated content
        let translatedContent = data.translated_text;
        translatedContent = translatedContent.replace(/\n/g, '<br>');
        translatedContent = translatedContent.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        contentElement.innerHTML = translatedContent;
        log.translated = true;

        // Update button
        button.innerHTML = '<span class="btn-icon">🔤</span><span class="btn-text">원문 보기</span>';

    } catch (error) {
        console.error('Translation error:', error);
        alert('번역 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
        // Hide loading
        contentElement.style.opacity = '1';
        loadingElement.style.display = 'none';
        button.disabled = false;
    }
}


function renderAnalysisTarget(data) {
    const header = document.getElementById('analysisTargetHeader');
    const valueElement = document.getElementById('analysisTargetValue');

    if (data && data.company_name && data.ticker) {
        valueElement.textContent = `${data.company_name} (${data.ticker})`;
        header.style.display = 'block';
    } else {
        header.style.display = 'none';
    }
}


function renderActionCard(action) {
    const actionCard = document.getElementById('actionCard');
    const actionValue = document.getElementById('actionValue');

    // Set the text
    actionValue.textContent = action || '데이터 없음';

    // Remove all previous action classes
    actionCard.classList.remove('buy', 'sell', 'hold');

    // Add appropriate class based on action
    if (action) {
        const actionUpper = action.toUpperCase();
        if (actionUpper.includes('BUY') || actionUpper.includes('매수')) {
            actionCard.classList.add('buy');
        } else if (actionUpper.includes('SELL') || actionUpper.includes('매도')) {
            actionCard.classList.add('sell');
        } else if (actionUpper.includes('HOLD') || actionUpper.includes('보유') || actionUpper.includes('유지')) {
            actionCard.classList.add('hold');
        }
    }
}

function renderScoreCards(data) {
    const container = document.getElementById('scoresGrid');

    const scores = [
        {
            title: '시장 점수',
            score: data.market_score,
            type: 'market'
        },
        {
            title: '종목 점수',
            score: data.company_score,
            type: 'company'
        },
        {
            title: '단기적 전망',
            score: data.outlook_score,
            type: 'outlook'
        }
    ];

    // Add Probability and Confidence cards if available
    if (data.decision_prob !== undefined) {
        scores.push({
            title: '투자 매력도',
            score: (data.decision_prob * 100).toFixed(1), // Convert to percentage
            type: 'probability',
            isPercent: true
        });
    }

    if (data.confidence !== undefined) {
        scores.push({
            title: '분석 일관성',
            score: (data.confidence * 100).toFixed(1), // Convert to percentage  
            type: 'confidence',
            isPercent: true,
            level: data.confidence_level || '중간'
        });
    }

    container.innerHTML = scores.map(s => {
        // Special handling for probability and confidence
        if (s.type === 'probability' || s.type === 'confidence') {
            const scoreNum = s.score !== null && !isNaN(s.score) ? s.score : 'N/A';
            const color = s.type === 'probability' ?
                (parseFloat(s.score) >= 62 ? '#10b981' : parseFloat(s.score) >= 47 ? '#f59e0b' : '#ef4444') :
                (parseFloat(s.score) >= 70 ? '#10b981' : parseFloat(s.score) >= 45 ? '#f59e0b' : '#ef4444');

            return `
                <div class="score-card">
                    <div class="score-title">${s.title}</div>
                    <div class="score-value-wrapper">
                        ${s.level ? `<div class="score-level" style="color: ${color};">${s.level}</div>` : ''}
                        <div class="score-number" style="color: ${color};">${scoreNum}%</div>
                    </div>
                    <div class="score-description">
                        ${s.type === 'probability' ?
                    `투자 매력도가 ${parseFloat(s.score) >= 62 ? '높습니다' : parseFloat(s.score) >= 47 ? '중립입니다' : '낮습니다'}.` :
                    `지표 간 일관성이 ${s.level} 수준입니다.`}
                    </div>
                </div>
            `;
        }

        // Regular score cards
        const color = getScoreColor(s.score);
        const level = getScoreLevel(s.score);
        const scoreNum = s.score !== null && !isNaN(s.score) ? s.score : 'N/A';

        return `
            <div class="score-card">
                <div class="score-title">${s.title}</div>
                <div class="score-value-wrapper">
                    <div class="score-level" style="color: ${color};">${level}</div>
                    <div class="score-number">${scoreNum}/10</div>
                </div>
                <div class="score-description">
                    ${getScoreDescription(s.score, s.type)}
                </div>
            </div>
        `;
    }).join('');
}

function getScoreDescription(score, type) {
    const target = type === 'market' ? '시장 전반' : type === 'company' ? '해당 종목' : '단기적 전망';

    if (score === null || isNaN(score)) {
        return `${target}을(를) 판단하기 위한 데이터가 부족합니다.`;
    }

    if (score <= 2) return `${target}이(가) 매우 부정적인 구간입니다.`;
    if (score <= 4) return `${target}이(가) 다소 부정적인 구간입니다.`;
    if (score <= 5) return `${target}이(가) 뚜렷한 방향성이 없는 중립 구간입니다.`;
    if (score <= 7) return `${target}이(가) 비교적 우호적인 구간입니다.`;
    return `${target}이(가) 매우 우호적인 구간입니다.`;
}

function renderPriceChart(chartData, period = '1y') {
    const canvas = document.getElementById('priceChart');
    const ctx = canvas.getContext('2d');

    // Store full chart data in state for period filtering
    if (chartData && chartData.prices && chartData.prices.length > 0) {
        state.fullChartData = chartData;
    }

    // Destroy existing chart if any
    if (state.priceChart) {
        state.priceChart.destroy();
    }

    const allPrices = state.fullChartData?.prices || chartData?.prices || [];
    const allDates = state.fullChartData?.dates || chartData?.dates || [];

    // Filter data based on period
    const periodMap = {
        '1w': 5,
        '1m': 21,
        '3m': 63,
        '6m': 126,
        '1y': 252,
        '3y': 756
    };

    const days = periodMap[period] || 252;
    const startIndex = Math.max(0, allPrices.length - days);
    const prices = allPrices.slice(startIndex);
    const dates = allDates.slice(startIndex);

    state.priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: '종가',
                data: prices,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#3b82f6',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(59, 130, 246, 0.5)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function (context) {
                            return '가격: $' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        maxTicksLimit: 8
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: function (value) {
                            return '$' + value.toFixed(0);
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function renderMetrics(data) {
    const container = document.getElementById('metricsGrid');

    const metrics = [
        { label: '1주 수익률', value: formatPercent(data.ret_1w) },
        { label: '1개월 수익률', value: formatPercent(data.ret_1m) },
        { label: '3개월 수익률', value: formatPercent(data.ret_3m) },

        {
            label: 'RSI (14)',
            value: formatNumber(data.rsi, 1),
            tooltip: '최근 가격의 과열·과매도 정도를 나타냅니다. 70 이상은 과열, 30 이하는 과매도로 해석됩니다.'
        }
    ];

    container.innerHTML = metrics.map(m => `
        <div class="metric-item">
            <div class="metric-label">${m.label}</div>
            <div class="metric-value">${m.value}</div>
            ${m.tooltip ? `<div class="metric-tooltip">${m.tooltip}</div>` : ''}
        </div>
    `).join('');
}

function renderFundamentals(fundamentals) {
    const section = document.getElementById('fundamentalsSection');
    const container = document.getElementById('fundamentalsGrid');

    if (!fundamentals || Object.keys(fundamentals).length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    const items = [];

    if (fundamentals.revenue_growth_yoy !== undefined) {
        items.push({
            label: '매출 성장률 (YoY)',
            value: formatPercent(fundamentals.revenue_growth_yoy * 100, 1),
            tooltip: '전년 대비 매출이 얼마나 증가했는지 보여줍니다. 성장성 지표입니다.'
        });
    }
    if (fundamentals.operating_margin !== undefined) {
        items.push({
            label: '영업이익률',
            value: formatPercent(fundamentals.operating_margin * 100, 1),
            tooltip: '매출에서 실제로 얼마나 이익을 남기는지 나타냅니다. 높을수록 수익성이 좋습니다.'
        });
    }
    if (fundamentals.roe !== undefined) {
        items.push({
            label: 'ROE',
            value: formatPercent(fundamentals.roe * 100, 1),
            tooltip: '자기자본을 얼마나 효율적으로 활용해 이익을 내는지 나타냅니다.'
        });
    }
    if (fundamentals.debt_to_equity !== undefined) {
        items.push({
            label: '부채비율 (D/E)',
            value: formatNumber(fundamentals.debt_to_equity, 2),
            tooltip: '자본 대비 부채의 크기를 보여줍니다. 높을수록 재무 위험이 커질 수 있습니다.'
        });
    }
    if (fundamentals.pe !== undefined) {
        items.push({
            label: 'PER',
            value: formatNumber(fundamentals.pe, 2),
            tooltip: '현재 주가가 이익의 몇 배인지 나타냅니다. 높을수록 미래 성장 기대가 크다는 의미입니다.'
        });
    }
    if (fundamentals.pb !== undefined) {
        items.push({
            label: 'PBR',
            value: formatNumber(fundamentals.pb, 2),
            tooltip: '주가가 순자산 대비 몇 배인지 보여줍니다. 1 이하이면 자산 대비 저평가로 볼 수 있습니다.'
        });
    }

    container.innerHTML = items.map(item => `
        <div class="fundamental-item">
            <div class="fundamental-label">${item.label}</div>
            <div class="fundamental-value">${item.value}</div>
            ${item.tooltip ? `<div class="fundamental-tooltip">${item.tooltip}</div>` : ''}
        </div>
    `).join('');
}

function renderCommentary(comment) {
    const container = document.getElementById('commentaryContent');

    if (!comment) {
        container.textContent = 'AI 분석을 생성할 수 없습니다.';
        return;
    }

    // Debug: Log the type and content of comment
    console.log('renderCommentary input:', typeof comment, comment);

    let data;
    try {
        if (typeof comment === 'object' && comment !== null) {
            data = comment;
        } else if (typeof comment === 'string') {
            try {
                data = JSON.parse(comment);
            } catch (e) {
                // If parsing fails, treat it as a plain string
                console.warn('JSON parse failed, treating as string');
                data = { summary: comment };
            }
        } else {
            data = { summary: String(comment) };
        }

        // Check if data has the expected structure
        const hasStructure = data.summary || data.market_env || data.company_summary;

        if (!hasStructure) {
            // If it doesn't look like our expected object, just dump it as text
            const dump = typeof data === 'object' ? JSON.stringify(data, null, 2) : String(data);
            container.innerHTML = `<div class="commentary-text" style="white-space: pre-wrap;">${dump}</div>`;
            return;
        }

        // Helper to safely get text content
        const getText = (val) => {
            if (typeof val === 'object') return JSON.stringify(val);
            return val || '내용 없음';
        };

        // If successful, render structured cards
        container.innerHTML = `
            <div class="commentary-grid">
                <div class="commentary-item full-width">
                    <div class="commentary-label"> 핵심 결론</div>
                    <div class="commentary-text highlight">${getText(data.summary)}</div>
                </div>
                <div class="commentary-item">
                    <div class="commentary-label"> 시장 환경</div>
                    <div class="commentary-text">${getText(data.market_env)}</div>
                </div>
                <div class="commentary-item">
                    <div class="commentary-label"> 종목 요약</div>
                    <div class="commentary-text">${getText(data.company_summary)}</div>
                </div>
                <div class="commentary-item">
                    <div class="commentary-label"> 단기적 전망</div>
                    <div class="commentary-text">${getText(data.outlook_3m)}</div>
                </div>
                <div class="commentary-item">
                    <div class="commentary-label"> 리스크 요인</div>
                    <div class="commentary-text">${getText(data.risks)}</div>
                </div>
                <div class="commentary-item full-width">
                    <div class="commentary-label"> 대응 제안</div>
                    <div class="commentary-text action-text">${getText(data.suggestion)}</div>
                </div>
            </div>
        `;
    } catch (e) {
        console.error('Error in renderCommentary:', e);
        const textContent = typeof comment === 'object' ? JSON.stringify(comment, null, 2) : comment;
        container.innerHTML = `<div class="commentary-text" style="white-space: pre-wrap;">Error: ${e.message}\n\nData: ${textContent}</div>`;
    }
}

function renderNews(news) {
    const container = document.getElementById('newsContainer');

    if (!news || news.length === 0) {
        container.innerHTML = '<p class="text-muted">관련 뉴스가 없습니다.</p>';
        return;
    }

    container.innerHTML = news.slice(0, 10).map(item => {
        const title = item.title_ko || item.title || '제목 없음';
        const source = item.source || '';
        const date = item.published_at || '';
        const url = item.url || '';

        // 제목을 링크로 감싸기 (URL이 있을 경우)
        const titleHTML = url
            ? `<a href="${url}" target="_blank" rel="noopener noreferrer" class="news-link">${title}</a>`
            : title;

        return `
            <div class="news-item">
                <div class="news-item-title">${titleHTML}</div>
                <div class="news-item-meta">
                    ${source ? source : ''} ${source && date ? '|' : ''} ${date ? date : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ==========================================
// Chatbot
// ==========================================
function initChatbot() {
    const toggle = document.getElementById('chatbotToggle');
    const close = document.getElementById('chatbotClose');
    const sidebar = document.getElementById('chatbotSidebar');
    const input = document.getElementById('chatbotInput');
    const send = document.getElementById('chatbotSend');
    const voiceInput = document.getElementById('voiceInput');
    const voiceToggle = document.getElementById('voiceToggle');

    toggle.addEventListener('click', () => {
        sidebar.classList.add('open');
        state.chatbotOpen = true;
    });

    close.addEventListener('click', () => {
        sidebar.classList.remove('open');
        state.chatbotOpen = false;
    });

    send.addEventListener('click', () => sendMessage());

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    voiceToggle.addEventListener('click', () => {
        state.voiceEnabled = !state.voiceEnabled;
        voiceToggle.classList.toggle('active', state.voiceEnabled);
    });

    // Voice input
    voiceInput.addEventListener('click', async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('음성 입력이 지원되지 않는 브라우저입니다.');
            return;
        }

        if (voiceInput.classList.contains('recording')) {
            // Stop recording
            stopRecording();
        } else {
            // Start recording
            startRecording();
        }
    });


    let mediaRecorder;
    let audioChunks = [];
    let audioContext;
    let analyser;
    let silenceStart;
    const SILENCE_THRESHOLD = 0.01; // Volume threshold for silence
    const SILENCE_DURATION = 1000; // 1 second of silence triggers auto-stop

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            // Setup Web Audio API for silence detection
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaStreamSource(stream);
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 2048;
            source.connect(analyser);

            const bufferLength = analyser.fftSize;
            const dataArray = new Uint8Array(bufferLength);

            // Start silence detection
            let isSpeaking = false;
            silenceStart = Date.now();

            const detectSilence = () => {
                if (mediaRecorder && mediaRecorder.state === 'recording') {
                    analyser.getByteTimeDomainData(dataArray);

                    // Calculate average volume (RMS)
                    let sum = 0;
                    for (let i = 0; i < bufferLength; i++) {
                        const normalized = (dataArray[i] - 128) / 128;
                        sum += normalized * normalized;
                    }
                    const rms = Math.sqrt(sum / bufferLength);

                    // Check if speaking or silent
                    if (rms > SILENCE_THRESHOLD) {
                        // User is speaking
                        isSpeaking = true;
                        silenceStart = Date.now();
                    } else if (isSpeaking) {
                        // User stopped speaking, check silence duration
                        const silenceDuration = Date.now() - silenceStart;
                        if (silenceDuration > SILENCE_DURATION) {
                            console.log('🔇 Silence detected, auto-stopping...');
                            stopRecording();
                            return;
                        }
                    }

                    // Continue monitoring
                    requestAnimationFrame(detectSilence);
                }
            };

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

                // Cleanup audio context
                if (audioContext) {
                    audioContext.close();
                    audioContext = null;
                }

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());

                // Send to STT and auto-submit
                await sendAudioToSTT(audioBlob, true); // true = auto-send
            };

            mediaRecorder.start();
            voiceInput.classList.add('recording');
            voiceInput.innerHTML = '⏹️'; // Stop icon
            voiceInput.style.backgroundColor = '#ef4444'; // Red color

            // Start silence detection
            detectSilence();

            // Fallback: Auto stop after 30 seconds (safety limit)
            setTimeout(() => {
                if (mediaRecorder && mediaRecorder.state === 'recording') {
                    console.log('⏱️ Max recording time reached, stopping...');
                    stopRecording();
                }
            }, 30000);

        } catch (error) {
            console.error('Error accessing microphone:', error);
            alert('마이크 접근 권한이 필요합니다.');
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            voiceInput.classList.remove('recording');
            voiceInput.innerHTML = '🎤';
            voiceInput.style.backgroundColor = '';
        }
    }

    async function sendAudioToSTT(audioBlob, autoSend = false) {
        // Show loading state in input
        const originalPlaceholder = input.placeholder;
        input.placeholder = '음성 변환 중...';
        input.disabled = true;

        try {
            const response = await fetch(`${API_BASE}/stt`, {
                method: 'POST',
                body: audioBlob
            });

            if (!response.ok) throw new Error('STT failed');

            const data = await response.json();
            if (data.text) {
                input.value = data.text;

                // Auto-send if requested
                if (autoSend) {
                    console.log('📤 Auto-sending message:', data.text);
                    // Small delay to show the text before sending
                    setTimeout(() => {
                        sendMessage();
                    }, 300);
                } else {
                    input.focus();
                }
            }
        } catch (error) {
            console.error('STT Error:', error);
            alert('음성 인식에 실패했습니다.');
        } finally {
            input.placeholder = originalPlaceholder;
            input.disabled = false;
        }
    }
}

async function sendMessage() {
    const input = document.getElementById('chatbotInput');
    const message = input.value.trim();

    if (!message) return;

    // Add user message to UI
    addChatMessage('user', message);
    input.value = '';

    // Prepare context
    let context = '';

    // Add Market Indicators to context
    if (state.marketIndicators) {
        const m = state.marketIndicators;
        context += `[시장 지표 (실시간)]\n`;

        // US Data
        if (m.us) {
            context += `미국:\n`;
            context += `- SPY 3개월 수익률: ${formatPercent(m.us.spy_3m_ret)}\n`;
            context += `- QQQ 3개월 수익률: ${formatPercent(m.us.qqq_3m_ret)}\n`;
            context += `- VIX (공포지수): ${formatNumber(m.us.vix_current)}\n`;
            context += `- 10년물 국채: ${formatNumber(m.us.tnx_current)}%\n`;
            context += `- FGI (공포탐욕지수): ${m.us.fgi_score}\n`;
        }

        // Korea Data
        if (m.korea) {
            context += `한국:\n`;

            // Equity
            if (m.korea.equity) {
                if (m.korea.equity.KOSPI) {
                    context += `- KOSPI 3개월 수익률: ${formatPercent(m.korea.equity.KOSPI.ret_3m?.value)}\n`;
                }
                if (m.korea.equity.KOSDAQ) {
                    context += `- KOSDAQ 3개월 수익률: ${formatPercent(m.korea.equity.KOSDAQ.ret_3m?.value)}\n`;
                }
            }

            // Volatility
            if (m.korea.volatility && m.korea.volatility.VKOSPI) {
                context += `- VKOSPI (변동성): ${formatNumber(m.korea.volatility.VKOSPI.value)}\n`;
            }

            // Macro
            if (m.korea.macro && m.korea.macro.KR10Y) {
                context += `- 한국 10년물 국채: ${formatNumber(m.korea.macro.KR10Y.value)}%\n`;
            }

            // Valuation
            if (m.korea.valuation && m.korea.valuation.KOSPI_PBR) {
                context += `- KOSPI PBR: ${formatNumber(m.korea.valuation.KOSPI_PBR.value)}\n`;
            }

            // FX
            if (m.korea.fx && m.korea.fx.USDKRW) {
                context += `- 원/달러 환율: ${formatNumber(m.korea.fx.USDKRW.value)}원\n`;
            }
        }
        context += `\n`;
    }

    if (state.currentAnalysis) {
        const a = state.currentAnalysis;
        context += `[현재 분석 데이터]\n`;
        context += `- 종목: ${a.ticker}\n`;
        context += `- 회사명: ${a.company_name || a.ticker}\n`;
        context += `- 투자 판단: ${a.action}\n`;
        context += `- 시장 점수: ${a.market_score}/10\n`;
        context += `- 종목 점수: ${a.company_score}/10\n`;
        context += `- 전망 점수: ${a.outlook_score}/10\n`;

        // Add Investment Attractiveness (decision_prob)
        if (a.decision_prob !== undefined) {
            const probPercent = (a.decision_prob * 100).toFixed(1);
            context += `- 투자 매력도 (Investment Attractiveness): ${probPercent}%\n`;
            context += `  (상승 확률 기반 지표, 62% 이상=높음, 47~62%=중립, 47% 미만=낮음)\n`;
        }

        // Add Analysis Consistency (confidence)
        if (a.confidence !== undefined) {
            const confPercent = (a.confidence * 100).toFixed(1);
            const confLevel = a.confidence_level || '중간';
            context += `- 분석 일관성 (Analysis Consistency): ${confPercent}% (${confLevel})\n`;
            context += `  (여러 지표 간 일치도, 70% 이상=높음, 45~70%=중간, 45% 미만=낮음)\n`;
        }

        // Add Decision Breakdown (why these scores?)
        if (a.decision_breakdown) {
            context += `\n[투자 판단 근거]\n`;
            const db = a.decision_breakdown;
            if (db.market_gate !== undefined) {
                context += `- 시장 게이트: ${db.market_gate ? '통과' : '미통과'}\n`;
            }
            if (db.timing_gate !== undefined) {
                context += `- 타이밍 게이트: ${db.timing_gate ? '통과' : '미통과'}\n`;
            }
            if (db.p_up !== undefined) {
                context += `- 상승 확률 (p_up): ${(db.p_up * 100).toFixed(1)}%\n`;
            }
            if (db.p_down !== undefined) {
                context += `- 하락 확률 (p_down): ${(db.p_down * 100).toFixed(1)}%\n`;
            }
            if (db.p_neutral !== undefined) {
                context += `- 중립 확률 (p_neutral): ${(db.p_neutral * 100).toFixed(1)}%\n`;
            }
        }

        // Add AI Commentary
        if (a.overall_comment) {
            context += `\n[AI 종합 코멘트]\n`;
            if (typeof a.overall_comment === 'object') {
                if (a.overall_comment.summary) {
                    context += `핵심 결론: ${a.overall_comment.summary}\n`;
                }
                if (a.overall_comment.market_env) {
                    context += `시장 환경: ${a.overall_comment.market_env}\n`;
                }
                if (a.overall_comment.company_summary) {
                    context += `종목 요약: ${a.overall_comment.company_summary}\n`;
                }
                if (a.overall_comment.outlook_3m) {
                    context += `단기적 전망: ${a.overall_comment.outlook_3m}\n`;
                }
                if (a.overall_comment.risks) {
                    context += `리스크 요인: ${a.overall_comment.risks}\n`;
                }
                if (a.overall_comment.suggestion) {
                    context += `대응 제안: ${a.overall_comment.suggestion}\n`;
                }
            } else {
                context += `${a.overall_comment}\n`;
            }
        }

        // Add Recent News (Top 5)
        if (a.news && a.news.length > 0) {
            context += `\n[최근 뉴스 (상위 5개)]\n`;
            a.news.slice(0, 5).forEach((item, idx) => {
                const title = item.title_ko || item.title || '제목 없음';
                const date = item.published_at || '';
                context += `${idx + 1}. ${title}`;
                if (date) context += ` (${date})`;
                context += `\n`;
            });
        }

        // Add Fundamentals
        if (a.fundamentals) {
            const f = a.fundamentals;
            context += `\n[재무 제표 요약]\n`;
            if (f.pe !== undefined) context += `- PER: ${f.pe}\n`;
            if (f.pb !== undefined) context += `- PBR: ${f.pb}\n`;
            if (f.roe !== undefined) context += `- ROE: ${(f.roe * 100).toFixed(1)}%\n`;
            if (f.revenue_growth_yoy !== undefined) context += `- 매출 성장률 (YoY): ${(f.revenue_growth_yoy * 100).toFixed(1)}%\n`;
            if (f.operating_margin !== undefined) context += `- 영업이익률: ${(f.operating_margin * 100).toFixed(1)}%\n`;
            if (f.debt_to_equity !== undefined) context += `- 부채비율: ${f.debt_to_equity.toFixed(2)}\n`;
            if (f.market_cap) context += `- 시가총액: ${f.market_cap}\n`;
        }

        // Add Price Metrics
        if (a.ret_1w !== undefined || a.ret_1m !== undefined || a.ret_3m !== undefined) {
            context += `\n[가격 수익률]\n`;
            if (a.ret_1w !== undefined) context += `- 1주: ${formatPercent(a.ret_1w)}\n`;
            if (a.ret_1m !== undefined) context += `- 1개월: ${formatPercent(a.ret_1m)}\n`;
            if (a.ret_3m !== undefined) context += `- 3개월: ${formatPercent(a.ret_3m)}\n`;
            if (a.rsi !== undefined) context += `- RSI(14): ${formatNumber(a.rsi, 1)}\n`;
        }
    }

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                messages: [
                    ...state.chatMessages,
                    { role: 'user', content: message }
                ],
                context: context
            })
        });

        const data = await response.json();
        let assistantMessage = data.response || '응답을 생성할 수 없습니다.';

        // Check for navigation tag
        const navMatch = assistantMessage.match(/\[\[ANALYZE:(.*?)\]\]/);
        if (navMatch) {
            const ticker = navMatch[1];
            // Remove tag from display message
            assistantMessage = assistantMessage.replace(navMatch[0], '');

            // Trigger analysis
            analyzeStock(ticker);
        }

        addChatMessage('assistant', assistantMessage);

        // Text-to-speech if enabled
        if (state.voiceEnabled) {
            playTextToSpeech(assistantMessage);
        }
    } catch (error) {
        console.error('Chat failed:', error);
        addChatMessage('assistant', '죄송합니다. 오류가 발생했습니다.');
    }
}

function addChatMessage(role, content) {
    const messagesContainer = document.getElementById('chatbotMessages');

    // Clean content for display (just in case)
    const displayContent = content.replace(/\[\[ANALYZE:.*?\]\]/g, '');

    state.chatMessages.push({ role, content: displayContent });

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${displayContent}</div>`;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function playTextToSpeech(text) {
    try {
        const response = await fetch(`${API_BASE}/tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text })
        });

        if (response.ok) {
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();
        }
    } catch (error) {
        console.error('TTS failed:', error);
    }
}

// ==========================================
// Sub Tab Navigation (Analysis Section)
// ==========================================
function initSubTabs() {
    const subTabs = document.querySelectorAll('.sub-nav-tab');
    const subTabContents = document.querySelectorAll('.sub-tab-content');

    subTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.subTab;

            // Update active states
            subTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            subTabContents.forEach(content => {
                content.classList.remove('active');
                if (content.dataset.subTabContent === tabName) {
                    content.classList.add('active');
                }
            });

            // Resize chart if chart tab is selected
            if (tabName === 'chart' && state.priceChart) {
                setTimeout(() => {
                    state.priceChart.resize();
                }, 0);
            }
        });
    });
}

// Initialize chart period buttons (Analysis Tab)
function initChartPeriodButtons() {
    const periodButtons = document.querySelectorAll('.chart-period-btn');

    periodButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const period = btn.dataset.period;

            // Update active state on buttons
            periodButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Re-render chart with new period
            if (state.fullChartData) {
                renderPriceChart(state.fullChartData, period);
            }
        });
    });
}

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSubTabs(); // Initialize sub-tabs
    initMarketTabs(); // Initialize market tabs
    initChartPeriodButtons(); // Initialize chart period buttons
    initSearch();
    initChatbot();
    initPortfolioSearch(); // Initialize portfolio search

    // Load initial data
    loadMarketIndicators();
    loadPortfolio(); // Load portfolio from localStorage

    // Refresh portfolio data to get latest prices
    setTimeout(() => {
        refreshPortfolioData();
    }, 1000); // Delay 1 second to ensure DOM is ready

    // Refresh market data every 5 minutes (starting now)
    setInterval(loadMarketIndicators, 5 * 60 * 1000);

    // Refresh portfolio data every 5 minutes (offset by 2.5 minutes to avoid collision)
    setInterval(refreshPortfolioData, 5 * 60 * 1000);

    // Offset the portfolio refresh to avoid simultaneous API calls
    setTimeout(() => {
        refreshPortfolioData();
    }, 2.5 * 60 * 1000); // Start portfolio refresh 2.5 minutes after page load

    // Add PDF export button listener
    const pdfButton = document.getElementById('btnExportPDF');
    if (pdfButton) {
        pdfButton.addEventListener('click', exportPDF);
    }
});

function initMarketTabs() {
    const tabs = document.querySelectorAll('.market-tab');
    const sections = document.querySelectorAll('.market-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const market = tab.dataset.market;

            // Update active state for tabs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show/Hide sections
            sections.forEach(section => {
                if (section.dataset.marketSection === market) {
                    section.style.display = 'block';
                    // Trigger animation if available
                    section.style.animation = 'none';
                    section.offsetHeight; /* trigger reflow */
                    section.style.animation = 'fadeIn 0.3s ease-out';
                } else {
                    section.style.display = 'none';
                }
            });
        });
    });
}

// ==========================================

// Save portfolio to localStorage
function savePortfolio() {
    try {
        localStorage.setItem('portfolio', JSON.stringify(state.portfolio));
    } catch (error) {
        console.error('Failed to save portfolio:', error);
    }
}

// Load portfolio from localStorage
function loadPortfolio() {
    try {
        const saved = localStorage.getItem('portfolio');
        if (saved) {
            state.portfolio = JSON.parse(saved);
            renderPortfolio();
            console.log('✅ Portfolio loaded from localStorage:', state.portfolio.length, 'stocks');
        }
    } catch (error) {
        console.error('Failed to load portfolio:', error);
        state.portfolio = [];
    }
}

// Initialize portfolio search
function initPortfolioSearch() {
    const searchInput = document.getElementById('portfolioSearchInput');
    const searchResults = document.getElementById('portfolioSearchResults');

    console.log('🔍 Initializing portfolio search...');
    console.log('Search Input:', searchInput);
    console.log('Search Results:', searchResults);

    if (!searchInput || !searchResults) {
        console.error('❌ Portfolio search elements not found!');
        return;
    }

    console.log('✅ Portfolio search elements found');

    const debouncedSearch = debounce(async (query) => {
        console.log('🔎 Portfolio search query:', query);

        if (!query || query.length < 1) {
            searchResults.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query)}`);
            const data = await response.json();

            console.log('📊 Portfolio search results:', data);

            if (data.results && data.results.length > 0) {
                renderPortfolioSearchResults(data.results);
                searchResults.style.display = 'block';
                console.log('✅ Showing portfolio search results');
            } else {
                searchResults.innerHTML = '<div class="portfolio-search-result-item"><p class="text-muted">검색 결과가 없습니다.</p></div>';
                searchResults.style.display = 'block';
            }
        } catch (error) {
            console.error('❌ Portfolio search failed:', error);
        }
    }, DEBOUNCE_DELAY);

    searchInput.addEventListener('input', (e) => {
        debouncedSearch(e.target.value);
    });

    // Close results when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });

    console.log('✅ Portfolio search initialized successfully');
}

// Render portfolio search results
function renderPortfolioSearchResults(results) {
    const searchResults = document.getElementById('portfolioSearchResults');

    console.log('📋 Rendering', results.length, 'portfolio search results');

    searchResults.innerHTML = results.slice(0, 10).map(result => `
        <div class="portfolio-search-result-item" data-ticker="${result.symbol}">
            <div class="portfolio-result-ticker">${result.symbol}</div>
            <div class="portfolio-result-name">${result.name || result.symbol}</div>
        </div>
    `).join('');

    // Add click handlers
    searchResults.querySelectorAll('.portfolio-search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const ticker = item.dataset.ticker;
            console.log('🖱️ Clicked portfolio item:', ticker);
            addToPortfolio(ticker);
            searchResults.style.display = 'none';
            document.getElementById('portfolioSearchInput').value = '';
        });
    });

    console.log('✅ Click handlers attached to', searchResults.querySelectorAll('.portfolio-search-result-item').length, 'items');
}

// Add stock to portfolio
async function addToPortfolio(ticker) {
    console.log('➕ Adding to portfolio:', ticker);

    // Check if already exists
    if (state.portfolio.some(stock => stock.ticker === ticker)) {
        console.log('⚠️ Stock already in portfolio:', ticker);
        alert(`${ticker}는 이미 포트폴리오에 있습니다.`);
        return;
    }

    console.log('🔄 Fetching stock data for:', ticker);

    try {
        // Fetch basic price data (Using lightweight endpoint)
        const response = await fetch(`${API_BASE}/stock/${ticker}/basic`);
        console.log('📡 API response status:', response.status);

        const data = await response.json();
        console.log('📊 Stock data received:', data);

        const stockData = {
            ticker: ticker,
            name: data.company_name || ticker,
            dailyReturn: data.returns?.['1d'] || 0,
            weeklyReturn: data.returns?.['1w'] || 0,
            returns: data.returns || {},
            chartData: data.chart_data || {},
            currentPrice: data.current_price || 0,
            addedAt: new Date().toISOString()
        };

        console.log('💾 Saving stock to portfolio:', stockData);
        state.portfolio.push(stockData);
        savePortfolio();
        renderPortfolio();
        console.log('✅ Stock added successfully!');
    } catch (error) {
        console.error('❌ Failed to add to portfolio:', error);
        // Add with placeholder data if API fails
        const stockData = {
            ticker: ticker,
            name: ticker,
            weeklyReturn: 0,
            returns: {},
            chartData: {},
            currentPrice: 0,
            addedAt: new Date().toISOString()
        };

        console.log('⚠️ Adding with placeholder data');
        state.portfolio.push(stockData);
        savePortfolio();
        renderPortfolio();
        console.log('✅ Stock added with placeholder data');
    }
}

// Remove stock from portfolio
function removeFromPortfolio(ticker) {
    state.portfolio = state.portfolio.filter(stock => stock.ticker !== ticker);
    savePortfolio();
    renderPortfolio();
}

// Render portfolio grid
function renderPortfolio() {
    const emptyState = document.getElementById('portfolioEmpty');
    const grid = document.getElementById('portfolioGrid');

    if (!emptyState || !grid) return;

    if (state.portfolio.length === 0) {
        emptyState.style.display = 'block';
        grid.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    grid.style.display = 'grid';

    grid.innerHTML = state.portfolio.map(stock => {
        const returnClass = getChangeClass(stock.weeklyReturn);
        const returnValue = formatPercent(stock.weeklyReturn, 2);
        const currentPrice = stock.currentPrice ? `$${formatNumber(stock.currentPrice, 2)}` : '';

        // Prepare metrics for expanded view
        const returns = stock.returns || {};
        const r1w = formatPercent(returns['1w'] || stock.weeklyReturn, 2);
        const r1m = formatPercent(returns['1m'], 2);
        const r3m = formatPercent(returns['3m'], 2);
        const r6m = formatPercent(returns['6m'], 2);
        const r1y = formatPercent(returns['1y'], 2);

        const c1w = getChangeClass(returns['1w'] || stock.weeklyReturn);
        const c1m = getChangeClass(returns['1m']);
        const c3m = getChangeClass(returns['3m']);
        const c6m = getChangeClass(returns['6m']);
        const c1y = getChangeClass(returns['1y']);

        return `
            <div class="portfolio-card" id="card-${stock.ticker}" onclick="togglePortfolioItem('${stock.ticker}')">
                <div class="portfolio-header">
                    <div class="portfolio-card-left">
                        <div class="portfolio-ticker">${stock.ticker}</div>
                        <div class="portfolio-name">${stock.name}</div>
                    </div>
                    <div class="portfolio-card-right">
                        ${currentPrice ? `<div class="portfolio-price" style="font-weight:700; color:#f8fafc; margin-right:1rem;">${currentPrice}</div>` : ''}
                        <div class="portfolio-return-label">1주</div>
                        <div class="portfolio-return ${returnClass}">${returnValue}</div>
                        <button class="portfolio-delete-btn" onclick="event.stopPropagation(); removeFromPortfolio('${stock.ticker}')">✕</button>
                    </div>
                </div>
                
                <div class="portfolio-expanded-content" onclick="event.stopPropagation()">
                    <div class="portfolio-chart-container">
                        <canvas id="chart-${stock.ticker}"></canvas>
                    </div>
                    
                    <div class="portfolio-metrics-row">
                        <div class="portfolio-metric">
                            <div class="portfolio-metric-label">1주</div>
                            <div class="portfolio-metric-value ${c1w}">${r1w}</div>
                        </div>
                        <div class="portfolio-metric">
                            <div class="portfolio-metric-label">1달</div>
                            <div class="portfolio-metric-value ${c1m}">${r1m}</div>
                        </div>
                        <div class="portfolio-metric">
                            <div class="portfolio-metric-label">3달</div>
                            <div class="portfolio-metric-value ${c3m}">${r3m}</div>
                        </div>
                        <div class="portfolio-metric">
                            <div class="portfolio-metric-label">6달</div>
                            <div class="portfolio-metric-value ${c6m}">${r6m}</div>
                        </div>
                        <div class="portfolio-metric">
                            <div class="portfolio-metric-label">1년</div>
                            <div class="portfolio-metric-value ${c1y}">${r1y}</div>
                        </div>
                    </div>
                    
                    <button class="portfolio-action-btn" onclick="analyzeStock('${stock.ticker}')">
                        AI 분석하기
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function togglePortfolioItem(ticker) {
    const card = document.getElementById(`card-${ticker}`);
    if (!card) return;

    // Close other cards
    document.querySelectorAll('.portfolio-card.expanded').forEach(c => {
        if (c.id !== `card-${ticker}`) c.classList.remove('expanded');
    });

    card.classList.toggle('expanded');

    if (card.classList.contains('expanded')) {
        // Render chart if needed
        const stock = state.portfolio.find(s => s.ticker === ticker);
        if (stock && stock.chartData && stock.chartData.prices && stock.chartData.prices.length > 0) {
            // Small delay to allow animation to start/layout to settle
            setTimeout(() => {
                renderMiniChart(ticker, stock.chartData);
            }, 50);
        }
    }
    console.log('📋 Rendering', results.length, 'portfolio search results');

    searchResults.innerHTML = results.slice(0, 10).map(result => `
        <div class="portfolio-search-result-item" data-ticker="${result.symbol}">
            <div class="portfolio-result-ticker">${result.symbol}</div>
            <div class="portfolio-result-name">${result.name || result.symbol}</div>
        </div>
    `).join('');

    // Add click handlers
    searchResults.querySelectorAll('.portfolio-search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const ticker = item.dataset.ticker;
            console.log('🖱️ Clicked portfolio item:', ticker);
            addToPortfolio(ticker);
            searchResults.style.display = 'none';
            document.getElementById('portfolioSearchInput').value = '';
        });
    });

    console.log('✅ Click handlers attached to', searchResults.querySelectorAll('.portfolio-search-result-item').length, 'items');
}

// Add stock to portfolio
async function addToPortfolio(ticker) {
    console.log('➕ Adding to portfolio:', ticker);

    // Check if already exists
    if (state.portfolio.some(stock => stock.ticker === ticker)) {
        console.log('⚠️ Stock already in portfolio:', ticker);
        alert(`${ticker}는 이미 포트폴리오에 있습니다.`);
        return;
    }

    console.log('🔄 Fetching stock data for:', ticker);

    try {
        // Fetch basic price data (Using lightweight endpoint)
        const response = await fetch(`${API_BASE}/stock/${ticker}/basic`);
        console.log('📡 API response status:', response.status);

        const data = await response.json();
        console.log('📊 Stock data received:', data);

        const stockData = {
            ticker: ticker,
            name: data.company_name || ticker,
            dailyReturn: data.returns?.['1d'] ?? data.ret_1d ?? 0,
            weeklyReturn: data.returns?.['1w'] ?? data.ret_1w ?? 0,
            returns: data.returns || {},
            chartData: data.chart_data || {},
            currentPrice: data.current_price ?? data.last_price ?? 0,
            addedAt: new Date().toISOString()
        };

        console.log('💾 Saving stock to portfolio:', stockData);
        state.portfolio.push(stockData);
        savePortfolio();
        renderPortfolio();
        console.log('✅ Stock added successfully!');
    } catch (error) {
        console.error('❌ Failed to add to portfolio:', error);
        // Add with placeholder data if API fails
        const stockData = {
            ticker: ticker,
            name: ticker,
            weeklyReturn: 0,
            returns: {},
            chartData: {},
            currentPrice: 0,
            addedAt: new Date().toISOString()
        };

        console.log('⚠️ Adding with placeholder data');
        state.portfolio.push(stockData);
        savePortfolio();
        renderPortfolio();
        console.log('✅ Stock added with placeholder data');
    }
}

// Remove stock from portfolio
function removeFromPortfolio(ticker) {
    state.portfolio = state.portfolio.filter(stock => stock.ticker !== ticker);
    savePortfolio();
    renderPortfolio();
}

// Render portfolio grid
function renderPortfolio() {
    const emptyState = document.getElementById('portfolioEmpty');
    const grid = document.getElementById('portfolioGrid');

    if (!emptyState || !grid) return;

    if (state.portfolio.length === 0) {
        emptyState.style.display = 'block';
        grid.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    grid.style.display = 'grid';

    grid.innerHTML = state.portfolio.map(stock => {
        // Detect currency symbol (Korean stocks use ₩, others use $)
        const isKorean = stock.ticker.endsWith('.KS') || stock.ticker.endsWith('.KQ');
        const currencySymbol = isKorean ? '₩' : '$';

        // Format price with appropriate currency
        const currentPrice = stock.currentPrice ? `${currencySymbol}${formatNumber(stock.currentPrice, 2)}` : '';

        // Get 1D change for header
        const dailyReturn = stock.dailyReturn || 0;
        const dailyReturnClass = getChangeClass(dailyReturn);
        const dailyReturnValue = formatPercent(dailyReturn, 2);

        // Prepare metrics for expanded view (Only 1W, 1M, 3M, 6M, 1Y - removed 5Y)
        const returns = stock.returns || {};
        const r1w = formatPercent(returns['1w'] || stock.weeklyReturn, 2);
        const r1m = formatPercent(returns['1m'], 2);
        const r3m = formatPercent(returns['3m'], 2);
        const r6m = formatPercent(returns['6m'], 2);
        const r1y = formatPercent(returns['1y'], 2);

        const c1w = getChangeClass(returns['1w'] || stock.weeklyReturn);
        const c1m = getChangeClass(returns['1m']);
        const c3m = getChangeClass(returns['3m']);
        const c6m = getChangeClass(returns['6m']);
        const c1y = getChangeClass(returns['1y']);

        return `
            <div class="portfolio-card" id="card-${stock.ticker}" onclick="togglePortfolioItem('${stock.ticker}')">
                <div class="portfolio-header">
                    <div class="portfolio-card-left">
                        <div class="portfolio-ticker">${stock.ticker}</div>
                        <div class="portfolio-name">${stock.name}</div>
                    </div>
                    <div class="portfolio-card-right">
                        ${currentPrice ? `<div class="portfolio-price" style="font-weight:700; color:#1e293b; margin-right:0.5rem;">${currentPrice}</div>` : ''}
                        <div class="portfolio-return-label">1D</div>
                        <div class="portfolio-return ${dailyReturnClass}">${dailyReturnValue}</div>
                        <button class="portfolio-delete-btn" onclick="event.stopPropagation(); removeFromPortfolio('${stock.ticker}')">✕</button>
                    </div>
                </div>
                
                <div class="portfolio-expanded-content" onclick="event.stopPropagation()">
                    <div class="portfolio-chart-container">
                        <canvas id="chart-${stock.ticker}"></canvas>
                    </div>
                    
                    <div class="portfolio-metrics-row">
                        <div class="portfolio-metric portfolio-metric-period" data-period="1w" onclick="updateChartPeriod('${stock.ticker}', '1w')">
                            <div class="portfolio-metric-label">1W</div>
                            <div class="portfolio-metric-value ${c1w}">${r1w}</div>
                        </div>
                        <div class="portfolio-metric portfolio-metric-period" data-period="1m" onclick="updateChartPeriod('${stock.ticker}', '1m')">
                            <div class="portfolio-metric-label">1M</div>
                            <div class="portfolio-metric-value ${c1m}">${r1m}</div>
                        </div>
                        <div class="portfolio-metric portfolio-metric-period" data-period="3m" onclick="updateChartPeriod('${stock.ticker}', '3m')">
                            <div class="portfolio-metric-label">3M</div>
                            <div class="portfolio-metric-value ${c3m}">${r3m}</div>
                        </div>
                        <div class="portfolio-metric portfolio-metric-period" data-period="6m" onclick="updateChartPeriod('${stock.ticker}', '6m')">
                            <div class="portfolio-metric-label">6M</div>
                            <div class="portfolio-metric-value ${c6m}">${r6m}</div>
                        </div>
                        <div class="portfolio-metric portfolio-metric-period" data-period="1y" onclick="updateChartPeriod('${stock.ticker}', '1y')">
                            <div class="portfolio-metric-label">1Y</div>
                            <div class="portfolio-metric-value ${c1y}">${r1y}</div>
                        </div>
                    </div>
                    
                    <button class="portfolio-action-btn" onclick="analyzeStock('${stock.ticker}')">
                        AI 분석하기
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function togglePortfolioItem(ticker) {
    const card = document.getElementById(`card-${ticker}`);
    if (!card) return;

    // Close other cards
    document.querySelectorAll('.portfolio-card.expanded').forEach(c => {
        if (c.id !== `card-${ticker}`) c.classList.remove('expanded');
    });

    card.classList.toggle('expanded');

    if (card.classList.contains('expanded')) {
        // Render chart if needed
        const stock = state.portfolio.find(s => s.ticker === ticker);
        if (stock && stock.chartData && stock.chartData.prices && stock.chartData.prices.length > 0) {
            // Small delay to allow animation to start/layout to settle
            setTimeout(() => {
                renderMiniChart(ticker, stock.chartData, '1y'); // Default to 1 year
            }, 50);
        }
    }
}

function renderMiniChart(ticker, chartData, period = '1y') {
    const canvas = document.getElementById(`chart-${ticker}`);
    if (!canvas) return;

    // Destroy existing chart if any
    if (canvas.chart) {
        canvas.chart.destroy();
    }

    const ctx = canvas.getContext('2d');
    const allPrices = chartData.prices;
    const allDates = chartData.dates;

    // Filter data based on period
    const periodMap = {
        '1w': 5,
        '1m': 21,
        '3m': 63,
        '6m': 126,
        '1y': 252,
        '5y': 1260
    };

    const days = periodMap[period] || 252;
    const startIndex = Math.max(0, allPrices.length - days);
    const prices = allPrices.slice(startIndex);
    const dates = allDates.slice(startIndex);

    // Simple color based on trend
    const isPositive = prices[prices.length - 1] >= prices[0];
    const color = isPositive ? '#10b981' : '#ef4444';
    const bgColor = isPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    canvas.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                data: prices,
                borderColor: color,
                backgroundColor: bgColor,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    displayColors: false,
                    callbacks: {
                        label: function (context) {
                            return '$' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: { display: false },
                y: { display: false } // Hide Y axis for cleaner look
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Update chart period when clicking on period buttons
function updateChartPeriod(ticker, period) {
    // Update active state on buttons
    const card = document.getElementById(`card-${ticker}`);
    if (!card) return;

    const periodButtons = card.querySelectorAll('.portfolio-metric-period');
    periodButtons.forEach(btn => {
        if (btn.dataset.period === period) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Re-render chart with new period
    const stock = state.portfolio.find(s => s.ticker === ticker);
    if (stock && stock.chartData) {
        renderMiniChart(ticker, stock.chartData, period);
    }
}

// Refresh portfolio data in background
async function refreshPortfolioData() {
    console.log('🔄 Refreshing portfolio data...');

    if (!state.portfolio || state.portfolio.length === 0) return;

    // Create a snapshot of tickers to refresh
    const stocksToRefresh = [...state.portfolio];

    const updates = await Promise.all(stocksToRefresh.map(async (stock) => {
        try {
            // Add timestamp to prevent caching
            const timestamp = Date.now();
            const response = await fetch(`${API_BASE}/stock/${stock.ticker}/basic?_t=${timestamp}`);
            const data = await response.json();

            // 🔍 Enhanced DEBUG logging
            console.log(`📊 [${new Date().toLocaleTimeString()}] API Response for ${stock.ticker}:`, {
                ticker: data.ticker,
                current_price: data.current_price,
                returns_1d: data.returns?.['1d'],
                returns_1w: data.returns?.['1w'],
                all_returns: data.returns
            });

            // Merge with existing data but update dynamic fields
            return {
                ticker: stock.ticker,
                data: {
                    ...stock,
                    dailyReturn: data.returns?.['1d'] || 0,
                    weeklyReturn: data.returns?.['1w'] || 0,
                    returns: data.returns || {},
                    chartData: data.chart_data || {},
                    currentPrice: data.current_price || 0
                }
            };
        } catch (e) {
            console.error(`❌ Failed to refresh ${stock.ticker}:`, e);
            return { ticker: stock.ticker, data: stock }; // Keep old data if refresh fails
        }
    }));

    // Create a map for quick lookup
    const updateMap = new Map(updates.map(u => [u.ticker, u.data]));

    // Update state.portfolio safely (preserving any new items added during fetch)
    state.portfolio = state.portfolio.map(stock => {
        const updatedData = updateMap.get(stock.ticker);
        return updatedData ? updatedData : stock;
    });

    savePortfolio();
    renderPortfolio();
    console.log(`✅ Portfolio data refreshed at ${new Date().toLocaleTimeString()}`);
}

// ==========================================
// PDF Export
// ==========================================
async function exportPDF() {
    if (!state.currentAnalysis) {
        alert('분석 데이터가 없습니다. 먼저 종목을 분석해주세요.');
        return;
    }

    const pdfButton = document.getElementById('btnExportPDF');

    try {
        // Disable button and show loading state
        if (pdfButton) {
            pdfButton.disabled = true;
            pdfButton.innerHTML = '<span class="pdf-icon">⏳</span><span class="pdf-text">생성 중...</span>';
        }

        console.log('📄 Requesting PDF generation...');

        // Send analysis data to backend
        const response = await fetch(`${API_BASE}/report/pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(state.currentAnalysis)
        });

        if (!response.ok) {
            throw new Error(`PDF generation failed: ${response.statusText}`);
        }

        // Get PDF blob
        const blob = await response.blob();

        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Extract filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'AI_Analysis_Report.pdf';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename=(.+)/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();

        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        console.log('✅ PDF downloaded successfully');

    } catch (error) {
        console.error('❌ PDF export failed:', error);
        alert('PDF 생성 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
        // Restore button state
        if (pdfButton) {
            pdfButton.disabled = false;
            pdfButton.innerHTML = '<span class="pdf-icon">📄</span><span class="pdf-text">PDF 리포트 다운로드</span>';
        }
    }
}
