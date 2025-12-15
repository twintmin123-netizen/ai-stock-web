// ==========================================
// Portfolio Management
// ==========================================

// Load portfolio from localStorage
function loadPortfolio() {
    try {
        const saved = localStorage.getItem('portfolio');
        if (saved) {
            state.portfolio = JSON.parse(saved);
            renderPortfolio();
        }
    } catch (error) {
        console.error('Failed to load portfolio:', error);
        state.portfolio = [];
    }
}

// Save portfolio to localStorage
function savePortfolio() {
    try {
        localStorage.setItem('portfolio', JSON.stringify(state.portfolio));
    } catch (error) {
        console.error('Failed to save portfolio:', error);
    }
}

// Initialize portfolio search
function initPortfolioSearch() {
    const searchInput = document.getElementById('portfolioSearchInput');
    const searchResults = document.getElementById('portfolioSearchResults');

    if (!searchInput || !searchResults) return;

    const debouncedSearch = debounce(async (query) => {
        if (!query || query.length < 1) {
            searchResults.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.results && data.results.length > 0) {
                renderPortfolioSearchResults(data.results);
                searchResults.style.display = 'block';
            } else {
                searchResults.innerHTML = '<div class="portfolio-search-result-item"><p class="text-muted">검색 결과가 없습니다.</p></div>';
                searchResults.style.display = 'block';
            }
        } catch (error) {
            console.error('Portfolio search failed:', error);
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
}

// Render portfolio search results
function renderPortfolioSearchResults(results) {
    const searchResults = document.getElementById('portfolioSearchResults');

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
            addToPortfolio(ticker);
            searchResults.style.display = 'none';
            document.getElementById('portfolioSearchInput').value = '';
        });
    });
}

// Add stock to portfolio
async function addToPortfolio(ticker) {
    // Check if already exists
    if (state.portfolio.some(stock => stock.ticker === ticker)) {
        console.log('Stock already in portfolio');
        return;
    }

    try {
        // Fetch basic price data
        const response = await fetch(`${API_BASE}/stock/${ticker}/analysis`);
        const data = await response.json();

        const stockData = {
            ticker: ticker,
            name: data.company_name || ticker,
            dailyReturn: data.returns?.['1d'] ?? data.ret_1d ?? 0,
            weeklyReturn: data.returns?.['1w'] ?? data.ret_1w ?? 0,
            returns: data.returns || {},
            chartData: data.chart_data || {},
            currentPrice: data.current_price ?? 0,
            addedAt: new Date().toISOString()
        };

        state.portfolio.push(stockData);
        savePortfolio();
        renderPortfolio();
    } catch (error) {
        console.error('Failed to add to portfolio:', error);
        // Add with placeholder data if API fails
        const stockData = {
            ticker: ticker,
            name: ticker,
            weeklyReturn: 0,
            addedAt: new Date().toISOString()
        };

        state.portfolio.push(stockData);
        savePortfolio();
        renderPortfolio();
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

        return `
            <div class="portfolio-card">
                <div class="portfolio-card-left">
                    <div class="portfolio-ticker">${stock.ticker}</div>
                    <div class="portfolio-name">${stock.name}</div>
                </div>
                <div class="portfolio-card-right">
                    <div class="portfolio-return ${returnClass}">${returnValue}</div>
                    <button class="portfolio-delete-btn" onclick="removeFromPortfolio('${stock.ticker}')">✕</button>
                </div>
            </div>
        `;
    }).join('');
}
