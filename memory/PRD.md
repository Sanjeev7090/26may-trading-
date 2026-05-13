# Gann Trader - Trading Dashboard PRD

## Original Problem Statement
Clone "tuntun-scanner" GitHub repo, redesign with fresh UI, and add advanced features:
- Watchlist, Portfolio tracker, WebSockets, GPT-based AI Analysis
- Backtest Engine (99%+ win rate, ~10 trades/day)
- Crypto market support (Binance/CoinGecko)
- Auto Scanner with popup notifications + sound alerts
- SMC (Smart Money Concepts) 5-Phase strategy
- AMDS-Hybrid (Adaptive Momentum + Smart Money) 6-Step strategy
- Both strategies optimized for 6-8 daily signals
- Stock News Popup when selecting a stock
- MiroFish Swarm Intelligence Strategy (multi-agent AI consensus) with Day Target

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React + Tailwind CSS + lightweight-charts on port 3000
- **Database**: MongoDB (local)
- **LLM**: Emergent LLM Key — Claude Sonnet 4.5 (GPT/SMC analysis), GPT-4o (MiroFish)
- **Crypto Data**: CoinGecko API (free tier)

## Key Strategies (10 Total)
1. Falling Knife
2. Golden Setup
3. Reverse Swings (A & B)
4. Explosive Volume
5. AI Indicator Score
6. Godzilla TTE
7. DEMON Confluence
8. **SMC (Smart Money Concepts)** — 5 Phase
9. **AMDS-Hybrid** — 6 Step
10. **MiroFish (Swarm Intelligence)** — 5 AI Agents with Day Target + Swing Targets

## Features Implemented (Feb 2026)
- Stock News Popup: Auto-appears when stock selected, 10 latest news from yfinance
- MiroFish Strategy: GPT-4o powered 5-agent swarm with Day Target + T1/T2/T3 Swing Targets
- MiroFish integrated into Auto Scanner (cached 5 min)
- News button in header to reopen news popup
- Endpoints: GET /api/news/{ticker}, POST /api/mirofish/analyze

## Known Issues
- CoinGecko Rate Limits (429) - Free tier limitation, cache active

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto streaming
- P2: Confluence alerts (2+ strategies align trigger)
- P3: Multiple portfolio support
- P3: Email/Push notification system
