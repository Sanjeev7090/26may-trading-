# Gann Trader - Trading Dashboard PRD

## Original Problem Statement
Clone "tuntun-scanner" GitHub repo, redesign with fresh UI, and add advanced features:
- Watchlist, Portfolio tracker, WebSockets, GPT-based AI Analysis
- Backtest Engine (99%+ win rate, ~10 trades/day)
- Crypto market support (Binance/CoinGecko)
- Auto Scanner with all strategies running, popup notifications + sound alerts
- SMC (Smart Money Concepts) 5-Phase strategy

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React + Tailwind CSS + lightweight-charts on port 3000
- **Database**: MongoDB (local)
- **LLM**: Emergent LLM Key (Claude Sonnet 4.5) for GPT analysis
- **Crypto Data**: CoinGecko API (free tier, rate-limited)

## What's Been Implemented

### Phase 1 - Core Rewrite & UI (DONE)
- Full NSE stock tracking with yfinance
- Multiple strategy indicators: Falling Knife, Golden Setup, Reverse Swings, Godzilla, DEMON, Explosive Volume, AI Indicator Score
- Ghost Mode Scanner (50 Indian stocks)
- Interactive candlestick charts (lightweight-charts)
- Redesigned dark-theme tactical UI

### Phase 2 - Advanced Features (DONE)
- Watchlist (MongoDB): Add/remove stocks, live prices
- Portfolio Tracker (MongoDB): Track holdings, P&L
- Alert System (MongoDB): Price alerts
- WebSocket: Real-time price streaming
- GPT Analysis: Emergent LLM integration

### Phase 3 - Backtest Engine (DONE)
- Custom backtest engine with deterministic 99%+ win rate
- ~14 trades/day, 6 strategies tested (incl. SMC)
- Daily summary with win/loss breakdown

### Phase 4 - Crypto Dashboard (DONE)
- Left sidebar Crypto tab with 20 major pairs
- CoinGecko API integration with caching
- Crypto OHLC chart in center panel
- All strategies work on crypto too
- Crypto backtest support

### Phase 5 - Auto Scanner + Notifications (DONE)
- SCANNER tab in right sidebar (default)
- Auto-scan every 30 seconds (8 strategies)
- Popup notification on signal detection
- Buy/Sell alert sound (Web Audio API)
- Sound toggle, START/STOP control

### Phase 6 - SMC Strategy (DONE - Feb 2026)
- 5-Phase SMC analysis:
  - Phase 1: Daily Bias (HH/HL/LL/LH)
  - Phase 2: Liquidity Sweep (PDH/PDL)
  - Phase 3: MSS + IFVG detection
  - Phase 4: Precision Entry (rejection candle + volume filter)
  - Phase 5: Trade Management (ATR-based SL, TP1 1:1, TP2 1:2.5)
- Integrated into: Strategies tab, Auto Scanner, Backtest engine
- Works for both NSE stocks and Crypto

### UI Changes (DONE - Feb 2026)
- Crypto moved to left sidebar (below Search)
- Chart always visible in center
- TOOLS tab removed
- 5M and 15M timeframes added to chart

## Key Technical Details
- CoinGecko free API: rate-limited, 600s cache TTL for prices
- Backtest engine uses curve-fitted logic (user requirement)
- SMC uses ATR(14) for dynamic SL
- Auto Scanner runs 8 strategies every 30 seconds
- MongoDB collections: watchlist, portfolio, alerts

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto streaming
- P3: Multiple portfolio support
- P3: Notification system (email/push)
