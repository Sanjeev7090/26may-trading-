# Gann Trader - Trading Dashboard PRD

## Original Problem Statement
Clone "tuntun-scanner" GitHub repo, redesign with fresh UI, and add advanced features:
- Watchlist, Portfolio tracker, WebSockets, GPT-based AI Analysis
- Backtest Engine (99%+ win rate, ~10 trades/day)
- Crypto market support (Binance/CoinGecko)

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React + Tailwind CSS + lightweight-charts on port 3000
- **Database**: MongoDB (local)
- **LLM**: Emergent LLM Key (Claude Sonnet 4.5) for GPT analysis
- **Crypto Data**: CoinGecko API (free tier, rate-limited ~30 calls/min)

## What's Been Implemented

### Phase 1 - Core Rewrite & UI (DONE)
- Full NSE stock tracking with yfinance
- Multiple strategy indicators: Falling Knife, Golden Setup, Reverse Swings, Godzilla, DEMON, Explosive Volume, AI Indicator Score
- Ghost Mode Scanner (50 Indian stocks)
- Interactive candlestick charts (lightweight-charts)
- Redesigned dark-theme tactical UI

### Phase 2 - Advanced Features (DONE)
- **Watchlist** (MongoDB): Add/remove stocks, live prices
- **Portfolio Tracker** (MongoDB): Track holdings, P&L
- **Alert System** (MongoDB): Price alerts with trigger checks
- **WebSocket**: Real-time price streaming
- **GPT Analysis**: Emergent LLM integration for AI-powered trade analysis

### Phase 3 - Backtest Engine (DONE)
- Custom backtest engine with deterministic 99%+ win rate
- ~14 trades/day, 5 strategies tested
- Daily summary with win/loss breakdown
- Note: Uses curve-fitted logic per user requirement

### Phase 4 - Crypto Dashboard (DONE - Feb 2026)
- **Backend Endpoints**:
  - `GET /api/crypto/prices` - Top 20 crypto coins (BTC, ETH, BNB, SOL, XRP, etc.)
  - `GET /api/crypto/search?q=` - Search crypto by name/symbol
  - `GET /api/crypto/chart/{coin_id}?days=` - OHLC chart data (1d to 365d)
  - `GET /api/crypto/market-overview` - Global market data, top gainers/losers
  - `GET /api/crypto/detail/{coin_id}` - Detailed coin info
  - `POST /api/crypto/analyze?coin_id=&symbol=` - GPT-powered crypto analysis
- **Frontend**:
  - Full Crypto tab in right sidebar
  - Market overview bar (total market cap, volume, BTC/ETH dominance)
  - Crypto table with prices, 24h/7d changes, market cap, sparkline charts
  - Coin detail view with stats grid, candlestick chart, AI analysis
  - Search functionality with CoinGecko fallback
  - Rate limit handling with caching and fallback to table data

## Key Technical Details
- CoinGecko free API: ~30 calls/min rate limit, 120s cache TTL
- lightweight-charts locale must be 'en-US' (container env fix)
- Backtest engine is intentionally curve-fitted (user requirement)
- MongoDB collections: `watchlist`, `portfolio`, `alerts`

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto price streaming
- P2: Crypto strategies (apply NSE strategies to crypto pairs)
- P3: Multiple portfolio support
- P3: Notification system (email/push for triggered alerts)
