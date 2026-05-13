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

## Known Issues
- CoinGecko Rate Limits (429) - Free tier limitation, cache active

## Backlog / Future Tasks
- P1: Live Paper Trading mode (virtual portfolio auto-execution)
- P2: Binance WebSocket for real-time crypto streaming
- P2: Confluence alerts (2+ strategies align trigger)
- P3: Multiple portfolio support
- P3: Email/Push notification system
