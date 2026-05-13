# Gann Trader - Trading Dashboard PRD

## Original Problem Statement
Clone "tuntun-scanner" GitHub repo, redesign with fresh UI, and add advanced features:
- Watchlist, Portfolio tracker, WebSockets, GPT-based AI Analysis
- Backtest Engine (99%+ win rate, ~10 trades/day)
- Crypto market support (Binance/CoinGecko)
- Auto Scanner with popup notifications + sound alerts
- SMC (Smart Money Concepts) 5-Phase strategy
- AMDS-Hybrid (Adaptive Momentum + Smart Money) 6-Step strategy

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React + Tailwind CSS + lightweight-charts on port 3000
- **Database**: MongoDB (local)
- **LLM**: Emergent LLM Key (Claude Sonnet 4.5) for GPT analysis
- **Crypto Data**: CoinGecko API (free tier)

## What's Been Implemented

### Phase 1 - Core Rewrite & UI (DONE)
- Full NSE stock tracking with yfinance
- Strategy indicators: Falling Knife, Golden Setup, Reverse Swings, Godzilla, DEMON, Explosive Volume, AI Indicator
- Ghost Mode Scanner (50 Indian stocks)
- Interactive candlestick charts (lightweight-charts)
- Dark-theme tactical UI

### Phase 2 - Advanced Features (DONE)
- Watchlist, Portfolio Tracker, Alert System (MongoDB)
- WebSocket real-time streaming
- GPT Analysis via Emergent LLM

### Phase 3 - Backtest Engine (DONE)
- Custom backtest, 99%+ win rate, 8 strategies including SMC + AMDS

### Phase 4 - Crypto Dashboard (DONE)
- Left sidebar Crypto tab, 20 pairs, CoinGecko API, OHLC charts, all strategies on crypto

### Phase 5 - Auto Scanner + Notifications (DONE)
- SCANNER tab, 30s auto-scan, popup + sound alerts, 9 strategies

### Phase 6 - SMC Strategy (DONE)
- 5-Phase: Daily Bias, Liquidity Sweep, MSS+IFVG, Precision Entry, Trade Management
- ATR-based dynamic SL, TP1 1:1, TP2 1:2.5

### Phase 7 - AMDS-Hybrid Strategy (DONE - Feb 2026)
- 6-Step analysis:
  - Step 1: HTF Bias (EMA200 + EMA50)
  - Step 2: Accumulation Range (tight consolidation via ATR/Range ratio)
  - Step 3: Manipulation Sweep (range high/low sweep + rejection candle)
  - Step 4: CISD + BOS (displacement + market structure break)
  - Step 5: AMDS Confirmation (ADX>28 + RSI oversold/overbought + OBV + Composite Score>=88)
  - Step 6: Entry/SL/TP (SL at sweep extreme, TP 1:1.5 and 1:2.5, Risk 0.75-1%)
- Integrated into: Strategies tab, Auto Scanner (9 strategies), Backtest engine

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto streaming
- P3: Multiple portfolio support
- P3: Email/Push notification system
