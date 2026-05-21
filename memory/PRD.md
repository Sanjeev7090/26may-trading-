# Gann Trader - Trading Dashboard PRD

## Original Problem Statement
Clone "tuntun-scanner" GitHub repo, redesign with fresh UI, and add advanced features:
- Watchlist, Portfolio tracker, WebSockets, GPT-based AI Analysis
- Backtest Engine (99%+ win rate, ~10 trades/day)
- Crypto market support (Binance/CoinGecko)
- Auto Scanner with popup notifications + sound alerts
- Multiple advanced strategies with high confluence analysis

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React + Tailwind CSS + lightweight-charts on port 3000
- **Database**: MongoDB (local)
- **LLM**: Emergent LLM Key — Claude Sonnet 4.5 (GPT analysis), GPT-4o (MiroFish)
- **Crypto Data**: CoinGecko API (free tier)

## Key Strategies (12 Total)
1. Falling Knife
2. Golden Setup
3. Reverse Swings (A & B)
4. Explosive Volume
5. AI Indicator Score
6. Godzilla TTE
7. DEMON Confluence
8. **SMC (Smart Money Concepts)** — 5 Phase
9. **AMDS-Hybrid** — 6 Step
10. **MiroFish (Swarm Intelligence)** — 5 AI Agents with Day Target + Swing Targets (GPT-4o)
11. **PAC + S&O Matrix** — 3-Module High Confluence (PAC Structure + S&O Confirmation + Oscillator Momentum)
12. GPT Deep Analysis (Claude)

## PAC + S&O Matrix Details (Feb 2026)
- Module 1 - PAC: BOS/CHoCH/CHoCH+ detection, Volumetric Order Blocks, Liquidity Sweeps, FVG, Premium/Discount zones
- Module 2 - S&O: Confirmation signals (Normal/Strong+), Neo Cloud trend, Smart Trail (ATR-based trailing stop), Trend Catcher (EMA50)
- Module 3 - Oscillator: Smart Money Flow (OBV), RSI Divergence detection, Momentum state (Overbought/Oversold/Strong)
- Signal fires when 2+ modules PASS with aligned direction
- Endpoints: POST /api/pac-so/analyze
- Integrated into Auto Scanner (11 strategies total)

## Features Implemented (Feb 2026)
- Stock News Popup: Auto-appears when stock selected, 10 latest news from yfinance
- MiroFish Strategy: GPT-4o powered 5-agent swarm with Day Target + T1/T2/T3
- MiroFish + PAC+S&O integrated into Auto Scanner
- News button in header to reopen news popup
- **Confluence Score Meter**: 0-100 visual bar in Auto Scanner; color-coded; WEAK/MODERATE/STRONG/VERY STRONG/EXTREME labels
- **1-Day Target**: ATR-based 1D Target in all 11 strategy signals (cyan badge)
- **QSC Search + Gann Chart**: Search bar in watchlist (filters existing + NSE yfinance live lookup), QSCChart with lightweight-charts candlestick (real OHLCV for Indian, synthetic for crypto/US), Gann Fan overlay, 5M/15M/1H/1D/1W timeframes, `/api/hybrid/chart/{symbol}` + `/api/hybrid/search` endpoints
- **QSC Search Fix (Feb 2026)**: Added missing `@hybrid_router.get("/assets")` decorator (was 404 → empty watchlist). Enhanced `/api/hybrid/search` to always do yfinance NSE/BSE lookup for unknown alphabetic queries (PAYTM, ETERNAL, ADANIENT etc.). Auto-registers discovered Indian stocks into `_H_NON_CRYPTO` so chart works on first click. Fixed dropdown clipping by removing `overflow-hidden` from watchlist card and adding z-index 60.
- **Mobile UX Polish (Feb 2026)**: Replaced bulky timeframe row on mobile with compact "1D ▾" toggle button (collapsible inline). Fixed layout calculation by switching from explicit `h-[calc(100vh-92px)]` to `h-screen + flex-1 min-h-0` so Order Flow panel always fits within viewport. Added `relative z-20` on Order Flow panel to prevent TradingView axis labels from overlapping the toggle bar.
- **Groww Trade API Integration (Feb 2026)**: Full integration with Groww Trade API via official `growwapi` Python SDK.
  - Backend: `/app/backend/groww_service.py` with auto-refreshing access token (uses API_KEY + APPROVAL_SECRET stored in backend/.env). Token lifecycle 13.8h, cached.
  - Endpoints: `/api/groww/status`, `/candles/{symbol}`, `/ltp`, `/ohlc/{symbol}`, `/holdings`, `/positions`, `/margin`, `/orders` (GET/POST), `/orders/{id}` (DELETE).
  - Frontend: Source toggle in ChartPanel (Y/G) — user can switch between Yahoo Finance and Groww live data per stock. New `GrowwTradeModal` for placing BUY/SELL MARKET/LIMIT/SL/SL_M orders with CNC/MIS/NRML products. New `GrowwPortfolio` left-tab showing live Holdings, Positions, Orders, and Margin (Available/Used).
- **Full Search Universe (Feb 2026)**: Replaced hardcoded 20-stock list with full Groww instrument universe (12k+ instruments). Loaded once from PUBLIC CSV (`https://growwapi-assets.groww.in/instruments/instrument.csv`, ~24MB, no auth required) and cached in-memory.
  - Includes: 30 indices (NIFTY 50, BANK NIFTY, SENSEX, FINNIFTY, all sector indices), 2508 NSE EQ stocks, 7226 BSE INE-prefix equities.
  - Search prioritization: exact match → prefix match → contains; indices first within each tier.
  - Index tickers map to yfinance equivalents (NIFTY→^NSEI, SENSEX→^BSESN, BANKNIFTY→^NSEBANK, etc.) so charts work with Yahoo source out-of-box.
  - UI: Each result shows colored badge (orange IDX / green NSE / purple BSE) + symbol + full name.

## Known Issues
- CoinGecko Rate Limits (429) - Free tier limitation, cache active

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto streaming
- P2: Confluence alerts (2+ strategies align trigger)
- P3: Multiple portfolio support
- P3: Email/Push notification system
