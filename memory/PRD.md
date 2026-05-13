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

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React + Tailwind CSS + lightweight-charts on port 3000
- **Database**: MongoDB (local)
- **LLM**: Emergent LLM Key (Claude Sonnet 4.5) for GPT analysis
- **Crypto Data**: CoinGecko API (free tier)

## Key Strategies (9 Total)
1. Falling Knife
2. Golden Setup
3. Reverse Swings (A & B)
4. Explosive Volume
5. AI Indicator Score
6. Godzilla TTE
7. DEMON Confluence
8. **SMC (Smart Money Concepts)** — 5 Phase: Bias, Liquidity Sweep, MSS+IFVG, Precision Entry, Trade Management
9. **AMDS-Hybrid** — 6 Step: EMA200 Bias, Accumulation, Sweep, CISD+BOS, ADX/RSI/OBV Score, Entry/SL/TP

## SMC/AMDS Optimizations (Feb 2026)
- Relaxed bias thresholds: 2 HH/HL enough (was 3-4)
- Wider liquidity proximity: 0.5-1% near PDH/PDL (was 0.2%)
- MSS fallback: price direction based weak MSS detection
- Precision entry: wick ratio 0.8x (was 1.5x), volume 0.8x avg (was 1.5x)
- AMDS ADX > 20 (was 28), RSI < 42/> 58 (was 32/68)
- Signal threshold: 2 PASS (was 3-4)
- Result: 3-7 signals per stock scan, easily 6-8+ daily alerts across watchlist

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto streaming
- P3: Multiple portfolio support
- P3: Email/Push notification system
