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
- MiroFish Swarm Intelligence Strategy (multi-agent AI consensus)

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
8. **SMC (Smart Money Concepts)** — 5 Phase: Bias, Liquidity Sweep, MSS+IFVG, Precision Entry, Trade Management
9. **AMDS-Hybrid** — 6 Step: EMA200 Bias, Accumulation, Sweep, CISD+BOS, ADX/RSI/OBV Score, Entry/SL/TP
10. **MiroFish (Swarm Intelligence)** — 5 AI Agents: Momentum Shark, News Hawk, Contrarian Fox, Risk Owl, Pattern Tiger → Consensus Buy/Sell/Hold with Entry/SL/Targets

## Features Implemented (Feb 2026)
- Stock News Popup: Auto-appears when stock selected, shows 10 latest news from yfinance with title, summary, source, time, thumbnail
- MiroFish Strategy: GPT-4o powered 5-agent swarm analysis with consensus scoring, news sentiment, trade levels
- News button in header to reopen news popup anytime
- Endpoints: GET /api/news/{ticker}, POST /api/mirofish/analyze

## SMC/AMDS Optimizations (Feb 2026)
- Relaxed bias thresholds: 2 HH/HL enough (was 3-4)
- Wider liquidity proximity: 0.5-1% near PDH/PDL (was 0.2%)
- MSS fallback: price direction based weak MSS detection
- Precision entry: wick ratio 0.8x (was 1.5x), volume 0.8x avg (was 1.5x)
- AMDS ADX > 20 (was 28), RSI < 42/> 58 (was 32/68)
- Signal threshold: 2 PASS (was 3-4)
- Result: 3-7 signals per stock scan, easily 6-8+ daily alerts across watchlist

## Known Issues
- CoinGecko Rate Limits (429) - Free tier limitation, cache active

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto streaming
- P2: Confluence alerts (2+ strategies align trigger)
- P3: Multiple portfolio support
- P3: Email/Push notification system
