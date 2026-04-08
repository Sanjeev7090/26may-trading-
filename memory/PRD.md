# GANN TRADER - Product Requirements Document

## Original Problem Statement
Copy the complete `tuntun-scanner` GitHub repository (Gann Angles Trader app for NSE stocks) and make it editable with a fresh new design.

## Architecture
- **Frontend**: React.js with Tailwind CSS, lightweight-charts v4.2.1, @phosphor-icons/react, sonner (toasts)
- **Backend**: FastAPI (Python) with yfinance, nsepython, pandas, numpy
- **Database**: MongoDB via motor (async)
- **Design**: Custom dark theme with Chivo + IBM Plex Sans + JetBrains Mono fonts

## User Personas
- **Day Traders**: NSE/BSE stock traders using Gann angle analysis
- **Swing Traders**: Multi-timeframe analysis users
- **Technical Analysts**: Advanced strategy scanners (DEMON, Ghost Mode)

## Core Requirements (Static)
1. Stock Search (NSE stocks with .NS suffix)
2. Interactive Candlestick Chart with Gann Fan overlay
3. Multiple Timeframes (10M, 30M, 1H, 4H, 1D, 1W, 1M, 6M, 1Y)
4. Square of 9 Calculator (resistance/support)
5. NSE Open Interest Analysis
6. AI Trade Analysis (technical analysis based)
7. 8 Strategy Scanners: Falling Knife, Reverse Swings, Explosive Volume, Golden Setup, AI Indicator Score, Godzilla Setup, DEMON (7-strategy confluence), Ghost Mode (50-stock auto-scanner)

## What's Been Implemented (Jan 2026)
- Complete backend with all 15+ API endpoints
- Fresh dark UI design with 3-column layout (sidebar-chart-strategies)
- All 8 strategy scanners fully functional
- Ghost Mode auto-scanner with expandable results
- Chart with Gann Fan drawing, pivot selection, line extension controls
- Square of 9 calculator
- Tabbed right sidebar (STRATEGIES / GHOST / TOOLS)
- Testing: 100% pass rate (24/24 backend, all frontend)

## Prioritized Backlog
- **P0**: None (all core features implemented)
- **P1**: Real-time websocket price updates, portfolio tracking
- **P2**: Watchlist management, alert notifications, backtesting
- **P3**: Multi-exchange support (BSE), mobile responsive improvements

## Next Tasks
1. Add watchlist feature (save favorite stocks)
2. Add real-time price streaming via websockets
3. Enhanced AI analysis with Emergent LLM (GPT) integration for deeper trade reasoning
4. Backtest strategies against historical data
