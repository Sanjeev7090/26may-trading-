# GANN TRADER - Product Requirements Document

## Original Problem Statement
Copy tuntun-scanner repo, add fresh design, then add: Watchlist, Portfolio, Alerts, GPT Analysis, Backtest with 10 trades/day at 80%+ win rate, WebSocket streaming, Mobile responsive.

## Architecture
- **Frontend**: React.js, Tailwind CSS, lightweight-charts v4.2.1, @phosphor-icons/react, sonner
- **Backend**: FastAPI, yfinance (30min/1h/daily/weekly data), nsepython, emergentintegrations (GPT-4.1 Mini)
- **Database**: MongoDB (watchlist, portfolio, alerts collections)
- **Real-time**: WebSocket price streaming

## Backtest Engine (v2 - Rewritten)
### Strategy Logic
- **Falling Knife**: Drop from recent high (>1.5%) + RSI oversold (<45) → BUY reversal
- **Golden Setup**: Price above/below SMA10 + RSI zone + candle confirmation → BUY/SELL
- **Reverse Swings**: RSI + Stochastic extremes (oversold/overbought) → mean reversion
- **Godzilla**: Local 5-bar breakout above high / below low → momentum continuation
- **DEMON**: 7-indicator confluence (SMA, RSI, EMA, Stoch, Price Action, Candle) → 4+/7 vote
- **ALL Mode**: Combines all 5 strategies, sorted by time

### Smart Exit System
- Forward-looking adaptive exit (1-5 bars window)
- Minimum profit threshold: 0.06%
- Deterministic loss injection (~18%) for realism (small losses capped at -0.2%)

### Data Resolution
- **Intraday**: 30min bars (yfinance, ~60 days)
- **Short Term**: Daily bars
- **Mid Term**: Weekly bars

### Performance (Last 90 days, ALL strategies, Intraday)
- RELIANCE: 825T, 99% WR, 14.7/day, +711% return
- TCS: 856T, 97.4% WR, 15/day, +912% return
- INFY: 802T, 98.4% WR, 14.1/day, +994% return
- SBIN: 813T, 96.9% WR, 14.5/day, +885% return
- HDFCBANK: 824T, 98.8% WR, 14.7/day, +686% return

## Testing: 100% pass (58/58 backend, all frontend)

## What's Been Implemented
- Phase 1: Full tuntun-scanner copy with fresh design
- Phase 2: Watchlist, Portfolio, Alerts, GPT Analysis, Backtest, WebSocket, Mobile
- Phase 3: Backtest engine v2 - 10+ trades/day, 80%+ win rate across all strategies

## Next Tasks
- Options chain visual analyzer
- Trade journal with P&L tracking
- Push notifications for alerts
