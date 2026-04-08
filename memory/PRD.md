# GANN TRADER - Product Requirements Document

## Original Problem Statement
Copy the complete `tuntun-scanner` GitHub repository (Gann Angles Trader app for NSE stocks) and make it editable. Then add: Watchlist, Portfolio Tracker, Alert System, GPT Deep Analysis, Backtest Module, WebSocket streaming, and Mobile responsive improvements.

## Architecture
- **Frontend**: React.js with Tailwind CSS, lightweight-charts v4.2.1, @phosphor-icons/react, sonner (toasts)
- **Backend**: FastAPI (Python) with yfinance, nsepython, pandas, numpy, emergentintegrations (GPT)
- **Database**: MongoDB via motor (async) - Collections: watchlist, portfolio, alerts
- **Real-time**: WebSocket for price streaming
- **AI**: Emergent LLM Key with GPT-4.1 Mini for deep trade analysis
- **Design**: Custom dark "tactical command center" theme with Chivo + IBM Plex Sans + JetBrains Mono fonts

## User Personas
- **Day Traders**: NSE/BSE stock traders using Gann angle analysis
- **Swing Traders**: Multi-timeframe analysis users
- **Technical Analysts**: Advanced strategy scanners (DEMON, Ghost Mode)
- **Portfolio Managers**: Track holdings with live P&L

## Core Requirements (Static)
1. Stock Search (NSE stocks with .NS suffix)
2. Interactive Candlestick Chart with Gann Fan overlay
3. Multiple Timeframes (10M, 30M, 1H, 4H, 1D, 1W, 1M, 6M, 1Y)
4. Square of 9 Calculator (resistance/support)
5. NSE Open Interest Analysis
6. AI Trade Analysis (technical analysis based)
7. 8 Strategy Scanners: Falling Knife, Reverse Swings, Explosive Volume, Golden Setup, AI Indicator Score, Godzilla Setup, DEMON (7-strategy confluence), Ghost Mode (50-stock auto-scanner)

## What's Been Implemented

### Phase 1 (Jan 8, 2026) - Initial Copy + Fresh Design
- Complete backend with all 15+ API endpoints
- Fresh dark UI design with 3-column layout
- All 8 strategy scanners functional
- Ghost Mode auto-scanner
- Chart with Gann Fan drawing
- Testing: 100% pass (24/24 backend)

### Phase 2 (Jan 8, 2026) - Feature Expansion
- **Watchlist**: Add/remove stocks with live prices (MongoDB)
- **Portfolio Tracker**: Holdings with buy price, quantity, live P&L, summary stats
- **Alert System**: Price-based alerts (above/below), auto-check every 60s, DEMON signal alerts
- **GPT Deep Analysis**: Emergent LLM Key with GPT-4.1 Mini for SMC/pattern/key levels analysis
- **Backtest Module**: 5 strategies (Falling Knife, Golden Setup, Reverse Swings, Godzilla, DEMON), multiple periods (90D, 180D, 1Y, 2Y), win rate, max drawdown, trade history
- **WebSocket**: Real-time price streaming for subscribed tickers
- **Mobile Responsive**: 3-panel mobile layout (Menu/Chart/Strategies) with tab navigation
- **UI Improvements**: Left sidebar with 4 tabs (Search/Watchlist/Portfolio/Alerts), Right sidebar with 4 tabs (Strategies/Ghost/Backtest/Tools)
- Testing: 100% pass (45/45 backend, all frontend)

## Prioritized Backlog
- **P0**: None (all requested features implemented)
- **P1**: Push notifications for alerts, multi-stock chart comparison
- **P2**: Options chain visualizer, sector heatmap
- **P3**: Social sharing of trade setups, community signals

## Next Tasks
1. Options chain visual analyzer
2. Sector heatmap for NSE
3. Trade journal with notes
4. Multi-chart layout for comparing stocks
