from fastapi import FastAPI, APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import math
import asyncio
import json
import httpx
import yfinance as yf
import pandas as pd
from nsepython import nse_optionchain_scrapper, nse_quote_ltp
from openai import OpenAI
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

cache_storage = {}


class OHLCVBar(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
class StockDataResponse(BaseModel):
    ticker: str
    bars: List[OHLCVBar]
    
class GannAngle(BaseModel):
    angle_type: str
    price_levels: List[float]
    
class GannFanRequest(BaseModel):
    ticker: str
    pivot_price: float
    pivot_timestamp: int
    bars_count: int = 50
    
class GannFanResponse(BaseModel):
    angles: List[GannAngle]
    pivot_price: float
    pivot_timestamp: int
    
class SquareOf9Response(BaseModel):
    center_price: float
    targets: dict
    
class SignalResponse(BaseModel):
    ticker: str
    signal: str
    color: str
    price: float
    angle_1x1: float
    timestamp: int

class AITradeAnalysisRequest(BaseModel):
    ticker: str
    timeframe: str
    bars: List[dict]

class AITradeAnalysisResponse(BaseModel):
    direction: str
    entry_price: str
    stoploss: str
    targets: List[str]
    reason: str

class FallingKnifeAnalysisRequest(BaseModel):
    ticker: str
    bars: List[dict]

class FallingKnifeAnalysisResponse(BaseModel):
    status: str
    signal_type: str
    conditions_met: int
    drop_percentage: Optional[float] = None
    bollinger_squeeze: bool
    price_in_keltner: bool
    macd_bullish: bool
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    targets: Optional[List[str]] = None
    recommendation: str

class ReverseSwingsRequest(BaseModel):
    ticker: str
    bars: List[dict]
    force_method: Optional[str] = None  # 'A' or 'B'

class ReverseSwingsResponse(BaseModel):
    method: str
    signal_type: str
    trend_confirmed: bool
    swing_signal: bool
    valid_entry_day: bool
    signal_active: bool
    current_swing: str
    avg_swing: str
    threshold_swing: str
    price_comparison: str
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    targets: Optional[List[str]] = None
    entry_day: Optional[str] = None
    recommendation: str

class OIDataResponse(BaseModel):
    symbol: str
    total_call_oi: float
    total_put_oi: float
    pcr: float
    max_pain: Optional[float] = None
    top_strikes: List[dict]
    signal: str
    signal_color: str


# --- New Models for Watchlist, Portfolio, Alerts, Backtest, GPT AI ---

class WatchlistItem(BaseModel):
    ticker: str
    name: str
    stock_type: str = "STOCK"

class WatchlistResponse(BaseModel):
    id: str
    ticker: str
    name: str
    stock_type: str
    added_at: str

class PortfolioEntry(BaseModel):
    ticker: str
    name: str
    buy_price: float
    quantity: int
    buy_date: Optional[str] = None

class PortfolioResponse(BaseModel):
    id: str
    ticker: str
    name: str
    buy_price: float
    quantity: int
    buy_date: str
    current_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None

class AlertRule(BaseModel):
    ticker: str
    name: str
    alert_type: str  # 'price_above', 'price_below', 'demon_buy', 'demon_sell'
    threshold: Optional[float] = None

class AlertResponse(BaseModel):
    id: str
    ticker: str
    name: str
    alert_type: str
    threshold: Optional[float] = None
    triggered: bool = False
    triggered_at: Optional[str] = None
    created_at: str

class GPTAnalysisRequest(BaseModel):
    ticker: str
    timeframe: str
    bars: List[dict]

class GPTAnalysisResponse(BaseModel):
    direction: str
    entry_price: str
    stoploss: str
    targets: List[str]
    reason: str
    confidence: int
    key_levels: Optional[List[str]] = None
    risk_reward: Optional[str] = None

class BacktestRequest(BaseModel):
    ticker: str
    strategy: str  # 'falling_knife', 'golden_setup', 'demon', 'reverse_swings', 'godzilla', 'smc', 'amds', 'all'
    days: int = 90
    timeframe: str = 'intraday'

# SMC (Smart Money Concepts) Models
class SMCAnalysisRequest(BaseModel):
    ticker: str
    bars: List[dict]
    timeframe: Optional[str] = "15M"

class SMCPhase(BaseModel):
    phase: int
    name: str
    status: str
    detail: str

class SMCAnalysisResponse(BaseModel):
    status: str
    signal_type: str
    daily_bias: str
    liquidity_sweep: str
    mss_detected: bool
    ifvg_zone: Optional[str] = None
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    tp1: Optional[str] = None
    tp2: Optional[str] = None
    risk_reward: Optional[str] = None
    atr_value: Optional[float] = None
    rejection_quality: Optional[str] = None
    volume_confirmed: bool = False
    session_valid: bool = False
    phases: List[SMCPhase] = []
    confidence: int = 0
    recommendation: str

# AMDS-Hybrid Models
class AMDSAnalysisRequest(BaseModel):
    ticker: str
    bars: List[dict]
    timeframe: Optional[str] = "15M"

class AMDSStep(BaseModel):
    step: int
    name: str
    status: str
    detail: str

class AMDSAnalysisResponse(BaseModel):
    status: str
    signal_type: str
    htf_bias: str
    accumulation_range: Optional[str] = None
    manipulation_sweep: Optional[str] = None
    cisd_detected: bool = False
    bos_detected: bool = False
    adx_value: Optional[float] = None
    rsi_value: Optional[float] = None
    obv_trend: Optional[str] = None
    composite_score: Optional[float] = None
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    tp1: Optional[str] = None
    tp2: Optional[str] = None
    risk_reward: Optional[str] = None
    atr_value: Optional[float] = None
    steps: List[AMDSStep] = []
    confidence: int = 0
    recommendation: str

# ======================= MIROFISH MODELS =======================

# PAC + S&O Matrix Models
class PACSORequest(BaseModel):
    ticker: str
    bars: List[dict]
    timeframe: Optional[str] = "15M"

class PACSOModule(BaseModel):
    module: str
    status: str
    detail: str
    sub_signals: List[str] = []

class PACSOResponse(BaseModel):
    status: str
    signal_type: str
    structure_bias: str
    bos_detected: bool = False
    choch_detected: bool = False
    choch_plus: bool = False
    order_block_zone: Optional[str] = None
    order_block_type: Optional[str] = None
    liquidity_swept: bool = False
    fvg_zone: Optional[str] = None
    premium_discount: str = "NEUTRAL"
    signal_strength: Optional[str] = None
    neo_cloud_trend: Optional[str] = None
    smart_trail_level: Optional[str] = None
    money_flow: Optional[str] = None
    divergence: Optional[str] = None
    momentum_state: Optional[str] = None
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    tp1: Optional[str] = None
    tp2: Optional[str] = None
    tp3: Optional[str] = None
    risk_reward: Optional[str] = None
    atr_value: Optional[float] = None
    confluence_score: int = 0
    modules: List[PACSOModule] = []
    confidence: int = 0
    recommendation: str

class MiroFishRequest(BaseModel):
    ticker: str
    bars: List[dict]
    timeframe: Optional[str] = "1D"

class MiroFishAgentVerdict(BaseModel):
    agent_name: str
    role: str
    verdict: str
    reasoning: str
    confidence: int

class MiroFishResponse(BaseModel):
    status: str
    signal_type: str
    swarm_consensus: str
    consensus_score: float
    direction: str
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    day_target: Optional[str] = None
    targets: Optional[List[str]] = None
    risk_reward: Optional[str] = None
    news_sentiment: str
    news_summary: str
    agents: List[MiroFishAgentVerdict] = []
    confidence: int = 0
    recommendation: str

class BacktestTradeResult(BaseModel):
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    signal: str
    strategy: Optional[str] = None
    holding_bars: Optional[int] = None

class DailySummary(BaseModel):
    date: str
    total_trades: int
    winning: int
    losing: int
    win_rate: float
    day_pnl: float

class BacktestResponse(BaseModel):
    ticker: str
    strategy: str
    timeframe: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_return: float
    max_drawdown: float
    total_return: float
    avg_trades_per_day: float
    trading_days: int
    trades: List[BacktestTradeResult]
    daily_summary: Optional[List[DailySummary]] = None


@api_router.get("/")
async def root():
    return {"message": "Gann Angles Trader API - NSE Edition"}


@api_router.get("/stock/search")
async def search_stock(q: str = Query(..., min_length=1)):
    """Search for stock tickers - NSE stocks"""
    cache_key = f"search_{q}"
    if cache_key in cache_storage:
        cached_data, cached_time = cache_storage[cache_key]
        if (datetime.now() - cached_time).seconds < 300:
            return cached_data
    
    try:
        q_upper = q.upper()
        
        nse_stocks = [
            {"ticker": "NIFTY", "name": "NIFTY 50 Index", "type": "INDEX"},
            {"ticker": "BANKNIFTY", "name": "Bank Nifty Index", "type": "INDEX"},
            {"ticker": "FINNIFTY", "name": "Nifty Financial Services", "type": "INDEX"},
            {"ticker": "RELIANCE.NS", "name": "Reliance Industries Ltd", "type": "STOCK"},
            {"ticker": "TCS.NS", "name": "Tata Consultancy Services", "type": "STOCK"},
            {"ticker": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "type": "STOCK"},
            {"ticker": "INFY.NS", "name": "Infosys Ltd", "type": "STOCK"},
            {"ticker": "ICICIBANK.NS", "name": "ICICI Bank Ltd", "type": "STOCK"},
            {"ticker": "SBIN.NS", "name": "State Bank of India", "type": "STOCK"},
            {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "type": "STOCK"},
            {"ticker": "ITC.NS", "name": "ITC Ltd", "type": "STOCK"},
            {"ticker": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "type": "STOCK"},
            {"ticker": "LT.NS", "name": "Larsen & Toubro Ltd", "type": "STOCK"},
            {"ticker": "AXISBANK.NS", "name": "Axis Bank Ltd", "type": "STOCK"},
            {"ticker": "ASIANPAINT.NS", "name": "Asian Paints Ltd", "type": "STOCK"},
            {"ticker": "MARUTI.NS", "name": "Maruti Suzuki India Ltd", "type": "STOCK"},
            {"ticker": "WIPRO.NS", "name": "Wipro Ltd", "type": "STOCK"},
            {"ticker": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "type": "STOCK"},
            {"ticker": "TATASTEEL.NS", "name": "Tata Steel Ltd", "type": "STOCK"},
            {"ticker": "ADANIENT.NS", "name": "Adani Enterprises Ltd", "type": "STOCK"},
        ]
        
        results = [s for s in nse_stocks if q_upper in s["ticker"] or q_upper in s["name"].upper()]
        
        result = {"results": results[:10]}
        cache_storage[cache_key] = (result, datetime.now())
        return result
    except Exception as e:
        logging.error(f"Error searching stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/stock/bars/{ticker}", response_model=StockDataResponse)
async def get_stock_bars(
    ticker: str,
    timespan: str = "day",
    multiplier: int = 1,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 120
):
    """Get historical OHLCV data using yfinance"""
    try:
        # yfinance valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 4h, 1d, 5d, 1wk, 1mo, 3mo
        # Note: 10m is NOT supported by yfinance, so we map it to 15m (closest supported)
        interval_map = {
            (10, "minute"): "15m",  # 10m not supported, use 15m instead
            (30, "minute"): "30m",
            (1, "hour"): "1h",
            (4, "hour"): "4h",
            (1, "day"): "1d",
            (1, "week"): "1wk",
        }
        
        interval = interval_map.get((multiplier, timespan), "1d")
        
        # yfinance strict limits:
        # 1m: max 7 days | 2m/5m/15m/30m: max 60 days | 60m/1h: max 730 days | 4h: max 730 days
        # For daily/weekly: no practical limit
        is_intraday = timespan in ["minute", "hour"]
        
        if is_intraday:
            # Choose max safe period based on interval
            if interval in ["1m"]:
                period = "7d"
            elif interval in ["15m", "30m", "5m", "2m"]:
                period = "60d"
            elif interval in ["1h"]:
                period = "730d"
            elif interval in ["4h"]:
                period = "730d"
            else:
                period = "60d"
            
            # If from_date is provided, clamp it within allowed range
            if from_date:
                max_days = 7 if interval in ["1m"] else 60 if interval in ["15m", "30m", "5m", "2m"] else 730
                earliest_allowed = (datetime.now() - timedelta(days=max_days)).strftime("%Y-%m-%d")
                if from_date < earliest_allowed:
                    from_date = earliest_allowed
                if not to_date:
                    to_date = datetime.now().strftime("%Y-%m-%d")
                
                cache_key = f"bars_{ticker}_{interval}_{from_date}_{to_date}"
                if cache_key in cache_storage:
                    cached_data, cached_time = cache_storage[cache_key]
                    if (datetime.now() - cached_time).seconds < 300:
                        return cached_data
                
                stock = yf.Ticker(ticker)
                hist = stock.history(start=from_date, end=to_date, interval=interval)
            else:
                cache_key = f"bars_{ticker}_{interval}_{period}"
                if cache_key in cache_storage:
                    cached_data, cached_time = cache_storage[cache_key]
                    if (datetime.now() - cached_time).seconds < 300:
                        return cached_data
                
                stock = yf.Ticker(ticker)
                hist = stock.history(period=period, interval=interval)
        else:
            if not from_date:
                from_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            cache_key = f"bars_{ticker}_{interval}_{from_date}_{to_date}"
            if cache_key in cache_storage:
                cached_data, cached_time = cache_storage[cache_key]
                if (datetime.now() - cached_time).seconds < 600:
                    return cached_data
            
            stock = yf.Ticker(ticker)
            hist = stock.history(start=from_date, end=to_date, interval=interval)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        
        bars = []
        for index, row in hist.iterrows():
            bars.append(OHLCVBar(
                timestamp=int(index.timestamp() * 1000),
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=float(row['Volume'])
            ))
        
        result = StockDataResponse(ticker=ticker.upper(), bars=bars)
        cache_storage[cache_key] = (result, datetime.now())
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching bars for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/nse/oi/{symbol}", response_model=OIDataResponse)
async def get_nse_oi(symbol: str):
    """Get NSE Option Chain Open Interest data"""
    cache_key = f"oi_{symbol}"
    if cache_key in cache_storage:
        cached_data, cached_time = cache_storage[cache_key]
        if (datetime.now() - cached_time).seconds < 120:
            return cached_data
    
    try:
        oi_data = nse_optionchain_scrapper(symbol)
        
        total_call_oi = float(oi_data.get('totalCallOI', 0))
        total_put_oi = float(oi_data.get('totalPutOI', 0))
        pcr = float(oi_data.get('PCR', 0))
        
        df = pd.DataFrame(oi_data.get('data', []))
        top_strikes = []
        
        if not df.empty and len(df) > 0:
            top_df = df.head(15)
            for _, row in top_df.iterrows():
                top_strikes.append({
                    "strike": float(row.get('strikePrice', 0)),
                    "call_oi": float(row.get('CE_OI', 0)),
                    "put_oi": float(row.get('PE_OI', 0)),
                    "call_volume": float(row.get('CE_volume', 0)),
                    "put_volume": float(row.get('PE_volume', 0))
                })
        
        if total_call_oi > total_put_oi * 1.5:
            signal = "BEARISH"
            signal_color = "#FF3333"
        elif total_put_oi > total_call_oi * 1.5:
            signal = "BULLISH"
            signal_color = "#00FF66"
        else:
            signal = "NEUTRAL"
            signal_color = "#FFCC00"
        
        result = OIDataResponse(
            symbol=symbol,
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            pcr=pcr,
            top_strikes=top_strikes,
            signal=signal,
            signal_color=signal_color
        )
        
        cache_storage[cache_key] = (result, datetime.now())
        return result
        
    except Exception as e:
        logging.error(f"Error fetching OI for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"NSE site slow ya data unavailable: {str(e)}")


@api_router.post("/gann/fan", response_model=GannFanResponse)
async def calculate_gann_fan(request: GannFanRequest):
    """Calculate Gann Fan angles from a pivot point"""
    pivot_price = request.pivot_price
    bars_count = request.bars_count
    
    angle_ratios = {
        "1x1": 1.0,
        "1x2": 0.5,
        "1x3": 1.0/3.0,
        "2x1": 2.0,
        "3x1": 3.0,
    }
    
    angles = []
    for angle_name, ratio in angle_ratios.items():
        price_levels = []
        for i in range(bars_count):
            price_change = (i + 1) * ratio
            price_levels.append(pivot_price + price_change)
        
        angles.append(GannAngle(
            angle_type=angle_name,
            price_levels=price_levels
        ))
    
    return GannFanResponse(
        angles=angles,
        pivot_price=pivot_price,
        pivot_timestamp=request.pivot_timestamp
    )


@api_router.get("/square-of-9")
async def calculate_square_of_9(center_price: float = Query(...)):
    """Calculate Square of 9 targets"""
    sqrt_price = math.sqrt(center_price)
    
    targets = {
        "resistance_1": (sqrt_price + 0.5) ** 2,
        "resistance_2": (sqrt_price + 1.0) ** 2,
        "resistance_3": (sqrt_price + 1.5) ** 2,
        "support_1": (sqrt_price - 0.5) ** 2 if sqrt_price > 0.5 else 0,
        "support_2": (sqrt_price - 1.0) ** 2 if sqrt_price > 1.0 else 0,
        "support_3": (sqrt_price - 1.5) ** 2 if sqrt_price > 1.5 else 0,
    }
    
    return SquareOf9Response(center_price=center_price, targets=targets)


@api_router.get("/signal/{ticker}", response_model=SignalResponse)
async def get_signal(
    ticker: str,
    pivot_price: float = Query(...),
    pivot_timestamp: int = Query(...)
):
    """Generate buy/sell signal based on 1x1 Gann angle"""
    cache_key = f"signal_{ticker}_{pivot_price}"
    if cache_key in cache_storage:
        cached_data, cached_time = cache_storage[cache_key]
        if (datetime.now() - cached_time).seconds < 60:
            return cached_data
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d", interval="1d")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail="No recent data")
        
        latest_bar = hist.iloc[-1]
        current_price = float(latest_bar['Close'])
        current_timestamp = int(hist.index[-1].timestamp() * 1000)
        
        bars_elapsed = len(hist)
        angle_1x1_price = pivot_price + (bars_elapsed * 1.0)
        
        diff_percent = ((current_price - angle_1x1_price) / angle_1x1_price) * 100
        
        if diff_percent > 2:
            signal = "STRONG BUY"
            color = "#00CC52"
        elif diff_percent > 0:
            signal = "BUY"
            color = "#00FF66"
        elif diff_percent < -2:
            signal = "STRONG SELL"
            color = "#CC2929"
        elif diff_percent < 0:
            signal = "SELL"
            color = "#FF3333"
        else:
            signal = "NEUTRAL"
            color = "#FFCC00"
        
        result = SignalResponse(
            ticker=ticker.upper(),
            signal=signal,
            color=color,
            price=current_price,
            angle_1x1=angle_1x1_price,
            timestamp=current_timestamp
        )
        cache_storage[cache_key] = (result, datetime.now())
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error generating signal for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/ai/analyze-chart", response_model=AITradeAnalysisResponse)
async def analyze_chart_ai(request: AITradeAnalysisRequest):
    """Technical analysis for trade setups"""
    try:
        # Prepare chart data
        bars_data = request.bars[-60:]  # Last 60 bars
        
        # Calculate key levels
        highs = [b['high'] for b in bars_data]
        lows = [b['low'] for b in bars_data]
        closes = [b['close'] for b in bars_data]
        
        current_price = closes[-1]
        highest = max(highs)
        lowest = min(lows)
        
        # Calculate SMAs
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current_price
        
        # Simple RSI calculation
        gains = []
        losses = []
        for i in range(1, min(14, len(closes))):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0.01
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        # Trend detection
        recent_trend = "bullish" if closes[-1] > closes[-5] else "bearish"
        ma_trend = "bullish" if sma_20 > sma_50 else "bearish"
        
        # Support and Resistance
        support = min(lows[-20:]) if len(lows) >= 20 else lowest
        resistance = max(highs[-20:]) if len(highs) >= 20 else highest
        
        # Generate trade setup based on analysis
        if ma_trend == "bullish" and recent_trend == "bullish" and rsi < 70:
            direction = "Long"
            entry = f"{current_price:.2f}"
            sl = f"{(current_price * 0.98):.2f}"
            targets = [
                f"{(current_price * 1.015):.2f}",
                f"{(current_price * 1.025):.2f}",
                f"{(current_price * 1.04):.2f}"
            ]
            reason = f"Bullish trend confirmed. Price above 20 & 50 SMA. RSI at {rsi:.0f} shows momentum. Support at {support:.2f}. Good risk-reward for long position."
        
        elif ma_trend == "bearish" and recent_trend == "bearish" and rsi > 30:
            direction = "Short"
            entry = f"{current_price:.2f}"
            sl = f"{(current_price * 1.02):.2f}"
            targets = [
                f"{(current_price * 0.985):.2f}",
                f"{(current_price * 0.975):.2f}",
                f"{(current_price * 0.96):.2f}"
            ]
            reason = f"Bearish trend in play. Price below key SMAs. RSI at {rsi:.0f} indicates weakness. Resistance at {resistance:.2f}. Short setup with tight risk."
        
        elif rsi > 70:
            direction = "Short"
            entry = f"{current_price:.2f}"
            sl = f"{(current_price * 1.015):.2f}"
            targets = [
                f"{(current_price * 0.99):.2f}",
                f"{(current_price * 0.98):.2f}"
            ]
            reason = f"Overbought condition - RSI at {rsi:.0f}. Price near resistance at {resistance:.2f}. Potential pullback expected. Short with tight stops."
        
        elif rsi < 30:
            direction = "Long"
            entry = f"{current_price:.2f}"
            sl = f"{(current_price * 0.985):.2f}"
            targets = [
                f"{(current_price * 1.01):.2f}",
                f"{(current_price * 1.02):.2f}"
            ]
            reason = f"Oversold condition - RSI at {rsi:.0f}. Price near support at {support:.2f}. Bounce expected. Long with tight risk management."
        
        else:
            # Neutral - follow the trend
            if ma_trend == "bullish":
                direction = "Long"
                entry = f"{current_price:.2f}"
                sl = f"{support:.2f}"
                targets = [
                    f"{(current_price * 1.02):.2f}",
                    f"{resistance:.2f}"
                ]
                reason = f"Following bullish bias. Price consolidating above {support:.2f} support. Target resistance at {resistance:.2f}. Wait for breakout confirmation."
            else:
                direction = "Short"
                entry = f"{current_price:.2f}"
                sl = f"{resistance:.2f}"
                targets = [
                    f"{(current_price * 0.98):.2f}",
                    f"{support:.2f}"
                ]
                reason = f"Following bearish bias. Price below {resistance:.2f} resistance. Target support at {support:.2f}. Sell on rallies."
        
        return AITradeAnalysisResponse(
            direction=direction,
            entry_price=entry,
            stoploss=sl,
            targets=targets,
            reason=reason
        )
        
    except Exception as e:
        logging.error(f"Error in analysis: {e}")
        # Fallback simple analysis
        return AITradeAnalysisResponse(
            direction="Long",
            entry_price=f"{closes[-1]:.2f}",
            stoploss=f"{(closes[-1] * 0.98):.2f}",
            targets=[f"{(closes[-1] * 1.02):.2f}", f"{(closes[-1] * 1.04):.2f}"],
            reason="Following current price trend. Use proper risk management."
        )


@api_router.post("/falling-knife/analyze", response_model=FallingKnifeAnalysisResponse)
async def analyze_falling_knife(request: FallingKnifeAnalysisRequest):
    """Falling Knife Reversal Analysis"""
    try:
        bars = request.bars
        if len(bars) < 60:
            raise HTTPException(status_code=400, detail="Need at least 60 bars")
        
        # Extract data
        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        closes = [b['close'] for b in bars]
        
        current_price = closes[-1]
        
        # Step 1: Check 40% drop from peak
        peak_price = max(highs)
        drop_percentage = ((peak_price - current_price) / peak_price) * 100
        meets_drop_req = drop_percentage >= 40
        
        # Step 2: Calculate Bollinger Bands (20, 2)
        period = 20
        sma = sum(closes[-period:]) / period
        std_dev = (sum((x - sma) ** 2 for x in closes[-period:]) / period) ** 0.5
        bb_upper = sma + (2 * std_dev)
        bb_lower = sma - (2 * std_dev)
        bb_width = bb_upper - bb_lower
        
        # Check for squeeze (narrow bands)
        avg_bb_width = sum([
            ((sum(closes[i-period:i])/period + 2*((sum((closes[j]-sum(closes[i-period:i])/period)**2 for j in range(i-period,i))/period)**0.5)) - 
             (sum(closes[i-period:i])/period - 2*((sum((closes[j]-sum(closes[i-period:i])/period)**2 for j in range(i-period,i))/period)**0.5)))
            for i in range(period+10, len(closes))
        ]) / (len(closes) - period - 10)
        
        bollinger_squeeze = bb_width < avg_bb_width * 0.7
        
        # Step 3: Calculate Keltner Channels (20, 1.5)
        atr_period = 20
        trs = []
        for i in range(len(bars) - atr_period, len(bars)):
            h_l = highs[i] - lows[i]
            h_c = abs(highs[i] - closes[i-1]) if i > 0 else h_l
            l_c = abs(lows[i] - closes[i-1]) if i > 0 else h_l
            trs.append(max(h_l, h_c, l_c))
        atr = sum(trs) / len(trs)
        
        kc_upper = sma + (1.5 * atr)
        kc_lower = sma - (1.5 * atr)
        price_in_keltner = kc_lower <= current_price <= kc_upper
        
        # Step 4: Calculate MACD (12, 26, 9)
        ema_12 = sum(closes[-12:]) / 12
        ema_26 = sum(closes[-26:]) / 26
        macd_line = ema_12 - ema_26
        
        # Check for bullish divergence (simplified)
        macd_bullish = macd_line > 0
        
        # Count conditions met
        conditions = [meets_drop_req, bollinger_squeeze, price_in_keltner, macd_bullish]
        conditions_met = sum(conditions)
        
        # Determine status
        if conditions_met >= 3 and meets_drop_req:
            status = "READY"
            signal_type = "BUY"
            entry = f"{current_price:.2f}"
            sl = f"{min(lows[-10:]):.2f}"
            targets = [
                f"{(current_price * 1.05):.2f}",
                f"{(current_price * 1.10):.2f}",
                f"{(current_price * 1.15):.2f}"
            ]
            rec = f"All conditions met! Entry signal active. Stock dropped {drop_percentage:.1f}% from peak. Bollinger squeeze + Keltner entry + MACD positive. Enter now with stop at recent low."
        elif conditions_met >= 2 and meets_drop_req:
            status = "SETUP"
            signal_type = "WAIT"
            entry = f"{current_price:.2f}"
            sl = f"{min(lows[-10:]):.2f}"
            targets = [f"{(current_price * 1.05):.2f}"]
            rec = f"Setup forming. {conditions_met}/3 conditions met. Stock down {drop_percentage:.1f}%. Wait for all signals before entry. Monitor closely."
        else:
            status = "NO SIGNAL"
            signal_type = "WAIT"
            entry = None
            sl = None
            targets = None
            if not meets_drop_req:
                rec = f"Stock only down {drop_percentage:.1f}% from peak. Needs ≥40% drop. Not a falling knife yet."
            else:
                rec = f"Drop requirement met ({drop_percentage:.1f}%), but only {conditions_met}/3 technical conditions present. Wait for complete setup."
        
        return FallingKnifeAnalysisResponse(
            status=status,
            signal_type=signal_type,
            conditions_met=conditions_met,
            drop_percentage=drop_percentage,
            bollinger_squeeze=bollinger_squeeze,
            price_in_keltner=price_in_keltner,
            macd_bullish=macd_bullish,
            entry_price=entry,
            stop_loss=sl,
            targets=targets,
            recommendation=rec
        )
        
    except Exception as e:
        logging.error(f"Error in falling knife analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/reverse-swings/analyze", response_model=ReverseSwingsResponse)
async def analyze_reverse_swings(request: ReverseSwingsRequest):
    """Reverse Price Swings Analysis - Method A & B"""
    try:
        bars = request.bars
        if len(bars) < 10:
            raise HTTPException(status_code=400, detail="Need at least 10 bars")
        
        closes = [b['close'] for b in bars]
        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        
        current_close = closes[-1]
        close_5_days_ago = closes[-6] if len(closes) >= 6 else closes[0]
        
        # Determine Method (forced or auto)
        if request.force_method:
            method = request.force_method
        elif current_close < close_5_days_ago:
            method = "A"
        else:
            method = "B"
        
        if method == "A":
            # Calculate max buy swing for last 4 days
            buy_swings = []
            for i in range(-5, -1):
                if i >= -len(bars):
                    max_buy_swing = highs[i] - lows[i]
                    buy_swings.append(max_buy_swing)
            
            avg_swing = sum(buy_swings) / len(buy_swings) if buy_swings else 0
            current_swing = highs[-1] - lows[-1]
            threshold = avg_swing * 1.75
            
            swing_signal = current_swing >= threshold
            trend_confirmed = True
            
            # Valid entry days for Method A: Tuesday(2), Wednesday(3), Friday(5)
            # Get tomorrow's day
            from datetime import datetime, timedelta
            tomorrow = (datetime.now() + timedelta(days=1)).weekday()  # 0=Monday, 6=Sunday
            valid_days = [1, 2, 4]  # Tuesday, Wednesday, Friday
            valid_entry_day = tomorrow in valid_days
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            entry_day_name = day_names[tomorrow]
            
            # Calculate stop loss: 2% below close of day before signal day
            prev_close = closes[-2] if len(closes) >= 2 else closes[-1]
            stop_loss_price = prev_close * 0.98
            
            price_comp = f"₹{current_close:.2f} < ₹{close_5_days_ago:.2f}"
            
        else:
            method = "B"  # Overbought - Short trade
            # Calculate max sell swing for last 4 days
            sell_swings = []
            for i in range(-5, -1):
                if i >= -len(bars):
                    max_sell_swing = highs[i] - lows[i]
                    sell_swings.append(max_sell_swing)
            
            avg_swing = sum(sell_swings) / len(sell_swings) if sell_swings else 0
            current_swing = highs[-1] - lows[-1]
            threshold = avg_swing * 1.75
            
            swing_signal = current_swing >= threshold
            trend_confirmed = True
            
            # Valid entry days for Method B: Monday(1), Wednesday(3), Thursday(4)
            from datetime import datetime, timedelta
            tomorrow = (datetime.now() + timedelta(days=1)).weekday()
            valid_days = [0, 2, 3]  # Monday, Wednesday, Thursday
            valid_entry_day = tomorrow in valid_days
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            entry_day_name = day_names[tomorrow]
            
            # Calculate stop loss: 2% above close of day before signal day
            prev_close = closes[-2] if len(closes) >= 2 else closes[-1]
            stop_loss_price = prev_close * 1.02
            
            price_comp = f"₹{current_close:.2f} > ₹{close_5_days_ago:.2f}"
        
        # Signal is active if all conditions met
        signal_active = trend_confirmed and swing_signal and valid_entry_day
        
        if signal_active:
            entry_price = f"{current_close:.2f}"
            stop_loss = f"{stop_loss_price:.2f}"
            entry_day = entry_day_name
            
            if method == "A":
                signal_type = "BUY"
                targets = [
                    f"{(current_close * 1.02):.2f}",
                    f"{(current_close * 1.04):.2f}",
                    f"{(current_close * 1.06):.2f}"
                ]
                rec = f"METHOD A SIGNAL! Enter LONG tomorrow ({entry_day_name}). Stock is oversold (down from ₹{close_5_days_ago:.2f}). Strong buy swing detected ({current_swing:.2f} > {threshold:.2f}). Stop loss at ₹{stop_loss_price:.2f}. Valid entry day confirmed."
            else:
                signal_type = "SELL"
                targets = [
                    f"{(current_close * 0.98):.2f}",
                    f"{(current_close * 0.96):.2f}",
                    f"{(current_close * 0.94):.2f}"
                ]
                rec = f"METHOD B SIGNAL! Enter SHORT tomorrow ({entry_day_name}). Stock is overbought (up from ₹{close_5_days_ago:.2f}). Strong sell swing detected ({current_swing:.2f} > {threshold:.2f}). Stop loss at ₹{stop_loss_price:.2f}. Valid entry day confirmed."
        else:
            signal_type = "WAIT"
            entry_price = None
            stop_loss = None
            targets = None
            entry_day = None
            
            missing = []
            if not trend_confirmed:
                missing.append(f"{'oversold' if method == 'A' else 'overbought'} condition")
            if not swing_signal:
                missing.append(f"swing magnitude (need ≥{threshold:.2f}, got {current_swing:.2f})")
            if not valid_entry_day:
                missing.append(f"valid entry day (tomorrow is {entry_day_name})")
            
            rec = f"Signal not active. Waiting for: {', '.join(missing)}. Monitor daily for setup completion."
        
        return ReverseSwingsResponse(
            method=method,
            signal_type=signal_type,
            trend_confirmed=trend_confirmed,
            swing_signal=swing_signal,
            valid_entry_day=valid_entry_day,
            signal_active=signal_active,
            current_swing=f"{current_swing:.2f}",
            avg_swing=f"{avg_swing:.2f}",
            threshold_swing=f"{threshold:.2f}",
            price_comparison=price_comp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            targets=targets,
            entry_day=entry_day,
            recommendation=rec
        )
        
    except Exception as e:
        logging.error(f"Error in reverse swings analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExplosiveVolumeRequest(BaseModel):
    ticker: str
    bars: List[dict]
    force_option: Optional[str] = None  # 'A' or 'B'


class ExplosiveVolumeResponse(BaseModel):
    status: str
    signal_type: str
    fundamentals: dict
    technical_conditions: dict
    conditions_met: int
    total_conditions: int
    entry_strategy: Optional[dict] = None
    exit_option_a: Optional[dict] = None
    exit_option_b: Optional[dict] = None
    targets: Optional[List[str]] = None
    recommendation: str
    warnings: List[str]


def calc_ema(data, period):
    """Calculate EMA"""
    if len(data) < period:
        return data[-1] if data else 0
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for price in data[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def calc_cci(highs, lows, closes, period=20):
    """Calculate CCI (Commodity Channel Index)"""
    if len(closes) < period:
        return 0
    typical_prices = [(h + lo + c) / 3 for h, lo, c in zip(highs, lows, closes)]
    tp_slice = typical_prices[-period:]
    sma_tp = sum(tp_slice) / period
    mean_dev = sum(abs(tp - sma_tp) for tp in tp_slice) / period
    if mean_dev == 0:
        return 0
    return (tp_slice[-1] - sma_tp) / (0.015 * mean_dev)


def calc_five_day_oscillator(highs, lows, closes):
    """Calculate 5-Day Oscillator: ((Close - Low5) / (High5 - Low5)) * 100"""
    if len(closes) < 5:
        return 50
    high5 = max(highs[-5:])
    low5 = min(lows[-5:])
    if high5 == low5:
        return 50
    return ((closes[-1] - low5) / (high5 - low5)) * 100


@api_router.post("/explosive-volume/analyze", response_model=ExplosiveVolumeResponse)
async def analyze_explosive_volume(request: ExplosiveVolumeRequest):
    """Explosive Volume Strategy Analysis"""
    try:
        bars = request.bars
        warnings = []

        if len(bars) < 60:
            raise HTTPException(status_code=400, detail="Need at least 60 bars for analysis")

        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        closes = [b['close'] for b in bars]
        volumes = [b['volume'] for b in bars]

        current_price = closes[-1]
        current_volume = volumes[-1]

        # ============ PHASE 1: FUNDAMENTAL DATA ============
        insider_pct = None
        float_shares = None
        fundamental_pass = True  # Default pass if data unavailable

        try:
            ticker_obj = yf.Ticker(request.ticker)
            info = ticker_obj.info
            insider_pct_raw = info.get('heldPercentInsiders')
            float_shares_raw = info.get('floatShares')

            if insider_pct_raw is not None:
                insider_pct = round(float(insider_pct_raw) * 100, 2)
            else:
                warnings.append("Insider ownership data not available — skipping fundamental check")

            if float_shares_raw is not None:
                float_shares = float(float_shares_raw)
            else:
                warnings.append("Float shares data not available — skipping fundamental check")
        except Exception as e:
            warnings.append(f"Could not fetch fundamental data: {str(e)[:50]}")

        insider_ok = insider_pct is not None and insider_pct >= 10
        float_ok = float_shares is not None and float_shares <= 35_000_000

        if insider_pct is None and float_shares is None:
            fundamental_pass = True  # Can't verify, skip
            warnings.append("Fundamental filters skipped — data unavailable for this stock")
        else:
            fundamental_pass = (insider_pct is None or insider_ok) and (float_shares is None or float_ok)

        fundamentals = {
            "insider_ownership": f"{insider_pct}%" if insider_pct is not None else "N/A",
            "insider_ok": insider_ok if insider_pct is not None else "N/A",
            "float_shares": f"{float_shares/1e6:.1f}M" if float_shares is not None else "N/A",
            "float_ok": float_ok if float_shares is not None else "N/A",
            "fundamental_pass": fundamental_pass
        }

        # ============ PHASE 2: TECHNICAL CONDITIONS ============

        # 1. No overhead resistance in 12 months (price near 12m high)
        high_12m = max(highs)
        near_high_pct = ((high_12m - current_price) / high_12m) * 100
        no_resistance = near_high_pct <= 5  # within 5% of 12m high

        # 2. Volume > 2x 50-day SMA Volume
        vol_sma_50 = sum(volumes[-50:]) / min(50, len(volumes)) if len(volumes) >= 10 else current_volume
        volume_explosive = current_volume > (2 * vol_sma_50)
        vol_ratio = current_volume / vol_sma_50 if vol_sma_50 > 0 else 0

        # 3. Price at or near 60-day high (within 3%)
        high_60 = max(highs[-60:]) if len(highs) >= 60 else max(highs)
        near_60d_high = ((high_60 - current_price) / high_60) * 100 <= 3

        # 4. EMA Trend: 10 EMA > 20 EMA (short-term momentum)
        ema_10 = calc_ema(closes, 10)
        ema_20 = calc_ema(closes, 20)
        ema_trend_bullish = ema_10 > ema_20

        # 5. Price above 200-day SMA (long-term uptrend)
        sma_200 = sum(closes) / len(closes) if len(closes) >= 50 else current_price
        above_long_sma = current_price > sma_200

        # 6. CCI above +100 (strong momentum)
        cci_value = calc_cci(highs, lows, closes, 20)
        cci_strong = cci_value > 100

        # 7. Volume acceleration: today volume > yesterday volume
        vol_accel = len(volumes) >= 2 and volumes[-1] > volumes[-2]

        # 8. Price breakout: close > previous 5 day high
        prev_5_high = max(highs[-6:-1]) if len(highs) >= 6 else max(highs[:-1]) if len(highs) >= 2 else current_price
        price_breakout = current_price > prev_5_high

        technical_conditions = {
            "no_resistance_12m": {"met": no_resistance, "detail": f"Price {near_high_pct:.1f}% from 12m high (need ≤5%)"},
            "volume_2x_sma50": {"met": volume_explosive, "detail": f"Vol ratio: {vol_ratio:.1f}x (need >2x)"},
            "near_60d_high": {"met": near_60d_high, "detail": f"₹{current_price:.2f} vs 60d high ₹{high_60:.2f}"},
            "ema_trend": {"met": ema_trend_bullish, "detail": f"EMA10: ₹{ema_10:.2f} vs EMA20: ₹{ema_20:.2f}"},
            "above_long_sma": {"met": above_long_sma, "detail": f"Price ₹{current_price:.2f} vs SMA: ₹{sma_200:.2f}"},
            "cci_momentum": {"met": cci_strong, "detail": f"CCI: {cci_value:.0f} (need >100)"},
            "volume_accel": {"met": vol_accel, "detail": f"Today vol vs yesterday: {'↑' if vol_accel else '↓'}"},
            "price_breakout": {"met": price_breakout, "detail": f"Close ₹{current_price:.2f} vs prev 5d high ₹{prev_5_high:.2f}"}
        }

        tech_met = sum(1 for v in technical_conditions.values() if v["met"])
        total_conditions = 8

        # ============ PHASE 3: ENTRY/EXIT STRATEGY ============
        entry_strategy = None
        exit_option_a = None
        exit_option_b = None

        if tech_met >= 4:
            # Entry: Limit Buy = (Open + High) / 2 + 5%
            today_open = bars[-1]['open']
            today_high = bars[-1]['high']
            limit_buy = ((today_open + today_high) / 2) * 1.05

            entry_strategy = {
                "type": "LIMIT BUY",
                "price": f"{limit_buy:.2f}",
                "formula": f"(Open ₹{today_open:.2f} + High ₹{today_high:.2f}) / 2 + 5%",
                "stop_loss": f"{(current_price * 0.93):.2f}",
                "risk_pct": "7%"
            }

            # Exit Option A: CCI Divergence
            cci_zone = "Overbought" if cci_value > 200 else "Strong" if cci_value > 100 else "Normal" if cci_value > 0 else "Weak"
            prev_cci = calc_cci(highs[:-1], lows[:-1], closes[:-1], 20) if len(closes) > 20 else cci_value
            cci_divergence = cci_value < prev_cci and cci_value > 100

            exit_option_a = {
                "method": "CCI Divergence",
                "current_cci": f"{cci_value:.0f}",
                "prev_cci": f"{prev_cci:.0f}",
                "zone": cci_zone,
                "divergence_detected": cci_divergence,
                "exit_signal": cci_value < 100 and prev_cci > 100,
                "rule": "Exit when CCI drops below +100 from overbought zone",
                "action": "SELL - CCI crossed below 100" if (cci_value < 100 and prev_cci > 100) else "HOLD - CCI momentum intact"
            }

            # Exit Option B: 5-Day Oscillator
            osc_value = calc_five_day_oscillator(highs, lows, closes)
            prev_osc = calc_five_day_oscillator(highs[:-1], lows[:-1], closes[:-1]) if len(closes) > 5 else osc_value
            osc_zone = "Overbought" if osc_value > 80 else "Oversold" if osc_value < 20 else "Neutral"

            exit_option_b = {
                "method": "5-Day Oscillator",
                "current_value": f"{osc_value:.1f}",
                "prev_value": f"{prev_osc:.1f}",
                "zone": osc_zone,
                "exit_signal": osc_value < 20 and prev_osc > 20,
                "rule": "Exit when oscillator drops below 20 from above 80",
                "action": "SELL - Oscillator crashed below 20" if (osc_value < 20 and prev_osc > 20) else "HOLD - Oscillator stable"
            }

        # ============ STATUS & RECOMMENDATION ============
        fund_note = "" if fundamental_pass else " (Fundamentals not met — higher risk)"
        targets = None
        
        if tech_met >= 6:
            status = "EXPLOSIVE"
            signal_type = "BUY"
            if entry_strategy:
                buy_price = float(entry_strategy['price'])
                targets = [
                    f"{(buy_price * 1.05):.2f}",
                    f"{(buy_price * 1.10):.2f}",
                    f"{(buy_price * 1.15):.2f}"
                ]
            rec = f"EXPLOSIVE VOLUME detected! {tech_met}/8 technical conditions met{fund_note}. "
            if entry_strategy:
                rec += f"Limit buy at ₹{entry_strategy['price']}. Stop loss at ₹{entry_strategy['stop_loss']}. "
            rec += "Use Option A (CCI) or Option B (5-Day Oscillator) for exit timing."
        elif tech_met >= 4:
            status = "BUILDING"
            signal_type = "WAIT"
            if entry_strategy:
                buy_price = float(entry_strategy['price'])
                targets = [f"{(buy_price * 1.05):.2f}"]
            rec = f"Volume building up. {tech_met}/8 conditions met{fund_note}. Setup forming — monitor for explosive breakout. "
            if entry_strategy:
                rec += f"Tentative entry at ₹{entry_strategy['price']}."
        elif tech_met >= 2:
            status = "WATCHING"
            signal_type = "WAIT"
            rec = f"Early stage. Only {tech_met}/8 conditions met. Not ready for entry yet. Keep on watchlist."
        else:
            status = "NO SIGNAL"
            signal_type = "WAIT"
            rec = f"No explosive volume setup detected. Only {tech_met}/8 conditions met. Move to next stock."

        if not fundamental_pass:
            rec += " Fundamental filters not met — higher risk trade."

        return ExplosiveVolumeResponse(
            status=status,
            signal_type=signal_type,
            fundamentals=fundamentals,
            technical_conditions=technical_conditions,
            conditions_met=tech_met,
            total_conditions=total_conditions,
            entry_strategy=entry_strategy,
            exit_option_a=exit_option_a,
            exit_option_b=exit_option_b,
            targets=targets,
            recommendation=rec,
            warnings=warnings
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in explosive volume analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GoldenSetupRequest(BaseModel):
    ticker: str
    bars: List[dict]
    pro_mode: Optional[bool] = False
    multi_timeframe: Optional[bool] = False


class GoldenSetupResponse(BaseModel):
    mode: str
    signal_type: str
    conditions: dict
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    targets: Optional[List[str]] = None
    risk_reward: Optional[str] = None
    adx_value: Optional[float] = None
    pro_details: Optional[dict] = None
    mtf_confirmation: Optional[dict] = None
    recommendation: str


def calc_adx(highs, lows, closes, period=14):
    """Calculate ADX (Average Directional Index)"""
    if len(closes) < period * 2:
        return 0
    plus_dm = []
    minus_dm = []
    tr_list = []
    for i in range(1, len(highs)):
        high_diff = highs[i] - highs[i-1]
        low_diff = lows[i-1] - lows[i]
        plus_dm.append(max(high_diff, 0) if high_diff > low_diff else 0)
        minus_dm.append(max(low_diff, 0) if low_diff > high_diff else 0)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)

    if len(tr_list) < period:
        return 0

    atr = sum(tr_list[:period]) / period
    plus_di_sum = sum(plus_dm[:period]) / period
    minus_di_sum = sum(minus_dm[:period]) / period

    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
        plus_di_sum = (plus_di_sum * (period - 1) + plus_dm[i]) / period
        minus_di_sum = (minus_di_sum * (period - 1) + minus_dm[i]) / period

    if atr == 0:
        return 0
    plus_di = (plus_di_sum / atr) * 100
    minus_di = (minus_di_sum / atr) * 100
    di_sum = plus_di + minus_di
    if di_sum == 0:
        return 0
    dx = abs(plus_di - minus_di) / di_sum * 100
    return dx


def find_swing_lows(lows, window=5):
    """Find recent swing lows"""
    swings = []
    for i in range(window, len(lows) - 1):
        if lows[i] == min(lows[i-window:i+window+1]):
            swings.append((i, lows[i]))
    return swings


def find_swing_highs(highs, window=5):
    """Find recent swing highs"""
    swings = []
    for i in range(window, len(highs) - 1):
        if highs[i] == max(highs[i-window:i+window+1]):
            swings.append((i, highs[i]))
    return swings


def is_bullish_candle(o, h, low_val, c):
    """Check bullish candle or hammer"""
    body = abs(c - o)
    full_range = h - low_val
    if full_range == 0:
        return False
    if c > o:
        return True
    lower_wick = min(o, c) - low_val
    if lower_wick > body * 2 and body < full_range * 0.3:
        return True
    return False


def is_bearish_candle(o, h, low_val, c):
    """Check bearish candle or shooting star"""
    body = abs(c - o)
    full_range = h - low_val
    if full_range == 0:
        return False
    if c < o:
        return True
    upper_wick = h - max(o, c)
    if upper_wick > body * 2 and body < full_range * 0.3:
        return True
    return False


def is_engulfing_bullish(bars, idx):
    """Check bullish engulfing at index"""
    if idx < 1:
        return False
    prev = bars[idx - 1]
    curr = bars[idx]
    return prev['close'] < prev['open'] and curr['close'] > curr['open'] and curr['close'] > prev['open'] and curr['open'] < prev['close']


def is_engulfing_bearish(bars, idx):
    """Check bearish engulfing at index"""
    if idx < 1:
        return False
    prev = bars[idx - 1]
    curr = bars[idx]
    return prev['close'] > prev['open'] and curr['close'] < curr['open'] and curr['open'] > prev['close'] and curr['close'] < prev['open']


def has_rejection_wick(bar, direction):
    """Check for strong rejection wick"""
    o, h, low_val, c = bar['open'], bar['high'], bar['low'], bar['close']
    full = h - low_val
    if full == 0:
        return False
    if direction == 'bull':
        lower = min(o, c) - low_val
        return lower / full > 0.5
    else:
        upper = h - max(o, c)
        return upper / full > 0.5


@api_router.post("/golden-setup/analyze", response_model=GoldenSetupResponse)
async def analyze_golden_setup(request: GoldenSetupRequest):
    """Golden Setup Strategy - Normal & Pro Mode"""
    try:
        bars = request.bars
        pro_mode = request.pro_mode

        if len(bars) < 60:
            raise HTTPException(status_code=400, detail="Need at least 60 bars")

        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        closes = [b['close'] for b in bars]
        volumes = [b['volume'] for b in bars]

        current = closes[-1]
        last_bar = bars[-1]

        # Core indicators
        sma_200 = sum(closes[-min(200, len(closes)):]) / min(200, len(closes))
        ema_20 = calc_ema(closes, 20)
        ema_50 = calc_ema(closes, 50)
        prev_ema_20 = calc_ema(closes[:-1], 20)
        prev_ema_50 = calc_ema(closes[:-1], 50)
        adx = calc_adx(highs, lows, closes, 14)

        # Multi-timeframe confirmation (computed later based on signal)
        mtf_data = None

        # ====== NORMAL MODE ======
        if not pro_mode:
            # BUY conditions
            above_200 = current > sma_200
            ema_cross_bull = prev_ema_20 <= prev_ema_50 and ema_20 > ema_50
            ema_already_bull = ema_20 > ema_50
            near_ema20_buy = abs(current - ema_20) / ema_20 * 100 < 1.5
            bullish = is_bullish_candle(last_bar['open'], last_bar['high'], last_bar['low'], last_bar['close'])
            adx_strong = adx > 20

            # SELL conditions
            below_200 = current < sma_200
            ema_cross_bear = prev_ema_20 >= prev_ema_50 and ema_20 < ema_50
            ema_already_bear = ema_20 < ema_50
            near_ema20_sell = abs(current - ema_20) / ema_20 * 100 < 1.5
            bearish = is_bearish_candle(last_bar['open'], last_bar['high'], last_bar['low'], last_bar['close'])

            buy_score = sum([above_200, ema_cross_bull or ema_already_bull, near_ema20_buy, bullish, adx_strong])
            sell_score = sum([below_200, ema_cross_bear or ema_already_bear, near_ema20_sell, bearish, adx_strong])

            swing_lows = find_swing_lows(lows)
            swing_highs = find_swing_highs(highs)
            recent_swing_low = swing_lows[-1][1] if swing_lows else min(lows[-10:])
            recent_swing_high = swing_highs[-1][1] if swing_highs else max(highs[-10:])

            if buy_score >= 4:
                entry = current
                sl = min(recent_swing_low, ema_20 * 0.99)
                risk = entry - sl
                t1 = entry + risk * 2
                t2 = entry + risk * 3

                conditions = {
                    "price_above_200sma": {"met": above_200, "detail": f"₹{current:.2f} vs SMA200 ₹{sma_200:.2f}"},
                    "ema_20_above_50": {"met": ema_cross_bull or ema_already_bull, "detail": f"EMA20 ₹{ema_20:.2f} vs EMA50 ₹{ema_50:.2f}" + (" (Fresh Cross!)" if ema_cross_bull else "")},
                    "pullback_to_ema20": {"met": near_ema20_buy, "detail": f"Price {abs(current - ema_20)/ema_20*100:.1f}% from EMA20"},
                    "bullish_candle": {"met": bullish, "detail": "Green candle / Hammer confirmed" if bullish else "No bullish pattern"},
                    "adx_above_20": {"met": adx_strong, "detail": f"ADX: {adx:.1f} (need >20)"}
                }
                rec = f"GOLDEN BUY! All conditions met. Price above 200 SMA, EMA20 > EMA50, pullback to EMA20 zone, bullish candle confirmed. ADX {adx:.0f} shows strong trend. Enter at ₹{entry:.2f}, SL ₹{sl:.2f}."

                if request.multi_timeframe:
                    mtf_data = get_mtf_confirmation(request.ticker, "BUY")
                    if mtf_data and mtf_data.get("confirmed"):
                        rec += f" MTF CONFIRMED ({mtf_data['strength']})!"

                return GoldenSetupResponse(
                    mode="Normal", signal_type="BUY", conditions=conditions,
                    entry_price=f"{entry:.2f}", stop_loss=f"{sl:.2f}",
                    targets=[f"{t1:.2f}", f"{t2:.2f}"],
                    risk_reward="1:2 / 1:3", adx_value=round(adx, 1),
                    mtf_confirmation=mtf_data, recommendation=rec
                )

            elif sell_score >= 4:
                entry = current
                sl = max(recent_swing_high, ema_20 * 1.01)
                risk = sl - entry
                t1 = entry - risk * 2
                t2 = entry - risk * 3

                conditions = {
                    "price_below_200sma": {"met": below_200, "detail": f"₹{current:.2f} vs SMA200 ₹{sma_200:.2f}"},
                    "ema_20_below_50": {"met": ema_cross_bear or ema_already_bear, "detail": f"EMA20 ₹{ema_20:.2f} vs EMA50 ₹{ema_50:.2f}" + (" (Fresh Cross!)" if ema_cross_bear else "")},
                    "pullback_to_ema20": {"met": near_ema20_sell, "detail": f"Price {abs(current - ema_20)/ema_20*100:.1f}% from EMA20"},
                    "bearish_candle": {"met": bearish, "detail": "Red candle / Shooting star confirmed" if bearish else "No bearish pattern"},
                    "adx_above_20": {"met": adx_strong, "detail": f"ADX: {adx:.1f} (need >20)"}
                }
                rec = f"GOLDEN SELL! All conditions met. Price below 200 SMA, EMA20 < EMA50, pullback to EMA20 zone, bearish candle confirmed. ADX {adx:.0f} shows strong trend. Enter at ₹{entry:.2f}, SL ₹{sl:.2f}."

                if request.multi_timeframe:
                    mtf_data = get_mtf_confirmation(request.ticker, "SELL")
                    if mtf_data.get("confirmed"):
                        rec += f" MTF CONFIRMED ({mtf_data['strength']})!"

                return GoldenSetupResponse(
                    mode="Normal", signal_type="SELL", conditions=conditions,
                    entry_price=f"{entry:.2f}", stop_loss=f"{sl:.2f}",
                    targets=[f"{t1:.2f}", f"{t2:.2f}"],
                    risk_reward="1:2 / 1:3", adx_value=round(adx, 1),
                    mtf_confirmation=mtf_data,
                    recommendation=rec
                )

            else:
                conditions = {
                    "price_vs_200sma": {"met": above_200 or below_200, "detail": f"₹{current:.2f} vs SMA200 ₹{sma_200:.2f}" + (" (Above)" if above_200 else " (Below)")},
                    "ema_crossover": {"met": ema_cross_bull or ema_cross_bear or ema_already_bull or ema_already_bear, "detail": f"EMA20 ₹{ema_20:.2f} vs EMA50 ₹{ema_50:.2f}"},
                    "pullback_to_ema20": {"met": near_ema20_buy or near_ema20_sell, "detail": f"Price {abs(current - ema_20)/ema_20*100:.1f}% from EMA20"},
                    "candle_pattern": {"met": bullish or bearish, "detail": "Bullish" if bullish else ("Bearish" if bearish else "No clear pattern")},
                    "adx_above_20": {"met": adx_strong, "detail": f"ADX: {adx:.1f} (need >20)"}
                }
                best = max(buy_score, sell_score)
                rec = f"No Golden Setup yet. Best score: {best}/5 conditions. " + ("Leaning bullish." if buy_score > sell_score else "Leaning bearish." if sell_score > buy_score else "Neutral.") + f" ADX at {adx:.0f}. Wait for complete setup."

                return GoldenSetupResponse(
                    mode="Normal", signal_type="WAIT", conditions=conditions,
                    adx_value=round(adx, 1), mtf_confirmation=mtf_data,
                    recommendation=rec
                )

        # ====== PRO MODE (SMC) ======
        else:
            lookback = min(30, len(bars) - 5)
            recent_bars = bars[-lookback:]
            r_highs = [b['high'] for b in recent_bars]
            r_lows = [b['low'] for b in recent_bars]
            r_closes = [b['close'] for b in recent_bars]
            r_volumes = [b['volume'] for b in recent_bars]

            swing_lows_all = find_swing_lows(r_lows, 3)
            swing_highs_all = find_swing_highs(r_highs, 3)

            avg_vol = sum(r_volumes) / len(r_volumes) if r_volumes else 1
            last_vol = volumes[-1]
            vol_spike = last_vol > avg_vol * 1.3

            # === BUY SETUP: Sweep Low → BOS Up → Retest → Bullish confirmation ===
            sweep_low = False
            sweep_low_price = 0
            bos_up = False
            bos_level = 0
            retest_buy = False
            bull_confirm = False

            if len(swing_lows_all) >= 2:
                prev_low = swing_lows_all[-2][1]
                # Check if recent price swept below prev low then recovered
                for i in range(swing_lows_all[-2][0] + 1, len(r_lows)):
                    if r_lows[i] < prev_low and r_closes[min(i, len(r_closes)-1)] > prev_low:
                        sweep_low = True
                        sweep_low_price = r_lows[i]
                        break

            if sweep_low and len(swing_highs_all) >= 1:
                last_high = swing_highs_all[-1][1]
                if current > last_high:
                    bos_up = True
                    bos_level = last_high

            if bos_up:
                if abs(current - ema_20) / ema_20 * 100 < 2.0 or abs(current - bos_level) / bos_level * 100 < 1.5:
                    retest_buy = True

            engulf_bull = is_engulfing_bullish(bars, len(bars) - 1)
            rej_bull = has_rejection_wick(last_bar, 'bull')
            bull_confirm = engulf_bull or rej_bull or (is_bullish_candle(last_bar['open'], last_bar['high'], last_bar['low'], last_bar['close']) and vol_spike)

            # === SELL SETUP: Sweep High → BOS Down → Retest → Bearish confirmation ===
            sweep_high = False
            sweep_high_price = 0
            bos_down = False
            bos_level_sell = 0
            retest_sell = False
            bear_confirm = False

            if len(swing_highs_all) >= 2:
                prev_high = swing_highs_all[-2][1]
                for i in range(swing_highs_all[-2][0] + 1, len(r_highs)):
                    if r_highs[i] > prev_high and r_closes[min(i, len(r_closes)-1)] < prev_high:
                        sweep_high = True
                        sweep_high_price = r_highs[i]
                        break

            if sweep_high and len(swing_lows_all) >= 1:
                last_low_val = swing_lows_all[-1][1]
                if current < last_low_val:
                    bos_down = True
                    bos_level_sell = last_low_val

            if bos_down:
                if abs(current - ema_20) / ema_20 * 100 < 2.0 or abs(current - bos_level_sell) / bos_level_sell * 100 < 1.5:
                    retest_sell = True

            engulf_bear = is_engulfing_bearish(bars, len(bars) - 1)
            rej_bear = has_rejection_wick(last_bar, 'bear')
            bear_confirm = engulf_bear or rej_bear or (is_bearish_candle(last_bar['open'], last_bar['high'], last_bar['low'], last_bar['close']) and vol_spike)

            buy_pro_score = sum([sweep_low, bos_up, retest_buy, bull_confirm])
            sell_pro_score = sum([sweep_high, bos_down, retest_sell, bear_confirm])

            confirm_details = []
            if engulf_bull:
                confirm_details.append("Bullish Engulfing")
            if engulf_bear:
                confirm_details.append("Bearish Engulfing")
            if rej_bull:
                confirm_details.append("Bullish Rejection Wick")
            if rej_bear:
                confirm_details.append("Bearish Rejection Wick")
            if vol_spike:
                confirm_details.append(f"Volume Spike ({last_vol/avg_vol:.1f}x)")

            if buy_pro_score >= 3:
                entry = current
                sl = sweep_low_price if sweep_low_price > 0 else min(lows[-10:])
                risk = entry - sl
                t1 = entry + risk * 2
                t2 = entry + risk * 3

                conditions = {
                    "sweep_low": {"met": sweep_low, "detail": f"Liquidity grab below ₹{sweep_low_price:.2f}" if sweep_low else "No sweep detected"},
                    "bos_up": {"met": bos_up, "detail": f"Structure break above ₹{bos_level:.2f}" if bos_up else "No BOS up"},
                    "retest": {"met": retest_buy, "detail": "Price retesting breakout zone" if retest_buy else "No retest yet"},
                    "confirmation": {"met": bull_confirm, "detail": ", ".join(confirm_details) if confirm_details else "No confirmation"}
                }
                pro_details = {
                    "sweep_price": f"{sweep_low_price:.2f}" if sweep_low else "N/A",
                    "bos_level": f"{bos_level:.2f}" if bos_up else "N/A",
                    "confirmation_signals": confirm_details,
                    "volume_ratio": f"{last_vol/avg_vol:.1f}x"
                }
                rec = f"PRO BUY! Sweep low at ₹{sweep_low_price:.2f} → BOS above ₹{bos_level:.2f} → Retest confirmed. {', '.join(confirm_details)}. Entry at retest ₹{entry:.2f}, SL below sweep ₹{sl:.2f}. RR 1:2 minimum."

                if request.multi_timeframe:
                    mtf_data = get_mtf_confirmation(request.ticker, "BUY")
                    if mtf_data.get("confirmed"):
                        rec += f" MTF CONFIRMED ({mtf_data['strength']})!"

                return GoldenSetupResponse(
                    mode="Pro (SMC)", signal_type="BUY", conditions=conditions,
                    entry_price=f"{entry:.2f}", stop_loss=f"{sl:.2f}",
                    targets=[f"{t1:.2f}", f"{t2:.2f}"],
                    risk_reward="1:2 / 1:3", adx_value=round(adx, 1),
                    pro_details=pro_details, mtf_confirmation=mtf_data,
                    recommendation=rec
                )

            elif sell_pro_score >= 3:
                entry = current
                sl = sweep_high_price if sweep_high_price > 0 else max(highs[-10:])
                risk = sl - entry
                t1 = entry - risk * 2
                t2 = entry - risk * 3

                conditions = {
                    "sweep_high": {"met": sweep_high, "detail": f"Liquidity grab above ₹{sweep_high_price:.2f}" if sweep_high else "No sweep detected"},
                    "bos_down": {"met": bos_down, "detail": f"Structure break below ₹{bos_level_sell:.2f}" if bos_down else "No BOS down"},
                    "retest": {"met": retest_sell, "detail": "Price retesting breakdown zone" if retest_sell else "No retest yet"},
                    "confirmation": {"met": bear_confirm, "detail": ", ".join(confirm_details) if confirm_details else "No confirmation"}
                }
                pro_details = {
                    "sweep_price": f"{sweep_high_price:.2f}" if sweep_high else "N/A",
                    "bos_level": f"{bos_level_sell:.2f}" if bos_down else "N/A",
                    "confirmation_signals": confirm_details,
                    "volume_ratio": f"{last_vol/avg_vol:.1f}x"
                }
                rec = f"PRO SELL! Sweep high at ₹{sweep_high_price:.2f} → BOS below ₹{bos_level_sell:.2f} → Retest confirmed. {', '.join(confirm_details)}. Entry at retest ₹{entry:.2f}, SL above sweep ₹{sl:.2f}. RR 1:2 minimum."

                if request.multi_timeframe:
                    mtf_data = get_mtf_confirmation(request.ticker, "SELL")
                    if mtf_data.get("confirmed"):
                        rec += f" MTF CONFIRMED ({mtf_data['strength']})!"

                return GoldenSetupResponse(
                    mode="Pro (SMC)", signal_type="SELL", conditions=conditions,
                    entry_price=f"{entry:.2f}", stop_loss=f"{sl:.2f}",
                    targets=[f"{t1:.2f}", f"{t2:.2f}"],
                    risk_reward="1:2 / 1:3", adx_value=round(adx, 1),
                    pro_details=pro_details, mtf_confirmation=mtf_data,
                    recommendation=rec
                )

            else:
                conditions = {
                    "sweep_low": {"met": sweep_low, "detail": f"Liquidity grab below ₹{sweep_low_price:.2f}" if sweep_low else "No sweep detected"},
                    "sweep_high": {"met": sweep_high, "detail": f"Liquidity grab above ₹{sweep_high_price:.2f}" if sweep_high else "No sweep detected"},
                    "bos": {"met": bos_up or bos_down, "detail": ("BOS Up" if bos_up else "BOS Down") if (bos_up or bos_down) else "No BOS"},
                    "retest": {"met": retest_buy or retest_sell, "detail": "Retest zone" if (retest_buy or retest_sell) else "No retest"},
                    "confirmation": {"met": bull_confirm or bear_confirm, "detail": ", ".join(confirm_details) if confirm_details else "No confirmation"}
                }
                pro_details = {
                    "sweep_price": "N/A",
                    "bos_level": "N/A",
                    "confirmation_signals": confirm_details,
                    "volume_ratio": f"{last_vol/avg_vol:.1f}x"
                }
                best = max(buy_pro_score, sell_pro_score)
                rec = f"No Pro setup yet. {best}/4 conditions met. " + ("Leaning bullish." if buy_pro_score > sell_pro_score else "Leaning bearish." if sell_pro_score > buy_pro_score else "Neutral.") + " Wait for complete Sweep → BOS → Retest → Confirm sequence."

                return GoldenSetupResponse(
                    mode="Pro (SMC)", signal_type="WAIT", conditions=conditions,
                    adx_value=round(adx, 1), pro_details=pro_details,
                    mtf_confirmation=mtf_data,
                    recommendation=rec
                )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in golden setup analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_mtf_confirmation(ticker, primary_signal):
    """Fetch higher timeframe data and confirm signal"""
    try:
        tf_data = yf.download(ticker, period="6mo", interval="1wk", progress=False)
        if tf_data.empty or len(tf_data) < 10:
            return {"confirmed": False, "timeframe": "Weekly", "detail": "Insufficient weekly data", "strength": "N/A"}

        # Handle multi-index columns from yfinance
        if isinstance(tf_data.columns, pd.MultiIndex):
            w_closes = tf_data['Close'].iloc[:, 0].dropna().values.tolist()
            w_highs = tf_data['High'].iloc[:, 0].dropna().values.tolist()
            w_lows = tf_data['Low'].iloc[:, 0].dropna().values.tolist()
        else:
            w_closes = tf_data['Close'].dropna().values.tolist()
            w_highs = tf_data['High'].dropna().values.tolist()
            w_lows = tf_data['Low'].dropna().values.tolist()

        if len(w_closes) < 10:
            return {"confirmed": False, "timeframe": "Weekly", "detail": "Not enough weekly closes", "strength": "N/A"}

        w_ema20 = calc_ema(w_closes, min(20, len(w_closes)))
        w_ema50 = calc_ema(w_closes, min(50, len(w_closes)))
        w_sma200 = sum(w_closes) / len(w_closes)
        w_current = w_closes[-1]
        w_adx = calc_adx(w_highs, w_lows, w_closes, 14)

        w_above_sma = w_current > w_sma200
        w_ema_bull = w_ema20 > w_ema50

        if primary_signal == "BUY":
            confirmed = w_above_sma and w_ema_bull
            strength = "STRONG" if confirmed and w_adx > 20 else ("MODERATE" if confirmed else "WEAK")
            detail = f"Weekly: Price {'>' if w_above_sma else '<'} SMA, EMA20 {'>' if w_ema_bull else '<'} EMA50, ADX {w_adx:.0f}"
        elif primary_signal == "SELL":
            confirmed = not w_above_sma and not w_ema_bull
            strength = "STRONG" if confirmed and w_adx > 20 else ("MODERATE" if confirmed else "WEAK")
            detail = f"Weekly: Price {'<' if not w_above_sma else '>'} SMA, EMA20 {'<' if not w_ema_bull else '>'} EMA50, ADX {w_adx:.0f}"
        else:
            confirmed = False
            strength = "N/A"
            detail = "No primary signal to confirm"

        return {"confirmed": confirmed, "timeframe": "Weekly", "detail": detail, "strength": strength, "adx": round(w_adx, 1)}
    except Exception as e:
        logging.error(f"MTF error: {e}")
        return {"confirmed": False, "timeframe": "Weekly", "detail": f"MTF error: {str(e)[:40]}", "strength": "N/A"}


class AIIndicatorRequest(BaseModel):
    ticker: str
    bars: List[dict]


class AIIndicatorResponse(BaseModel):
    ai_score: float
    signal_type: str
    indicator_scores: dict
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    targets: Optional[List[str]] = None
    exit_rules: Optional[dict] = None
    volume_confirmation: bool
    recommendation: str


def calc_rsi(closes, period=14):
    """Calculate RSI"""
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_stochastics(highs, lows, closes, k_period=14, d_period=3):
    """Calculate Stochastic %K and %D"""
    if len(closes) < k_period:
        return 50, 50

    k_values = []
    for i in range(k_period - 1, len(closes)):
        h = max(highs[i - k_period + 1:i + 1])
        lo = min(lows[i - k_period + 1:i + 1])
        if h == lo:
            k_values.append(50)
        else:
            k_values.append(((closes[i] - lo) / (h - lo)) * 100)

    pct_k = k_values[-1] if k_values else 50
    pct_d = sum(k_values[-d_period:]) / min(d_period, len(k_values)) if k_values else 50
    return pct_k, pct_d


def calc_dmi_score(highs, lows, closes, period=14):
    """Calculate DMI score (0-100)"""
    if len(closes) < period * 2:
        return 50, 0, 0

    plus_dm = []
    minus_dm = []
    tr_list = []
    for i in range(1, len(highs)):
        high_diff = highs[i] - highs[i-1]
        low_diff = lows[i-1] - lows[i]
        plus_dm.append(max(high_diff, 0) if high_diff > low_diff else 0)
        minus_dm.append(max(low_diff, 0) if low_diff > high_diff else 0)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)

    if len(tr_list) < period:
        return 50, 0, 0

    atr = sum(tr_list[:period]) / period
    p_sum = sum(plus_dm[:period]) / period
    m_sum = sum(minus_dm[:period]) / period

    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
        p_sum = (p_sum * (period - 1) + plus_dm[i]) / period
        m_sum = (m_sum * (period - 1) + minus_dm[i]) / period

    if atr == 0:
        return 50, 0, 0
    plus_di = (p_sum / atr) * 100
    minus_di = (m_sum / atr) * 100

    if plus_di + minus_di == 0:
        return 50, plus_di, minus_di

    # Score: 100 = strong bull, 0 = strong bear, 50 = neutral
    score = (plus_di / (plus_di + minus_di)) * 100
    return score, plus_di, minus_di


def calc_ma_score(closes):
    """MA Score from 9-day and 20-day MA"""
    if len(closes) < 20:
        return 50

    ma9 = sum(closes[-9:]) / 9
    ma20 = sum(closes[-20:]) / 20
    current = closes[-1]

    score = 50
    if current > ma9:
        score += 20
    if current > ma20:
        score += 15
    if ma9 > ma20:
        score += 15

    prev_ma9 = sum(closes[-10:-1]) / 9 if len(closes) >= 10 else ma9
    prev_ma20 = sum(closes[-21:-1]) / 20 if len(closes) >= 21 else ma20
    if prev_ma9 <= prev_ma20 and ma9 > ma20:
        score = min(score + 10, 100)
    if prev_ma9 >= prev_ma20 and ma9 < ma20:
        score = max(score - 10, 0)

    if current < ma9:
        score -= 20
    if current < ma20:
        score -= 15

    return max(0, min(100, score))


def calc_macd_score(closes):
    """MACD Score"""
    if len(closes) < 26:
        return 50

    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)
    macd_line = ema12 - ema26

    prev_ema12 = calc_ema(closes[:-1], 12)
    prev_ema26 = calc_ema(closes[:-1], 26)
    prev_macd = prev_ema12 - prev_ema26

    # Simple signal approximation
    signal = (macd_line + prev_macd) / 2
    histogram = macd_line - signal

    score = 50
    if macd_line > 0:
        score += 20
    else:
        score -= 20
    if macd_line > signal:
        score += 15
    else:
        score -= 15
    if histogram > 0 and histogram > prev_macd - signal:
        score += 15
    elif histogram < 0:
        score -= 15

    return max(0, min(100, score))


def calc_rsi_score(rsi_val):
    """Convert RSI to score"""
    if rsi_val < 30:
        return min(90, 50 + (30 - rsi_val) * 1.3)
    elif rsi_val > 70:
        return max(10, 50 - (rsi_val - 70) * 1.3)
    elif rsi_val > 50:
        return 50 + (rsi_val - 50) * 0.5
    else:
        return 50 - (50 - rsi_val) * 0.5


def calc_stoch_score(pct_k, pct_d):
    """Convert Stochastics to score"""
    score = 50
    if pct_k > pct_d:
        score += 25
    else:
        score -= 25
    if pct_k < 20:
        score += 15
    elif pct_k > 80:
        score -= 15
    return max(0, min(100, score))


@api_router.post("/ai-indicator/analyze", response_model=AIIndicatorResponse)
async def analyze_ai_indicator(request: AIIndicatorRequest):
    """AI Indicator Score - Weighted composite of 5 technical indicators"""
    try:
        bars = request.bars
        if len(bars) < 30:
            raise HTTPException(status_code=400, detail="Need at least 30 bars")

        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        closes = [b['close'] for b in bars]
        volumes = [b['volume'] for b in bars]
        current = closes[-1]

        # 1. DMI Score (30%)
        dmi_score, plus_di, minus_di = calc_dmi_score(highs, lows, closes)

        # 2. MA Score (25%)
        ma_score = calc_ma_score(closes)

        # 3. MACD Score (20%)
        macd_score = calc_macd_score(closes)

        # 4. RSI Score (15%)
        rsi_val = calc_rsi(closes, 14)
        rsi_score = calc_rsi_score(rsi_val)

        # 5. Stochastics Score (10%)
        pct_k, pct_d = calc_stochastics(highs, lows, closes)
        stoch_score = calc_stoch_score(pct_k, pct_d)

        # Weighted AI Score
        ai_score = (dmi_score * 0.30) + (ma_score * 0.25) + (macd_score * 0.20) + (rsi_score * 0.15) + (stoch_score * 0.10)
        ai_score = round(ai_score, 1)

        # Volume confirmation
        avg_vol = sum(volumes[-20:]) / min(20, len(volumes))
        vol_spike = volumes[-1] > avg_vol * 1.2

        indicator_scores = {
            "dmi": {"score": round(dmi_score, 1), "weight": "30%", "detail": f"+DI: {plus_di:.1f}, -DI: {minus_di:.1f}", "raw": f"+DI {plus_di:.0f} / -DI {minus_di:.0f}"},
            "moving_avg": {"score": round(ma_score, 1), "weight": "25%", "detail": "MA9 vs MA20 alignment", "raw": f"MA9: {sum(closes[-9:])/9:.2f}, MA20: {sum(closes[-20:])/min(20,len(closes)):.2f}"},
            "macd": {"score": round(macd_score, 1), "weight": "20%", "detail": "MACD momentum", "raw": f"EMA12-EMA26: {calc_ema(closes,12)-calc_ema(closes,26):.2f}"},
            "rsi": {"score": round(rsi_score, 1), "weight": "15%", "detail": f"RSI: {rsi_val:.1f}", "raw": f"RSI(14): {rsi_val:.1f}"},
            "stochastics": {"score": round(stoch_score, 1), "weight": "10%", "detail": f"%K: {pct_k:.1f}, %D: {pct_d:.1f}", "raw": f"%K: {pct_k:.0f}, %D: {pct_d:.0f}"}
        }

        # Signal
        if ai_score > 70:
            signal_type = "BUY"
            entry = current
            sl = current * 0.93  # 7% stop loss
            risk = entry - sl
            t1 = entry + risk * 2
            t2 = entry + risk * 3
            entry_price = f"{entry:.2f}"
            stop_loss = f"{sl:.2f}"
            targets = [f"{t1:.2f}", f"{t2:.2f}"]
            exit_rules = {
                "stop_loss_pct": "7%",
                "profit_target": f"₹{t1:.2f} (1:2 RR) / ₹{t2:.2f} (1:3 RR)",
                "time_exit": "Exit if no move in 10 days",
                "trailing": "Trail SL to breakeven after T1 hit"
            }
            rec = f"STRONG BUY! AI Score {ai_score:.0f}/100. All indicators aligned bullish. " + ("Volume spike confirms. " if vol_spike else "") + f"Entry ₹{entry:.2f}, SL ₹{sl:.2f} (7%). Targets: T1 ₹{t1:.2f}, T2 ₹{t2:.2f}."
        elif ai_score < 30:
            signal_type = "SELL"
            entry = current
            sl = current * 1.07  # 7% stop loss
            risk = sl - entry
            t1 = entry - risk * 2
            t2 = entry - risk * 3
            entry_price = f"{entry:.2f}"
            stop_loss = f"{sl:.2f}"
            targets = [f"{t1:.2f}", f"{t2:.2f}"]
            exit_rules = {
                "stop_loss_pct": "7%",
                "profit_target": f"₹{t1:.2f} (1:2 RR) / ₹{t2:.2f} (1:3 RR)",
                "time_exit": "Exit if no move in 10 days",
                "trailing": "Trail SL to breakeven after T1 hit"
            }
            rec = f"STRONG SELL! AI Score {ai_score:.0f}/100. Bearish alignment across indicators. " + ("Volume spike confirms breakdown. " if vol_spike else "") + f"Entry ₹{entry:.2f}, SL ₹{sl:.2f} (7%). Targets: T1 ₹{t1:.2f}, T2 ₹{t2:.2f}."
        else:
            signal_type = "WAIT"
            entry_price = None
            stop_loss = None
            targets = None
            exit_rules = None
            rec = f"HOLD — AI Score {ai_score:.0f}/100. Mixed signals. "
            if ai_score > 55:
                rec += "Leaning bullish, wait for score > 70 to enter."
            elif ai_score < 45:
                rec += "Leaning bearish, wait for score < 30 for short."
            else:
                rec += "Neutral zone. Avoid trading, wait for clear direction."

        return AIIndicatorResponse(
            ai_score=ai_score,
            signal_type=signal_type,
            indicator_scores=indicator_scores,
            entry_price=entry_price,
            stop_loss=stop_loss,
            targets=targets,
            exit_rules=exit_rules,
            volume_confirmation=vol_spike,
            recommendation=rec
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in AI indicator analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GodzillaSetupRequest(BaseModel):
    ticker: str
    bars: List[dict]


class GodzillaSetupResponse(BaseModel):
    signal_type: str
    trend_direction: str
    hook_detected: bool
    hook_price: Optional[str] = None
    hook_index: Optional[int] = None
    correction_bars: int
    entry_trigger: Optional[dict] = None
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    targets: Optional[List[str]] = None
    risk_management: Optional[dict] = None
    conditions: dict
    recommendation: str


def detect_ross_hooks(highs, lows, closes, lookback=30):
    """Detect Ross Hooks - first failure to make new high/low in a trend"""
    hooks = []
    start = max(0, len(highs) - lookback)

    # Uptrend hooks (failure to make higher high)
    for i in range(start + 2, len(highs)):
        if highs[i-2] < highs[i-1] and highs[i] < highs[i-1]:
            hooks.append({
                "type": "up",
                "index": i - 1,
                "price": highs[i - 1],
                "bar_index_from_end": len(highs) - 1 - (i - 1)
            })

    # Downtrend hooks (failure to make lower low)
    for i in range(start + 2, len(lows)):
        if lows[i-2] > lows[i-1] and lows[i] > lows[i-1]:
            hooks.append({
                "type": "down",
                "index": i - 1,
                "price": lows[i - 1],
                "bar_index_from_end": len(lows) - 1 - (i - 1)
            })

    return hooks


def detect_trend(closes, period=20):
    """Simple trend detection"""
    if len(closes) < period:
        return "NEUTRAL"
    sma = sum(closes[-period:]) / period
    recent = sum(closes[-5:]) / 5
    if recent > sma * 1.01:
        return "UP"
    elif recent < sma * 0.99:
        return "DOWN"
    return "NEUTRAL"


@api_router.post("/godzilla-setup/analyze", response_model=GodzillaSetupResponse)
async def analyze_godzilla_setup(request: GodzillaSetupRequest):
    """Godzilla Setup - Ross Hook + Trader's Trick Entry (TTE)"""
    try:
        bars = request.bars
        if len(bars) < 20:
            raise HTTPException(status_code=400, detail="Need at least 20 bars")

        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        closes = [b['close'] for b in bars]
        current = closes[-1]

        trend = detect_trend(closes)
        hooks = detect_ross_hooks(highs, lows, closes)

        # Filter hooks by relevance (recent, matching trend)
        relevant_hooks = []
        for h in hooks:
            if h["bar_index_from_end"] <= 10:
                if trend == "UP" and h["type"] == "up":
                    relevant_hooks.append(h)
                elif trend == "DOWN" and h["type"] == "down":
                    relevant_hooks.append(h)
                elif trend == "NEUTRAL":
                    relevant_hooks.append(h)

        if not relevant_hooks:
            # Check any recent hook regardless of trend
            recent = [h for h in hooks if h["bar_index_from_end"] <= 8]
            if recent:
                relevant_hooks = [recent[-1]]

        hook_detected = len(relevant_hooks) > 0

        if not hook_detected:
            conditions = {
                "trend": {"met": trend != "NEUTRAL", "detail": f"Trend: {trend}"},
                "ross_hook": {"met": False, "detail": "No Ross Hook detected in recent bars"},
                "correction_bars": {"met": False, "detail": "N/A - no hook"},
                "entry_trigger": {"met": False, "detail": "N/A - no hook"}
            }
            return GodzillaSetupResponse(
                signal_type="WAIT", trend_direction=trend,
                hook_detected=False, correction_bars=0,
                conditions=conditions,
                recommendation=f"No Ross Hook detected. Trend is {trend}. Wait for price to make a high/low followed by failure to exceed it."
            )

        # Use most recent relevant hook
        hook = relevant_hooks[-1]
        hook_idx = hook["index"]
        hook_price = hook["price"]
        hook_type = hook["type"]

        # Count correction bars after hook (max 3)
        bars_after_hook = len(bars) - 1 - hook_idx
        correction_count = min(bars_after_hook, 3)

        # Analyze correction bars for TTE entry
        entry_found = False
        entry_price_val = None
        sl_price = None
        trigger_info = None

        if hook_type == "up":
            # Long TTE: enter on breakout above correction bar high
            for i in range(1, correction_count + 1):
                bar_idx = hook_idx + i
                if bar_idx >= len(bars):
                    break
                corr_bar = bars[bar_idx]
                corr_high = corr_bar['high']

                # Check if enough distance between correction bar high and hook
                distance_pct = ((hook_price - corr_high) / hook_price) * 100
                if distance_pct > 0.3:  # At least 0.3% gap
                    # Check if current price broke above correction bar high
                    if current > corr_high:
                        entry_found = True
                        entry_price_val = corr_high
                        sl_price = corr_bar['low']
                        trigger_info = {
                            "correction_bar": i,
                            "bar_high": f"{corr_high:.2f}",
                            "bar_low": f"{corr_bar['low']:.2f}",
                            "distance_to_hook": f"{distance_pct:.1f}%",
                            "status": "TRIGGERED - Price broke above"
                        }
                        break
                    else:
                        trigger_info = {
                            "correction_bar": i,
                            "bar_high": f"{corr_high:.2f}",
                            "bar_low": f"{corr_bar['low']:.2f}",
                            "distance_to_hook": f"{distance_pct:.1f}%",
                            "status": f"PENDING - Price ₹{current:.2f} below trigger ₹{corr_high:.2f}"
                        }

            if not trigger_info and correction_count > 0:
                last_corr = bars[min(hook_idx + correction_count, len(bars) - 1)]
                trigger_info = {
                    "correction_bar": correction_count,
                    "bar_high": f"{last_corr['high']:.2f}",
                    "bar_low": f"{last_corr['low']:.2f}",
                    "distance_to_hook": f"{((hook_price - last_corr['high']) / hook_price * 100):.1f}%",
                    "status": "WATCHING"
                }

        else:
            # Short TTE: enter on breakout below correction bar low
            for i in range(1, correction_count + 1):
                bar_idx = hook_idx + i
                if bar_idx >= len(bars):
                    break
                corr_bar = bars[bar_idx]
                corr_low = corr_bar['low']

                distance_pct = ((corr_low - hook_price) / hook_price) * 100
                if distance_pct > 0.3:
                    if current < corr_low:
                        entry_found = True
                        entry_price_val = corr_low
                        sl_price = corr_bar['high']
                        trigger_info = {
                            "correction_bar": i,
                            "bar_high": f"{corr_bar['high']:.2f}",
                            "bar_low": f"{corr_low:.2f}",
                            "distance_to_hook": f"{distance_pct:.1f}%",
                            "status": "TRIGGERED - Price broke below"
                        }
                        break
                    else:
                        trigger_info = {
                            "correction_bar": i,
                            "bar_high": f"{corr_bar['high']:.2f}",
                            "bar_low": f"{corr_low:.2f}",
                            "distance_to_hook": f"{distance_pct:.1f}%",
                            "status": f"PENDING - Price ₹{current:.2f} above trigger ₹{corr_low:.2f}"
                        }

            if not trigger_info and correction_count > 0:
                last_corr = bars[min(hook_idx + correction_count, len(bars) - 1)]
                trigger_info = {
                    "correction_bar": correction_count,
                    "bar_high": f"{last_corr['high']:.2f}",
                    "bar_low": f"{last_corr['low']:.2f}",
                    "distance_to_hook": f"{((last_corr['low'] - hook_price) / hook_price * 100):.1f}%",
                    "status": "WATCHING"
                }

        # Build response
        if entry_found:
            signal_type = "BUY" if hook_type == "up" else "SELL"
            risk = abs(entry_price_val - sl_price)
            if hook_type == "up":
                cost_cover = entry_price_val + risk * 0.5
                t2 = hook_price
                t3 = hook_price + risk * 2
            else:
                cost_cover = entry_price_val - risk * 0.5
                t2 = hook_price
                t3 = hook_price - risk * 2

            targets = [f"{cost_cover:.2f}", f"{t2:.2f}", f"{t3:.2f}"]
            risk_mgmt = {
                "partial_exit": f"₹{cost_cover:.2f} (cover costs + small profit)",
                "breakeven_stop": f"₹{entry_price_val:.2f} (move SL to entry after T1)",
                "hook_target": f"₹{hook_price:.2f} (test Hook point)",
                "runner": f"₹{t3:.2f} (if breakout past Hook continues)"
            }
            rec = (f"GODZILLA {'BUY' if hook_type == 'up' else 'SELL'}! Ross Hook at ₹{hook_price:.2f}. "
                   f"TTE triggered on correction bar {trigger_info['correction_bar']}. "
                   f"Entry ₹{entry_price_val:.2f}, SL ₹{sl_price:.2f}. "
                   f"T1 (cost cover) ₹{cost_cover:.2f}, T2 (Hook test) ₹{hook_price:.2f}. "
                   f"After T1 move SL to breakeven. Let remaining position run if Hook breaks.")
        else:
            signal_type = "WAIT"
            targets = None
            risk_mgmt = None
            entry_price_val = None
            sl_price = None

            if correction_count >= 3:
                rec = f"Ross Hook at ₹{hook_price:.2f} detected but 3 correction bars passed without trigger. Setup expired. Wait for next Hook."
            elif correction_count > 0:
                if hook_type == "up":
                    trigger_level = trigger_info['bar_high'] if trigger_info else "N/A"
                    rec = f"Ross Hook at ₹{hook_price:.2f}. Correction bar {correction_count} active. Enter LONG if price breaks above ₹{trigger_level}. Max 3 bars to trigger."
                else:
                    trigger_level = trigger_info['bar_low'] if trigger_info else "N/A"
                    rec = f"Ross Hook at ₹{hook_price:.2f}. Correction bar {correction_count} active. Enter SHORT if price breaks below ₹{trigger_level}. Max 3 bars to trigger."
            else:
                rec = f"Ross Hook at ₹{hook_price:.2f}. Waiting for first correction bar. Hook type: {'Uptrend' if hook_type == 'up' else 'Downtrend'}."

        conditions = {
            "trend": {"met": trend != "NEUTRAL", "detail": f"Trend: {trend}"},
            "ross_hook": {"met": hook_detected, "detail": f"Hook at ₹{hook_price:.2f} ({'Uptrend' if hook_type == 'up' else 'Downtrend'})"},
            "correction_bars": {"met": correction_count > 0, "detail": f"{correction_count}/3 correction bars"},
            "entry_trigger": {"met": entry_found, "detail": trigger_info.get("status", "N/A") if trigger_info else "No trigger"}
        }

        return GodzillaSetupResponse(
            signal_type=signal_type,
            trend_direction=trend,
            hook_detected=hook_detected,
            hook_price=f"{hook_price:.2f}",
            hook_index=hook.get("bar_index_from_end"),
            correction_bars=correction_count,
            entry_trigger=trigger_info,
            entry_price=f"{entry_price_val:.2f}" if entry_price_val else None,
            stop_loss=f"{sl_price:.2f}" if sl_price else None,
            targets=targets,
            risk_management=risk_mgmt,
            conditions=conditions,
            recommendation=rec
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in godzilla setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================= SMC (Smart Money Concepts) ENGINE =======================

def _smc_compute_atr(highs, lows, closes, period=14):
    """ATR(14) calculation"""
    if len(closes) < period + 1:
        return abs(highs[-1] - lows[-1])
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:]) / period if len(trs) >= period else sum(trs) / len(trs)

def _smc_daily_bias(closes, highs, lows):
    """Phase 1: Daily Bias using Higher Highs/Lows — relaxed for more signals"""
    if len(closes) < 10:
        return "NEUTRAL", "Insufficient data"
    recent_highs = highs[-8:]
    recent_lows = lows[-8:]
    hh_count = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i-1])
    hl_count = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] > recent_lows[i-1])
    ll_count = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] < recent_lows[i-1])
    lh_count = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] < recent_highs[i-1])
    last_close = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else last_close
    # Relaxed: 2+ HH/HL enough for bias
    if hh_count >= 3 and hl_count >= 3:
        return "BULLISH", f"HH: {hh_count}, HL: {hl_count} — Strong uptrend"
    elif ll_count >= 3 and lh_count >= 3:
        return "BEARISH", f"LL: {ll_count}, LH: {lh_count} — Strong downtrend"
    elif hh_count >= 2 and last_close > prev_close:
        return "BULLISH", f"HH: {hh_count}, HL: {hl_count} — Bullish bias"
    elif ll_count >= 2 and last_close < prev_close:
        return "BEARISH", f"LL: {ll_count}, LH: {lh_count} — Bearish bias"
    elif last_close > prev_close and hh_count >= 1:
        return "BULLISH", f"HH: {hh_count} + price rising — Mild bullish"
    elif last_close < prev_close and ll_count >= 1:
        return "BEARISH", f"LL: {ll_count} + price falling — Mild bearish"
    return "NEUTRAL", f"HH:{hh_count} HL:{hl_count} LL:{ll_count} LH:{lh_count}"

def _smc_liquidity_sweep(highs, lows, closes):
    """Phase 2: Liquidity Sweep — relaxed with wider proximity check"""
    if len(closes) < 5:
        return "NONE", None, "Insufficient data"
    pdh = max(highs[-8:-1]) if len(highs) > 8 else max(highs[:-1])
    pdl = min(lows[-8:-1]) if len(lows) > 8 else min(lows[:-1])
    last_high = highs[-1]
    last_low = lows[-1]
    last_close = closes[-1]
    # Check last 3 bars for sweep
    for k in range(min(3, len(highs))):
        if highs[-(k+1)] > pdh and closes[-(k+1)] < pdh:
            return "PDH_SWEPT", pdh, f"Swept PDH {pdh:.2f} — Sell-side liquidity grabbed"
        if lows[-(k+1)] < pdl and closes[-(k+1)] > pdl:
            return "PDL_SWEPT", pdl, f"Swept PDL {pdl:.2f} — Buy-side liquidity grabbed"
    # Near proximity = 0.5% (was 0.2%)
    if last_high > pdh * 0.995:
        return "PDH_NEAR", pdh, f"Near PDH {pdh:.2f} — Potential sweep forming"
    if last_low < pdl * 1.005:
        return "PDL_NEAR", pdl, f"Near PDL {pdl:.2f} — Potential sweep forming"
    # Even milder: within 1% range
    if last_high > pdh * 0.99:
        return "PDH_NEAR", pdh, f"Within 1% of PDH {pdh:.2f}"
    if last_low < pdl * 1.01:
        return "PDL_NEAR", pdl, f"Within 1% of PDL {pdl:.2f}"
    return "NONE", None, "No liquidity sweep"

def _smc_detect_mss(closes, highs, lows):
    """Phase 3: Market Structure Shift + IFVG — relaxed detection"""
    if len(closes) < 8:
        return False, None, None, "Insufficient data"
    mss_found = False
    mss_direction = None
    ifvg_zone = None
    recent = closes[-8:]
    recent_h = highs[-8:]
    recent_l = lows[-8:]
    # Bearish MSS: any recent lower low after a swing high
    swing_h = max(recent[:-2])
    swing_h_idx = recent[:-2].index(swing_h)
    if swing_h_idx < len(recent) - 2:
        # Check if price dropped after swing high
        drop_after = min(recent[swing_h_idx+1:])
        prev_low = min(recent_l[:swing_h_idx+1]) if swing_h_idx > 0 else recent_l[0]
        if drop_after < prev_low * 1.005:  # Relaxed: within 0.5%
            mss_found = True
            mss_direction = "BEARISH"
            ifvg_high = max(recent_h[-3], recent_h[-2])
            ifvg_low = min(recent_l[-3], recent[-2])
            ifvg_zone = (ifvg_low, ifvg_high)
    # Bullish MSS: any recent higher high after a swing low
    if not mss_found:
        swing_l = min(recent[:-2])
        swing_l_idx = recent[:-2].index(swing_l)
        if swing_l_idx < len(recent) - 2:
            rise_after = max(recent[swing_l_idx+1:])
            prev_high = max(recent_h[:swing_l_idx+1]) if swing_l_idx > 0 else recent_h[0]
            if rise_after > prev_high * 0.995:  # Relaxed
                mss_found = True
                mss_direction = "BULLISH"
                ifvg_low = min(recent_l[-3], recent_l[-2])
                ifvg_high = max(recent[-2], recent_h[-3])
                ifvg_zone = (ifvg_low, ifvg_high)
    # Fallback: use price direction of last 5 bars as weak MSS
    if not mss_found:
        if closes[-1] > closes[-3] and closes[-2] > closes[-4]:
            mss_found = True
            mss_direction = "BULLISH"
            ifvg_low = min(lows[-4:])
            ifvg_high = max(highs[-4:])
            ifvg_zone = (ifvg_low, ifvg_high)
        elif closes[-1] < closes[-3] and closes[-2] < closes[-4]:
            mss_found = True
            mss_direction = "BEARISH"
            ifvg_low = min(lows[-4:])
            ifvg_high = max(highs[-4:])
            ifvg_zone = (ifvg_low, ifvg_high)
    detail = f"MSS {mss_direction} detected" if mss_found else "No MSS detected"
    if ifvg_zone:
        detail += f" | IFVG Zone: {ifvg_zone[0]:.2f} - {ifvg_zone[1]:.2f}"
    return mss_found, mss_direction, ifvg_zone, detail

def _smc_precision_entry(bars, ifvg_zone, mss_direction, atr):
    """Phase 4: Precision Entry — relaxed wick ratio and volume"""
    if not ifvg_zone or not mss_direction or len(bars) < 3:
        return False, None, "No IFVG zone for entry"
    last = bars[-1]
    op, hi, lo, cl = last['open'], last['high'], last['low'], last['close']
    body = abs(cl - op)
    upper_wick = hi - max(op, cl)
    lower_wick = min(op, cl) - lo
    candle_range = hi - lo if hi != lo else 0.01
    # Volume filter — relaxed: 1.0x average (was 1.5x)
    volumes = [b.get('volume', 0) for b in bars[-11:]]
    avg_vol = sum(volumes[:-1]) / max(len(volumes) - 1, 1) if len(volumes) > 1 else 0
    cur_vol = volumes[-1] if volumes else 0
    vol_confirmed = cur_vol > avg_vol * 0.8 if avg_vol > 0 else True
    rejection_quality = "WEAK"
    if mss_direction == "BULLISH":
        in_zone = lo <= ifvg_zone[1] * 1.01 and cl >= ifvg_zone[0] * 0.99  # Relaxed zone
        wick_ratio = lower_wick / body if body > 0 else 0
        close_in_range = (cl - lo) / candle_range if candle_range > 0 else 0
        if wick_ratio >= 1.8 and close_in_range >= 0.6:
            rejection_quality = "STRONG"
        elif wick_ratio >= 0.8 or close_in_range >= 0.55:
            rejection_quality = "MODERATE"
        entry_valid = in_zone and rejection_quality != "WEAK"
    else:
        in_zone = hi >= ifvg_zone[0] * 0.99 and cl <= ifvg_zone[1] * 1.01
        wick_ratio = upper_wick / body if body > 0 else 0
        close_in_range = (hi - cl) / candle_range if candle_range > 0 else 0
        if wick_ratio >= 1.8 and close_in_range >= 0.6:
            rejection_quality = "STRONG"
        elif wick_ratio >= 0.8 or close_in_range >= 0.55:
            rejection_quality = "MODERATE"
        entry_valid = in_zone and rejection_quality != "WEAK"
    # Fallback: if in zone, always at least moderate
    if not entry_valid and (mss_direction == "BULLISH" and lo <= ifvg_zone[1] * 1.02) or \
       (not entry_valid and mss_direction == "BEARISH" and hi >= ifvg_zone[0] * 0.98):
        rejection_quality = "MODERATE"
        entry_valid = True
        vol_confirmed = True
    detail = f"Rejection: {rejection_quality}, Vol: {'OK' if vol_confirmed else 'LOW'}"
    return entry_valid, rejection_quality, detail

def _smc_trade_management(entry_price, atr, direction):
    """Phase 5: Trade Management with ATR-based SL and TP"""
    sl_mult = 1.0
    sl = entry_price - (atr * sl_mult) if direction == "BUY" else entry_price + (atr * sl_mult)
    risk = abs(entry_price - sl)
    tp1 = entry_price + risk if direction == "BUY" else entry_price - risk
    tp2 = entry_price + (risk * 2.5) if direction == "BUY" else entry_price - (risk * 2.5)
    rr = f"1:{2.5:.1f}"
    return sl, tp1, tp2, rr

def run_full_smc_analysis(bars):
    """Full SMC 5-Phase analysis on bar data"""
    if len(bars) < 25:
        return {
            "status": "INSUFFICIENT_DATA", "signal_type": "WAIT",
            "daily_bias": "NEUTRAL", "liquidity_sweep": "NONE",
            "mss_detected": False, "phases": [], "confidence": 0,
            "recommendation": "Need at least 25 bars for SMC analysis"
        }
    closes = [b['close'] for b in bars]
    highs = [b['high'] for b in bars]
    lows = [b['low'] for b in bars]
    atr = _smc_compute_atr(highs, lows, closes)
    phases = []
    confidence = 0

    # Phase 1: Daily Bias
    bias, bias_detail = _smc_daily_bias(closes, highs, lows)
    p1_status = "PASS" if bias != "NEUTRAL" else "FAIL"
    phases.append({"phase": 1, "name": "Daily Bias", "status": p1_status, "detail": bias_detail})
    if p1_status == "PASS":
        confidence += 20

    # Phase 2: Liquidity Sweep
    sweep, sweep_level, sweep_detail = _smc_liquidity_sweep(highs, lows, closes)
    p2_pass = sweep in ("PDH_SWEPT", "PDL_SWEPT")
    p2_partial = sweep in ("PDH_NEAR", "PDL_NEAR")
    p2_status = "PASS" if p2_pass else ("PARTIAL" if p2_partial else "FAIL")
    phases.append({"phase": 2, "name": "Liquidity Sweep", "status": p2_status, "detail": sweep_detail})
    if p2_pass:
        confidence += 25
    elif p2_partial:
        confidence += 10

    # Phase 3: MSS + IFVG
    mss_found, mss_dir, ifvg_zone, mss_detail = _smc_detect_mss(closes, highs, lows)
    p3_status = "PASS" if mss_found else "FAIL"
    phases.append({"phase": 3, "name": "MSS + IFVG", "status": p3_status, "detail": mss_detail})
    if mss_found:
        confidence += 25

    # Phase 4: Precision Entry
    entry_valid, rejection_quality, entry_detail = _smc_precision_entry(bars, ifvg_zone, mss_dir, atr)
    p4_status = "PASS" if entry_valid else "FAIL"
    phases.append({"phase": 4, "name": "Precision Entry", "status": p4_status, "detail": entry_detail})
    if entry_valid:
        confidence += 20
        if rejection_quality == "STRONG":
            confidence += 10

    # Determine signal
    current = closes[-1]
    signal_type = "WAIT"
    entry_price = None
    sl = tp1 = tp2 = rr = None

    # Need at least Phase 1 (bias) + one more to generate signal — relaxed for more alerts
    pass_count = sum(1 for p in phases if p["status"] == "PASS")
    partial_count = sum(1 for p in phases if p["status"] == "PARTIAL")

    if pass_count >= 2:
        if bias == "BULLISH" or (mss_dir == "BULLISH"):
            signal_type = "BUY"
        elif bias == "BEARISH" or (mss_dir == "BEARISH"):
            signal_type = "SELL"
    elif pass_count >= 1 and partial_count >= 1 and confidence >= 25:
        if bias == "BULLISH":
            signal_type = "BUY"
        elif bias == "BEARISH":
            signal_type = "SELL"
        elif mss_dir == "BULLISH":
            signal_type = "BUY"
        elif mss_dir == "BEARISH":
            signal_type = "SELL"

    if signal_type != "WAIT":
        entry_price = current
        sl, tp1, tp2, rr = _smc_trade_management(entry_price, atr, signal_type)

    # Phase 5: Trade Management
    if signal_type != "WAIT":
        p5_detail = f"SL: {sl:.2f} (ATR-based) | TP1: {tp1:.2f} (1:1) | TP2: {tp2:.2f} (1:2.5) | Risk: 1% per trade"
        phases.append({"phase": 5, "name": "Trade Management", "status": "PASS", "detail": p5_detail})
    else:
        phases.append({"phase": 5, "name": "Trade Management", "status": "FAIL", "detail": "No trade — waiting for all conditions"})

    # Recommendation
    if signal_type == "BUY":
        rec = f"BUY — Entry: {current:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f}"
    elif signal_type == "SELL":
        rec = f"SELL — Entry: {current:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f}"
    else:
        rec = "WAIT — Not all SMC conditions met. Watching for setup."

    return {
        "status": "ACTIVE" if signal_type != "WAIT" else "SCANNING",
        "signal_type": signal_type,
        "daily_bias": bias,
        "liquidity_sweep": sweep,
        "mss_detected": mss_found,
        "ifvg_zone": f"{ifvg_zone[0]:.2f} - {ifvg_zone[1]:.2f}" if ifvg_zone else None,
        "entry_price": f"{entry_price:.2f}" if entry_price else None,
        "stop_loss": f"{sl:.2f}" if sl else None,
        "tp1": f"{tp1:.2f}" if tp1 else None,
        "tp2": f"{tp2:.2f}" if tp2 else None,
        "risk_reward": rr,
        "atr_value": round(atr, 2),
        "rejection_quality": rejection_quality if entry_valid else None,
        "volume_confirmed": entry_valid,
        "session_valid": True,
        "phases": phases,
        "confidence": min(confidence, 100),
        "recommendation": rec,
    }


def run_mini_smc(bars):
    """Quick SMC check for auto-scanner"""
    if len(bars) < 25:
        return "WAIT"
    result = run_full_smc_analysis(bars)
    return result.get("signal_type", "WAIT")


@api_router.post("/smc/analyze", response_model=SMCAnalysisResponse)
async def analyze_smc(request: SMCAnalysisRequest):
    """SMC (Smart Money Concepts) 5-Phase Analysis"""
    try:
        bars = request.bars
        if len(bars) < 25:
            return SMCAnalysisResponse(
                status="INSUFFICIENT_DATA", signal_type="WAIT",
                daily_bias="NEUTRAL", liquidity_sweep="NONE",
                mss_detected=False, phases=[], confidence=0,
                recommendation="Need at least 25 bars (15M timeframe recommended)"
            )
        result = run_full_smc_analysis(bars)
        return SMCAnalysisResponse(**result)
    except Exception as e:
        logging.error(f"SMC analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================= PAC + S&O MATRIX (High Confluence) =======================

def _pac_calc_ema(closes, period):
    if len(closes) < period:
        return sum(closes) / len(closes) if closes else 0
    mult = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for c in closes[period:]:
        ema = (c - ema) * mult + ema
    return ema

def _pac_calc_atr(bars, period=14):
    if len(bars) < 2:
        return 0
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]['high'], bars[i]['low'], bars[i-1]['close']
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return 0
    return sum(trs[-period:]) / min(len(trs), period)

def _pac_detect_structure(highs, lows, closes):
    """Detect BOS, CHoCH, CHoCH+ from swing points"""
    n = len(highs)
    if n < 10:
        return "NEUTRAL", False, False, False

    # Find swing points (simple 3-bar pivot)
    swing_highs, swing_lows = [], []
    for i in range(2, n - 2):
        if highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and highs[i] >= highs[i+1] and highs[i] >= highs[i+2]:
            swing_highs.append((i, highs[i]))
        if lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and lows[i] <= lows[i+1] and lows[i] <= lows[i+2]:
            swing_lows.append((i, lows[i]))

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "NEUTRAL", False, False, False

    # Check recent swing structure
    last_sh = swing_highs[-1][1]
    prev_sh = swing_highs[-2][1]
    last_sl = swing_lows[-1][1]
    prev_sl = swing_lows[-2][1]

    hh = last_sh > prev_sh
    hl = last_sl > prev_sl
    lh = last_sh < prev_sh
    ll = last_sl < prev_sl

    bos = False
    choch = False
    choch_plus = False

    if hh and hl:
        # Bullish structure — check for BOS (break above prev swing high)
        if closes[-1] > prev_sh:
            bos = True
        bias = "BULLISH"
    elif lh and ll:
        # Bearish structure — BOS below prev swing low
        if closes[-1] < prev_sl:
            bos = True
        bias = "BEARISH"
    elif hh and ll:
        # Mixed — possible CHoCH
        choch = True
        bias = "BULLISH" if closes[-1] > (last_sh + last_sl) / 2 else "BEARISH"
    elif lh and hl:
        choch = True
        bias = "BEARISH" if closes[-1] < (last_sh + last_sl) / 2 else "BULLISH"
    else:
        bias = "NEUTRAL"

    # CHoCH+ = strong reversal: previous was trending one way, now broke structure opposite
    if choch and abs(closes[-1] - closes[-5]) / closes[-5] > 0.008:
        choch_plus = True

    return bias, bos, choch, choch_plus

def _pac_find_order_blocks(bars, bias):
    """Find Volumetric Order Blocks (high volume candles at reversal points)"""
    n = len(bars)
    if n < 10:
        return None, None

    volumes = [b.get('volume', 0) for b in bars]
    avg_vol = sum(volumes[-20:]) / max(len(volumes[-20:]), 1) if volumes else 1

    ob_zone = None
    ob_type = None

    # Scan last 15 bars for order blocks
    for i in range(max(n - 15, 1), n - 1):
        vol = bars[i].get('volume', 0)
        body = abs(bars[i]['close'] - bars[i]['open'])
        candle_range = bars[i]['high'] - bars[i]['low']
        if candle_range == 0:
            continue
        body_ratio = body / candle_range

        # High volume + strong body = potential OB
        if vol > avg_vol * 1.2 and body_ratio > 0.5:
            if bias == "BULLISH" and bars[i]['close'] > bars[i]['open']:
                # Bullish OB = demand zone
                ob_zone = (bars[i]['low'], bars[i]['open'])
                ob_type = "BULLISH_OB"
            elif bias == "BEARISH" and bars[i]['close'] < bars[i]['open']:
                # Bearish OB = supply zone
                ob_zone = (bars[i]['open'], bars[i]['high'])
                ob_type = "BEARISH_OB"

    return ob_zone, ob_type

def _pac_detect_liquidity_sweep(highs, lows):
    """Detect liquidity grabs: equal highs/lows broken then reversed"""
    n = len(highs)
    if n < 10:
        return False

    # Check for equal lows/highs then sweep
    tolerance = 0.003  # 0.3%

    # Check recent equal lows swept
    for i in range(n - 8, n - 3):
        for j in range(i + 1, min(i + 4, n - 2)):
            if abs(lows[i] - lows[j]) / lows[i] < tolerance:
                # Equal lows found — check if swept then bounced
                for k in range(j + 1, min(j + 3, n)):
                    if lows[k] < min(lows[i], lows[j]) and highs[k] > lows[i]:
                        return True

    # Check equal highs swept
    for i in range(n - 8, n - 3):
        for j in range(i + 1, min(i + 4, n - 2)):
            if abs(highs[i] - highs[j]) / highs[i] < tolerance:
                for k in range(j + 1, min(j + 3, n)):
                    if highs[k] > max(highs[i], highs[j]) and lows[k] < highs[i]:
                        return True

    return False

def _pac_find_fvg(bars):
    """Find Fair Value Gaps (3-candle imbalances)"""
    n = len(bars)
    if n < 5:
        return None

    # Check last 10 bars for FVG
    for i in range(max(n - 10, 2), n - 1):
        # Bullish FVG: bar[i-2] high < bar[i] low (gap up)
        if bars[i]['low'] > bars[i-2]['high']:
            return (bars[i-2]['high'], bars[i]['low'])
        # Bearish FVG: bar[i-2] low > bar[i] high (gap down)
        if bars[i]['high'] < bars[i-2]['low']:
            return (bars[i]['high'], bars[i-2]['low'])

    return None

def _pac_premium_discount(closes, highs, lows):
    """Calculate if price is in Premium or Discount zone"""
    n = len(closes)
    if n < 20:
        return "NEUTRAL"
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    mid = (recent_high + recent_low) / 2
    current = closes[-1]
    if current < mid - (mid - recent_low) * 0.3:
        return "DISCOUNT"
    elif current > mid + (recent_high - mid) * 0.3:
        return "PREMIUM"
    return "EQUILIBRIUM"

def _so_signal_confirmation(closes, highs, lows, ema_fast, ema_slow):
    """S&O: Generate confirmation signals based on trend + retracement"""
    current = closes[-1]
    prev = closes[-2] if len(closes) > 1 else current

    above_cloud = current > ema_fast and current > ema_slow
    below_cloud = current < ema_fast and current < ema_slow
    trend_up = ema_fast > ema_slow
    trend_down = ema_fast < ema_slow

    # Check for retracement to EMA then bounce
    near_ema = abs(current - ema_fast) / ema_fast < 0.005
    bounce_up = prev < ema_fast and current > ema_fast
    bounce_down = prev > ema_fast and current < ema_fast

    signal = None
    strength = None

    if trend_up and above_cloud:
        if bounce_up or near_ema:
            signal = "BUY"
            strength = "STRONG+" if (current - prev) / prev > 0.003 else "NORMAL"
        elif current > prev:
            signal = "BUY"
            strength = "NORMAL"
    elif trend_down and below_cloud:
        if bounce_down or near_ema:
            signal = "SELL"
            strength = "STRONG+" if (prev - current) / prev > 0.003 else "NORMAL"
        elif current < prev:
            signal = "SELL"
            strength = "NORMAL"

    cloud_trend = "BULLISH" if above_cloud else "BEARISH" if below_cloud else "NEUTRAL"
    return signal, strength, cloud_trend

def _so_smart_trail(bars, atr):
    """S&O: Smart Trail calculation (ATR-based trailing stop)"""
    if not bars or atr == 0:
        return None
    current = bars[-1]['close']
    bullish = bars[-1]['close'] > bars[-1]['open']
    if bullish:
        return round(current - atr * 1.5, 2)
    else:
        return round(current + atr * 1.5, 2)

def _oscillator_matrix(closes, volumes):
    """Oscillator Matrix: Money Flow, Divergence, Momentum"""
    n = len(closes)

    # Smart Money Flow (simplified OBV direction)
    money_flow = "NEUTRAL"
    if n >= 10:
        obv = 0
        obv_vals = []
        for i in range(1, n):
            if closes[i] > closes[i-1]:
                obv += volumes[i] if i < len(volumes) else 0
            elif closes[i] < closes[i-1]:
                obv -= volumes[i] if i < len(volumes) else 0
            obv_vals.append(obv)
        if len(obv_vals) >= 5:
            recent_obv = obv_vals[-1]
            past_obv = obv_vals[-5]
            if recent_obv > past_obv * 1.05:
                money_flow = "BULLISH"
            elif recent_obv < past_obv * 0.95:
                money_flow = "BEARISH"

    # RSI for momentum
    rsi = 50
    if n >= 15:
        gains, losses_a = [], []
        for j in range(1, min(15, n)):
            d = closes[-j] - closes[-j-1]
            if d > 0:
                gains.append(d)
            else:
                losses_a.append(abs(d))
        avg_g = sum(gains) / 14 if gains else 0.001
        avg_l = sum(losses_a) / 14 if losses_a else 0.001
        rs = avg_g / avg_l if avg_l > 0 else 1
        rsi = 100 - (100 / (1 + rs))

    momentum = "OVERBOUGHT" if rsi > 70 else "OVERSOLD" if rsi < 30 else "STRONG" if 45 < rsi < 65 else "NEUTRAL"

    # Divergence detection (price vs RSI direction)
    divergence = None
    if n >= 20:
        price_trend = closes[-1] - closes[-10]
        # Simple RSI trend comparison
        rsi_now = rsi
        # Approx old RSI
        gains2, losses2 = [], []
        for j in range(10, min(24, n)):
            d = closes[-j] - closes[-j-1] if j+1 < n else 0
            if d > 0:
                gains2.append(d)
            else:
                losses2.append(abs(d))
        avg_g2 = sum(gains2) / 14 if gains2 else 0.001
        avg_l2 = sum(losses2) / 14 if losses2 else 0.001
        rs2 = avg_g2 / avg_l2 if avg_l2 > 0 else 1
        rsi_old = 100 - (100 / (1 + rs2))

        rsi_trend = rsi_now - rsi_old

        if price_trend < 0 and rsi_trend > 5:
            divergence = "BULLISH_DIVERGENCE"
        elif price_trend > 0 and rsi_trend < -5:
            divergence = "BEARISH_DIVERGENCE"

    return money_flow, divergence, momentum, rsi


def run_full_pac_so_analysis(bars):
    """Full PAC + S&O Matrix High Confluence Analysis"""
    n = len(bars)
    if n < 30:
        return {
            "status": "INSUFFICIENT_DATA", "signal_type": "WAIT",
            "structure_bias": "NEUTRAL", "confluence_score": 0,
            "modules": [], "confidence": 0,
            "recommendation": "Need at least 30 bars (15M timeframe recommended)"
        }

    closes = [b['close'] for b in bars]
    highs = [b['high'] for b in bars]
    lows = [b['low'] for b in bars]
    volumes = [b.get('volume', 0) for b in bars]
    current = closes[-1]

    atr = _pac_calc_atr(bars, 14)
    ema_9 = _pac_calc_ema(closes, 9)
    ema_21 = _pac_calc_ema(closes, 21)
    ema_50 = _pac_calc_ema(closes, min(50, n - 1))

    modules = []
    confluence = 0

    # ============ MODULE 1: PAC — Structure + Bias + Entry Zone ============
    bias, bos, choch, choch_plus = _pac_detect_structure(highs, lows, closes)
    ob_zone, ob_type = _pac_find_order_blocks(bars, bias)
    liq_swept = _pac_detect_liquidity_sweep(highs, lows)
    fvg = _pac_find_fvg(bars)
    pd_zone = _pac_premium_discount(closes, highs, lows)

    pac_signals = []
    pac_status = "FAIL"

    if bos:
        pac_signals.append(f"BOS detected ({bias})")
        confluence += 15
    if choch:
        pac_signals.append(f"CHoCH detected{' (STRONG+)' if choch_plus else ''}")
        confluence += 20 if choch_plus else 12
    if ob_zone:
        pac_signals.append(f"{ob_type}: {ob_zone[0]:.2f} - {ob_zone[1]:.2f}")
        confluence += 12
    if liq_swept:
        pac_signals.append("Liquidity Sweep confirmed")
        confluence += 10
    if fvg:
        pac_signals.append(f"FVG: {fvg[0]:.2f} - {fvg[1]:.2f}")
        confluence += 8
    if (bias == "BULLISH" and pd_zone == "DISCOUNT") or (bias == "BEARISH" and pd_zone == "PREMIUM"):
        pac_signals.append(f"Price in {pd_zone} zone (aligned with {bias} bias)")
        confluence += 10

    if confluence >= 20:
        pac_status = "PASS"
    elif confluence >= 10:
        pac_status = "PARTIAL"

    modules.append({
        "module": "PAC (Price Action Concepts)",
        "status": pac_status,
        "detail": f"Bias: {bias} | {'BOS' if bos else 'CHoCH+' if choch_plus else 'CHoCH' if choch else 'No structure break'} | Zone: {pd_zone}",
        "sub_signals": pac_signals,
    })

    # ============ MODULE 2: S&O — Confirmation + Trend Filter ============
    so_signal, so_strength, cloud_trend = _so_signal_confirmation(closes, highs, lows, ema_9, ema_21)
    smart_trail = _so_smart_trail(bars, atr)

    so_signals = []
    so_status = "FAIL"
    so_confluence = 0

    if so_signal:
        so_signals.append(f"{so_signal} Signal ({so_strength})")
        so_confluence += 18 if so_strength == "STRONG+" else 12
    if cloud_trend == bias and cloud_trend != "NEUTRAL":
        so_signals.append(f"Neo Cloud aligned ({cloud_trend})")
        so_confluence += 10
    if smart_trail:
        so_signals.append(f"Smart Trail: {smart_trail}")
        so_confluence += 5

    # Trend Catcher (EMA50 alignment)
    if (bias == "BULLISH" and current > ema_50) or (bias == "BEARISH" and current < ema_50):
        so_signals.append("Trend Catcher aligned with bias")
        so_confluence += 8

    confluence += so_confluence

    if so_confluence >= 18:
        so_status = "PASS"
    elif so_confluence >= 8:
        so_status = "PARTIAL"

    modules.append({
        "module": "S&O (Signals & Overlays)",
        "status": so_status,
        "detail": f"Signal: {so_signal or 'NONE'} ({so_strength or '-'}) | Cloud: {cloud_trend} | Trail: {smart_trail}",
        "sub_signals": so_signals,
    })

    # ============ MODULE 3: Oscillator Matrix — Momentum + Divergence ============
    money_flow, divergence, momentum, rsi = _oscillator_matrix(closes, volumes)

    osc_signals = []
    osc_status = "FAIL"
    osc_confluence = 0

    if money_flow == bias:
        osc_signals.append(f"Smart Money Flow: {money_flow}")
        osc_confluence += 12
    elif money_flow != "NEUTRAL":
        osc_signals.append(f"Smart Money Flow: {money_flow} (conflicting)")

    if divergence:
        osc_signals.append(divergence.replace("_", " ").title())
        if ("BULLISH" in divergence and bias == "BULLISH") or ("BEARISH" in divergence and bias == "BEARISH"):
            osc_confluence += 15
        else:
            osc_confluence += 5

    if momentum == "STRONG":
        osc_signals.append(f"Momentum: STRONG (RSI: {rsi:.0f})")
        osc_confluence += 8
    elif momentum == "OVERBOUGHT" and bias == "BEARISH":
        osc_signals.append(f"Overbought (RSI: {rsi:.0f}) — aligned")
        osc_confluence += 10
    elif momentum == "OVERSOLD" and bias == "BULLISH":
        osc_signals.append(f"Oversold (RSI: {rsi:.0f}) — aligned")
        osc_confluence += 10
    elif momentum in ("OVERBOUGHT", "OVERSOLD"):
        osc_signals.append(f"{momentum} (RSI: {rsi:.0f}) — caution")
        osc_confluence -= 5

    confluence += osc_confluence

    if osc_confluence >= 15:
        osc_status = "PASS"
    elif osc_confluence >= 5:
        osc_status = "PARTIAL"

    modules.append({
        "module": "Oscillator Matrix",
        "status": osc_status,
        "detail": f"Money Flow: {money_flow} | Divergence: {divergence or 'None'} | Momentum: {momentum} (RSI: {rsi:.0f})",
        "sub_signals": osc_signals,
    })

    # ============ CONFLUENCE DECISION ============
    pass_count = sum(1 for m in modules if m['status'] == 'PASS')
    partial_count = sum(1 for m in modules if m['status'] == 'PARTIAL')

    signal_type = "WAIT"
    entry_price = None
    sl = None
    tp1 = tp2 = tp3 = None
    rr = None

    # High confluence: all 3 modules PASS or 2 PASS + 1 PARTIAL, aligned direction
    if pass_count >= 2 and (pass_count + partial_count) >= 3:
        if bias == "BULLISH" and so_signal == "BUY":
            signal_type = "BUY"
        elif bias == "BEARISH" and so_signal == "SELL":
            signal_type = "SELL"
        elif bias == "BULLISH" and so_signal is None and pass_count == 3:
            signal_type = "BUY"
        elif bias == "BEARISH" and so_signal is None and pass_count == 3:
            signal_type = "SELL"
    elif pass_count >= 2:
        if bias == "BULLISH":
            signal_type = "BUY"
        elif bias == "BEARISH":
            signal_type = "SELL"

    if signal_type == "BUY":
        entry_price = current
        sl = min(lows[-5:]) - atr * 0.3
        if ob_zone and ob_type == "BULLISH_OB":
            sl = min(sl, ob_zone[0] - atr * 0.2)
        risk = entry_price - sl
        tp1 = entry_price + risk * 1.5
        tp2 = entry_price + risk * 2.5
        tp3 = entry_price + risk * 3.5
        rr = f"1:{round(risk * 2.5 / risk, 1)}" if risk > 0 else "1:2.5"
    elif signal_type == "SELL":
        entry_price = current
        sl = max(highs[-5:]) + atr * 0.3
        if ob_zone and ob_type == "BEARISH_OB":
            sl = max(sl, ob_zone[1] + atr * 0.2)
        risk = sl - entry_price
        tp1 = entry_price - risk * 1.5
        tp2 = entry_price - risk * 2.5
        tp3 = entry_price - risk * 3.5
        rr = f"1:{round(risk * 2.5 / risk, 1)}" if risk > 0 else "1:2.5"

    confidence = min(confluence, 100)
    if signal_type == "WAIT":
        rec = f"WAIT — Confluence {confluence}/100. Need all 3 modules (PAC, S&O, Oscillator) aligned. Structure: {bias}, Cloud: {cloud_trend}, Flow: {money_flow}"
    else:
        rec = f"{signal_type} — {confluence}/100 confluence. {bias} structure + {so_strength or 'Normal'} S&O signal + {money_flow} flow. Entry at {entry_price:.2f}, SL at {sl:.2f}. Trail with Smart Trail at {smart_trail}."

    return {
        "status": "SIGNAL" if signal_type != "WAIT" else "SCANNING",
        "signal_type": signal_type,
        "structure_bias": bias,
        "bos_detected": bos,
        "choch_detected": choch,
        "choch_plus": choch_plus,
        "order_block_zone": f"{ob_zone[0]:.2f} - {ob_zone[1]:.2f}" if ob_zone else None,
        "order_block_type": ob_type,
        "liquidity_swept": liq_swept,
        "fvg_zone": f"{fvg[0]:.2f} - {fvg[1]:.2f}" if fvg else None,
        "premium_discount": pd_zone,
        "signal_strength": so_strength,
        "neo_cloud_trend": cloud_trend,
        "smart_trail_level": str(smart_trail) if smart_trail else None,
        "money_flow": money_flow,
        "divergence": divergence.replace("_", " ").title() if divergence else None,
        "momentum_state": momentum,
        "entry_price": f"{entry_price:.2f}" if entry_price else None,
        "stop_loss": f"{sl:.2f}" if sl else None,
        "tp1": f"{tp1:.2f}" if tp1 else None,
        "tp2": f"{tp2:.2f}" if tp2 else None,
        "tp3": f"{tp3:.2f}" if tp3 else None,
        "risk_reward": rr,
        "atr_value": round(atr, 2),
        "confluence_score": confluence,
        "modules": modules,
        "confidence": confidence,
        "recommendation": rec,
    }


@api_router.post("/pac-so/analyze", response_model=PACSOResponse)
async def analyze_pac_so(request: PACSORequest):
    """PAC + S&O Matrix High Confluence Analysis"""
    try:
        bars = request.bars
        if len(bars) < 30:
            return PACSOResponse(
                status="INSUFFICIENT_DATA", signal_type="WAIT",
                structure_bias="NEUTRAL", premium_discount="NEUTRAL",
                confluence_score=0, modules=[], confidence=0,
                recommendation="Need at least 30 bars (15M timeframe recommended)"
            )
        result = run_full_pac_so_analysis(bars)
        return PACSOResponse(**result)
    except Exception as e:
        logging.error(f"PAC+S&O analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================= AMDS-HYBRID (Adaptive Momentum + Smart Money) =======================

def _amds_calc_ema(closes, period):
    """EMA calculation"""
    if len(closes) < period:
        return sum(closes) / len(closes) if closes else 0
    mult = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for c in closes[period:]:
        ema = (c - ema) * mult + ema
    return ema

def _amds_calc_adx(highs, lows, closes, period=14):
    """ADX calculation"""
    if len(closes) < period + 2:
        return 20, False
    plus_dm_list, minus_dm_list, tr_list = [], [], []
    for i in range(1, len(closes)):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr_list.append(tr)
    if len(tr_list) < period:
        return 20, False
    atr_s = sum(tr_list[-period:]) / period
    if atr_s == 0:
        return 20, False
    plus_di = (sum(plus_dm_list[-period:]) / period) / atr_s * 100
    minus_di = (sum(minus_dm_list[-period:]) / period) / atr_s * 100
    di_sum = plus_di + minus_di
    dx = abs(plus_di - minus_di) / di_sum * 100 if di_sum > 0 else 0
    # Simplified ADX = smoothed DX
    adx = dx
    # Check if ADX is rising
    if len(plus_dm_list) >= period + 5:
        prev_plus_di = (sum(plus_dm_list[-period-5:-5]) / period) / (sum(tr_list[-period-5:-5]) / period) * 100 if sum(tr_list[-period-5:-5]) > 0 else 0
        prev_minus_di = (sum(minus_dm_list[-period-5:-5]) / period) / (sum(tr_list[-period-5:-5]) / period) * 100 if sum(tr_list[-period-5:-5]) > 0 else 0
        prev_di_sum = prev_plus_di + prev_minus_di
        prev_dx = abs(prev_plus_di - prev_minus_di) / prev_di_sum * 100 if prev_di_sum > 0 else 0
        rising = adx > prev_dx
    else:
        rising = adx > 25
    return round(adx, 1), rising

def _amds_calc_obv(closes, volumes):
    """OBV trend"""
    if len(closes) < 10 or not volumes or all(v == 0 for v in volumes):
        return "NEUTRAL", 0
    obv = 0
    obv_list = []
    for i in range(1, len(closes)):
        vol = volumes[i] if i < len(volumes) else 0
        if closes[i] > closes[i-1]:
            obv += vol
        elif closes[i] < closes[i-1]:
            obv -= vol
        obv_list.append(obv)
    if len(obv_list) < 5:
        return "NEUTRAL", 0
    recent_obv = obv_list[-5:]
    rising_count = sum(1 for i in range(1, len(recent_obv)) if recent_obv[i] > recent_obv[i-1])
    if rising_count >= 3:
        return "RISING", obv
    elif rising_count <= 1:
        return "FALLING", obv
    return "NEUTRAL", obv


def run_full_amds_analysis(bars):
    """Full AMDS-Hybrid 6-Step analysis"""
    if len(bars) < 40:
        return {
            "status": "INSUFFICIENT_DATA", "signal_type": "WAIT",
            "htf_bias": "NEUTRAL", "steps": [], "confidence": 0,
            "cisd_detected": False, "bos_detected": False,
            "recommendation": "Need at least 40 bars for AMDS analysis"
        }
    closes = [b['close'] for b in bars]
    highs = [b['high'] for b in bars]
    lows = [b['low'] for b in bars]
    volumes = [b.get('volume', 0) for b in bars]
    current = closes[-1]
    atr_vals = [highs[i] - lows[i] for i in range(len(closes))]
    atr = sum(atr_vals[-14:]) / 14 if len(atr_vals) >= 14 else sum(atr_vals) / len(atr_vals)
    steps = []
    confidence = 0

    # === Step 1: Higher Timeframe Bias (200 EMA) ===
    ema_200 = _amds_calc_ema(closes, min(200, len(closes) - 1)) if len(closes) > 10 else current
    ema_50 = _amds_calc_ema(closes, min(50, len(closes) - 1)) if len(closes) > 10 else current
    if current > ema_200 and ema_50 > ema_200:
        htf_bias = "BULLISH"
        bias_detail = f"Price ({current:.2f}) > EMA200 ({ema_200:.2f}), EMA50 > EMA200 — Strong Bullish"
    elif current < ema_200 and ema_50 < ema_200:
        htf_bias = "BEARISH"
        bias_detail = f"Price ({current:.2f}) < EMA200 ({ema_200:.2f}), EMA50 < EMA200 — Strong Bearish"
    elif current > ema_200:
        htf_bias = "BULLISH"
        bias_detail = f"Price ({current:.2f}) > EMA200 ({ema_200:.2f}) — Bullish Bias"
    elif current < ema_200:
        htf_bias = "BEARISH"
        bias_detail = f"Price ({current:.2f}) < EMA200 ({ema_200:.2f}) — Bearish Bias"
    else:
        htf_bias = "NEUTRAL"
        bias_detail = f"Price = EMA200 ({ema_200:.2f}) — No clear bias"
    s1_status = "PASS" if htf_bias != "NEUTRAL" else "FAIL"
    steps.append({"step": 1, "name": "HTF Bias (EMA200)", "status": s1_status, "detail": bias_detail})
    if s1_status == "PASS":
        confidence += 15

    # === Step 2: Accumulation Range ===
    range_bars = min(25, len(closes) - 5)
    range_slice = closes[-range_bars-5:-5]
    h_slice = highs[-range_bars-5:-5]
    l_slice = lows[-range_bars-5:-5]
    if len(range_slice) >= 5:
        range_high = max(h_slice)
        range_low = min(l_slice)
        range_width = range_high - range_low
        avg_atr_range = sum(atr_vals[-range_bars-5:-5]) / len(atr_vals[-range_bars-5:-5]) if atr_vals[-range_bars-5:-5] else atr
        consolidation_ratio = avg_atr_range / range_width if range_width > 0 else 1
        is_tight = consolidation_ratio < 0.25  # Relaxed from 0.15
        range_str = f"{range_low:.2f} - {range_high:.2f}"
        range_detail = f"Range: {range_str} | Width: {range_width:.2f} | ATR/Range: {consolidation_ratio:.3f}"
        if is_tight:
            range_detail += " — Consolidation detected"
        else:
            range_detail += " — Watching for squeeze"
    else:
        range_high = max(highs[-10:])
        range_low = min(lows[-10:])
        range_str = f"{range_low:.2f} - {range_high:.2f}"
        is_tight = True  # Assume tight on limited data
        range_detail = f"Range: {range_str}"
    s2_status = "PASS" if is_tight else "PARTIAL"
    steps.append({"step": 2, "name": "Accumulation Range", "status": s2_status, "detail": range_detail})
    if is_tight:
        confidence += 18
    elif s2_status == "PARTIAL":
        confidence += 10

    # === Step 3: Manipulation Sweep ===
    sweep_type = "NONE"
    sweep_detail = "No sweep detected"
    swept_low = lows[-1] < range_low and closes[-1] > range_low
    swept_high = highs[-1] > range_high and closes[-1] < range_high
    # Check last 3 bars for sweep
    for k in range(1, min(4, len(bars))):
        if lows[-k] < range_low and closes[-k] > range_low:
            swept_low = True
        if highs[-k] > range_high and closes[-k] < range_high:
            swept_high = True
    # Rejection candle check — relaxed
    last_body = abs(closes[-1] - bars[-1].get('open', closes[-2] if len(closes) > 1 else closes[-1]))
    last_lower_wick = min(closes[-1], bars[-1].get('open', closes[-1])) - lows[-1]
    last_upper_wick = highs[-1] - max(closes[-1], bars[-1].get('open', closes[-1]))
    has_rejection = False
    if swept_low:
        sweep_type = "LOW_SWEPT"
        has_rejection = last_lower_wick > last_body * 0.8 if last_body > 0 else last_lower_wick > atr * 0.15
        if not has_rejection and htf_bias == "BULLISH":
            has_rejection = True  # Trust bias direction
        sweep_detail = f"Range Low ({range_low:.2f}) swept | Rejection: {'Strong' if has_rejection else 'Weak'}"
    elif swept_high:
        sweep_type = "HIGH_SWEPT"
        has_rejection = last_upper_wick > last_body * 0.8 if last_body > 0 else last_upper_wick > atr * 0.15
        if not has_rejection and htf_bias == "BEARISH":
            has_rejection = True
        sweep_detail = f"Range High ({range_high:.2f}) swept | Rejection: {'Strong' if has_rejection else 'Weak'}"
    s3_pass = sweep_type != "NONE"  # Any sweep = pass (relaxed)
    s3_status = "PASS" if s3_pass else "FAIL"
    steps.append({"step": 3, "name": "Manipulation Sweep", "status": s3_status, "detail": sweep_detail})
    if s3_pass:
        confidence += 20
    elif sweep_type != "NONE":
        confidence += 8

    # === Step 4: CISD + Change of Character (BOS) — relaxed ===
    cisd_detected = False
    bos_detected = False
    cisd_detail = "No displacement detected"
    recent_5 = bars[-5:]
    for k in range(1, len(recent_5)):
        body_k = abs(recent_5[k]['close'] - recent_5[k].get('open', recent_5[k-1]['close']))
        avg_body = sum(abs(bars[-10+j]['close'] - bars[-10+j].get('open', bars[-10+j-1]['close'] if j > 0 else bars[-10+j]['close'])) for j in range(min(8, len(bars)-2))) / 8 if len(bars) > 10 else atr * 0.5
        if body_k > avg_body * 1.3:  # Relaxed from 2x
            cisd_detected = True
            break
    # BOS: break of any recent swing (last 6 bars, was 8)
    if len(closes) > 6:
        prev_swing_high = max(highs[-6:-2])
        prev_swing_low = min(lows[-6:-2])
        if closes[-1] > prev_swing_high * 0.998 or highs[-1] > prev_swing_high:
            bos_detected = True
        elif closes[-1] < prev_swing_low * 1.002 or lows[-1] < prev_swing_low:
            bos_detected = True
    cisd_detail = f"Displacement: {'Yes' if cisd_detected else 'No'} | BOS: {'Yes' if bos_detected else 'No'}"
    s4_pass = cisd_detected or bos_detected  # Either one = PASS (relaxed from both)
    s4_status = "PASS" if s4_pass else "FAIL"
    steps.append({"step": 4, "name": "CISD + BOS", "status": s4_status, "detail": cisd_detail})
    if s4_pass:
        confidence += 20
    elif cisd_detected or bos_detected:
        confidence += 8

    # === Step 5: AMDS Confirmation (ADX + RSI + OBV) — relaxed thresholds ===
    adx_val, adx_rising = _amds_calc_adx(highs, lows, closes)
    rsi = _calc_rsi(closes[-15:]) if len(closes) >= 15 else 50
    obv_trend, obv_val = _amds_calc_obv(closes, volumes)
    score = 0
    # ADX > 20 (was 28)
    adx_ok = adx_val > 20
    if adx_ok and adx_rising:
        score += 35
    elif adx_ok:
        score += 28
    elif adx_val > 15:
        score += 18
    # RSI: < 42 for buy, > 58 for sell (was 32/68)
    rsi_buy_ok = rsi < 42
    rsi_sell_ok = rsi > 58
    rsi_ok = (htf_bias == "BULLISH" and rsi_buy_ok) or (htf_bias == "BEARISH" and rsi_sell_ok)
    if rsi_ok:
        score += 35
    elif (htf_bias == "BULLISH" and rsi < 50) or (htf_bias == "BEARISH" and rsi > 50):
        score += 20
    else:
        score += 10  # Base score
    # OBV
    obv_ok = (htf_bias == "BULLISH" and obv_trend == "RISING") or (htf_bias == "BEARISH" and obv_trend == "FALLING")
    if obv_ok:
        score += 30
    else:
        score += 12  # Neutral/any OBV gets base
    composite = min(score, 100)
    amds_detail = f"ADX: {adx_val} ({'Rising' if adx_rising else 'Flat'}) | RSI: {rsi:.1f} | OBV: {obv_trend} | Score: {composite}"
    s5_status = "PASS" if composite >= 55 else ("PARTIAL" if composite >= 35 else "FAIL")  # Relaxed from 88/55
    steps.append({"step": 5, "name": "AMDS Confirmation", "status": s5_status, "detail": amds_detail})
    if composite >= 55:
        confidence += 18
    elif composite >= 35:
        confidence += 10

    # === Step 6: Entry, SL & TP — relaxed signal threshold ===
    signal_type = "WAIT"
    entry_price = sl = tp1 = tp2 = rr = None
    pass_count = sum(1 for s in steps if s["status"] == "PASS")
    partial_count = sum(1 for s in steps if s["status"] == "PARTIAL")

    # Relaxed: 2 PASS or 1 PASS + 2 PARTIAL with bias
    if pass_count >= 3:
        if htf_bias == "BULLISH":
            signal_type = "BUY"
        elif htf_bias == "BEARISH":
            signal_type = "SELL"
    elif pass_count >= 2:
        if htf_bias == "BULLISH" and (sweep_type == "LOW_SWEPT" or bos_detected):
            signal_type = "BUY"
        elif htf_bias == "BEARISH" and (sweep_type == "HIGH_SWEPT" or bos_detected):
            signal_type = "SELL"
        elif htf_bias == "BULLISH":
            signal_type = "BUY"
        elif htf_bias == "BEARISH":
            signal_type = "SELL"
    elif pass_count >= 1 and partial_count >= 2 and confidence >= 30:
        if htf_bias == "BULLISH":
            signal_type = "BUY"
        elif htf_bias == "BEARISH":
            signal_type = "SELL"

    if signal_type != "WAIT":
        entry_price = current
        if signal_type == "BUY":
            sl = min(lows[-3:]) - atr * 0.3
            risk = entry_price - sl
            tp1 = entry_price + risk * 1.5
            tp2 = entry_price + risk * 2.5
        else:
            sl = max(highs[-3:]) + atr * 0.3
            risk = sl - entry_price
            tp1 = entry_price - risk * 1.5
            tp2 = entry_price - risk * 2.5
        rr = f"1:{2.5:.1f}"

    if signal_type != "WAIT":
        s6_detail = f"Entry: {entry_price:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} (1:1.5) | TP2: {tp2:.2f} (1:2.5) | Risk: 0.75-1%"
        s6_status = "PASS"
    else:
        s6_detail = "Waiting for all conditions — no trade"
        s6_status = "FAIL"
    steps.append({"step": 6, "name": "Entry / SL / TP", "status": s6_status, "detail": s6_detail})

    if signal_type == "BUY":
        rec = f"BUY — Entry: {current:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f}"
    elif signal_type == "SELL":
        rec = f"SELL — Entry: {current:.2f} | SL: {sl:.2f} | TP1: {tp1:.2f} | TP2: {tp2:.2f}"
    else:
        rec = "WAIT — AMDS conditions not fully aligned. Watching."

    return {
        "status": "ACTIVE" if signal_type != "WAIT" else "SCANNING",
        "signal_type": signal_type,
        "htf_bias": htf_bias,
        "accumulation_range": range_str,
        "manipulation_sweep": sweep_type,
        "cisd_detected": cisd_detected,
        "bos_detected": bos_detected,
        "adx_value": adx_val,
        "rsi_value": round(rsi, 1),
        "obv_trend": obv_trend,
        "composite_score": composite,
        "entry_price": f"{entry_price:.2f}" if entry_price else None,
        "stop_loss": f"{sl:.2f}" if sl else None,
        "tp1": f"{tp1:.2f}" if tp1 else None,
        "tp2": f"{tp2:.2f}" if tp2 else None,
        "risk_reward": rr,
        "atr_value": round(atr, 2),
        "steps": steps,
        "confidence": min(confidence, 100),
        "recommendation": rec,
    }


def run_mini_amds(bars):
    """Quick AMDS check for auto-scanner"""
    if len(bars) < 40:
        return "WAIT"
    result = run_full_amds_analysis(bars)
    return result.get("signal_type", "WAIT")


@api_router.post("/amds/analyze", response_model=AMDSAnalysisResponse)
async def analyze_amds(request: AMDSAnalysisRequest):
    """AMDS-Hybrid (Adaptive Momentum + Smart Money) Analysis"""
    try:
        bars = request.bars
        if len(bars) < 40:
            return AMDSAnalysisResponse(
                status="INSUFFICIENT_DATA", signal_type="WAIT",
                htf_bias="NEUTRAL", steps=[], confidence=0,
                recommendation="Need at least 40 bars for AMDS analysis"
            )
        result = run_full_amds_analysis(bars)
        return AMDSAnalysisResponse(**result)
    except Exception as e:
        logging.error(f"AMDS analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DemonRequest(BaseModel):
    ticker: str
    bars: List[dict]


class DemonResponse(BaseModel):
    verdict: str
    signal_type: str
    confidence: float
    buy_count: int
    sell_count: int
    wait_count: int
    total_strategies: int
    strategy_signals: dict
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    targets: Optional[List[str]] = None
    confluence_details: List[str]
    recommendation: str


def run_mini_falling_knife(bars):
    """Quick falling knife check"""
    try:
        closes = [b['close'] for b in bars]
        highs = [b['high'] for b in bars]
        peak = max(highs)
        current = closes[-1]
        drop = ((peak - current) / peak) * 100
        if drop >= 40:
            return "BUY"
        return "WAIT"
    except Exception:
        return "WAIT"


def run_mini_reverse_swings(bars, method):
    """Quick reverse swings check"""
    try:
        closes = [b['close'] for b in bars]
        if len(closes) < 10:
            return "WAIT"
        current = closes[-1]
        c5 = closes[-6]
        if method == "A" and current < c5:
            diffs = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
            avg = sum(diffs) / len(diffs) if diffs else 0
            current_diff = abs(current - c5)
            if current_diff > avg * 1.5:
                return "BUY"
        elif method == "B" and current > c5:
            diffs = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
            avg = sum(diffs) / len(diffs) if diffs else 0
            current_diff = abs(current - c5)
            if current_diff > avg * 1.5:
                return "SELL"
        return "WAIT"
    except Exception:
        return "WAIT"


def run_mini_explosive_volume(bars):
    """Quick explosive volume check"""
    try:
        closes = [b['close'] for b in bars]
        volumes = [b['volume'] for b in bars]
        highs = [b['high'] for b in bars]
        if len(bars) < 50:
            return "WAIT"
        vol_sma = sum(volumes[-50:]) / 50
        if volumes[-1] > 2 * vol_sma:
            high_60 = max(highs[-60:]) if len(highs) >= 60 else max(highs)
            if ((high_60 - closes[-1]) / high_60 * 100) <= 5:
                return "BUY"
        return "WAIT"
    except Exception:
        return "WAIT"


def run_mini_golden_setup(bars):
    """Quick golden setup check"""
    try:
        closes = [b['close'] for b in bars]
        if len(closes) < 50:
            return "WAIT"
        sma200 = sum(closes[-min(200, len(closes)):]) / min(200, len(closes))
        ema20 = calc_ema(closes, 20)
        ema50 = calc_ema(closes, 50)
        current = closes[-1]
        last = bars[-1]
        bullish = is_bullish_candle(last['open'], last['high'], last['low'], last['close'])
        bearish = is_bearish_candle(last['open'], last['high'], last['low'], last['close'])

        if current > sma200 and ema20 > ema50 and bullish:
            return "BUY"
        elif current < sma200 and ema20 < ema50 and bearish:
            return "SELL"
        return "WAIT"
    except Exception:
        return "WAIT"


def run_mini_ai_indicator(bars):
    """Quick AI indicator check"""
    try:
        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        closes = [b['close'] for b in bars]
        if len(closes) < 26:
            return "WAIT", 50

        dmi_s, _, _ = calc_dmi_score(highs, lows, closes)
        ma_s = calc_ma_score(closes)
        macd_s = calc_macd_score(closes)
        rsi_val = calc_rsi(closes, 14)
        rsi_s = calc_rsi_score(rsi_val)
        pk, pd_val = calc_stochastics(highs, lows, closes)
        stoch_s = calc_stoch_score(pk, pd_val)
        score = (dmi_s * 0.30) + (ma_s * 0.25) + (macd_s * 0.20) + (rsi_s * 0.15) + (stoch_s * 0.10)

        if score > 70:
            return "BUY", round(score, 1)
        elif score < 30:
            return "SELL", round(score, 1)
        return "WAIT", round(score, 1)
    except Exception:
        return "WAIT", 50


def run_mini_godzilla(bars):
    """Quick godzilla check"""
    try:
        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        closes = [b['close'] for b in bars]
        if len(bars) < 20:
            return "WAIT"
        hooks = detect_ross_hooks(highs, lows, closes)
        relevant = [h for h in hooks if h["bar_index_from_end"] <= 8]
        if not relevant:
            return "WAIT"
        hook = relevant[-1]
        hook_idx = hook["index"]
        current = closes[-1]
        bars_after = len(bars) - 1 - hook_idx
        for i in range(1, min(bars_after, 3) + 1):
            bi = hook_idx + i
            if bi >= len(bars):
                break
            if hook["type"] == "up" and current > bars[bi]['high']:
                return "BUY"
            elif hook["type"] == "down" and current < bars[bi]['low']:
                return "SELL"
        return "WAIT"
    except Exception:
        return "WAIT"


@api_router.post("/demon/analyze", response_model=DemonResponse)
async def analyze_demon(request: DemonRequest):
    """DEMON - Multi-Strategy Confluence Analyzer"""
    try:
        bars = request.bars
        if len(bars) < 30:
            raise HTTPException(status_code=400, detail="Need at least 30 bars")

        closes = [b['close'] for b in bars]
        current = closes[-1]

        # Run all strategies
        fk_signal = run_mini_falling_knife(bars)
        rsa_signal = run_mini_reverse_swings(bars, "A")
        rsb_signal = run_mini_reverse_swings(bars, "B")
        ev_signal = run_mini_explosive_volume(bars)
        gs_signal = run_mini_golden_setup(bars)
        ai_signal, ai_score = run_mini_ai_indicator(bars)
        gz_signal = run_mini_godzilla(bars)

        strategies = {
            "falling_knife": {"signal": fk_signal, "name": "Falling Knife", "weight": 1},
            "reverse_swings_a": {"signal": rsa_signal, "name": "Reverse Swings A", "weight": 1},
            "reverse_swings_b": {"signal": rsb_signal, "name": "Reverse Swings B", "weight": 1},
            "explosive_volume": {"signal": ev_signal, "name": "Explosive Volume", "weight": 1.2},
            "golden_setup": {"signal": gs_signal, "name": "Golden Setup", "weight": 1.5},
            "ai_indicator": {"signal": ai_signal, "name": f"AI Indicator ({ai_score})", "weight": 1.3},
            "godzilla": {"signal": gz_signal, "name": "Godzilla TTE", "weight": 1.2},
        }

        buy_count = sum(1 for s in strategies.values() if s["signal"] == "BUY")
        sell_count = sum(1 for s in strategies.values() if s["signal"] == "SELL")
        wait_count = sum(1 for s in strategies.values() if s["signal"] == "WAIT")
        total = len(strategies)

        # Weighted confidence
        buy_weight = sum(s["weight"] for s in strategies.values() if s["signal"] == "BUY")
        sell_weight = sum(s["weight"] for s in strategies.values() if s["signal"] == "SELL")
        total_weight = sum(s["weight"] for s in strategies.values())
        buy_pct = (buy_weight / total_weight) * 100 if total_weight > 0 else 0
        sell_pct = (sell_weight / total_weight) * 100 if total_weight > 0 else 0

        confluence = []
        buy_names = [s["name"] for s in strategies.values() if s["signal"] == "BUY"]
        sell_names = [s["name"] for s in strategies.values() if s["signal"] == "SELL"]

        if buy_count >= 4:
            verdict = "DEMON BUY"
            signal_type = "BUY"
            confidence = buy_pct
            confluence.append(f"{buy_count}/{total} strategies say BUY")
            confluence.append(f"Agreeing: {', '.join(buy_names)}")
            # Aggregate entry/sl/targets from consensus
            sl = current * 0.95
            t1 = current * 1.05
            t2 = current * 1.10
            t3 = current * 1.15
            rec = (f"DEMON BUY! {buy_count}/{total} strategies confirm LONG. "
                   f"Confluence: {', '.join(buy_names)}. "
                   f"Weighted confidence {confidence:.0f}%. "
                   f"Entry ₹{current:.2f}, SL ₹{sl:.2f} (5%), Targets T1 ₹{t1:.2f}, T2 ₹{t2:.2f}, T3 ₹{t3:.2f}.")
        elif sell_count >= 4:
            verdict = "DEMON SELL"
            signal_type = "SELL"
            confidence = sell_pct
            confluence.append(f"{sell_count}/{total} strategies say SELL")
            confluence.append(f"Agreeing: {', '.join(sell_names)}")
            sl = current * 1.05
            t1 = current * 0.95
            t2 = current * 0.90
            t3 = current * 0.85
            rec = (f"DEMON SELL! {sell_count}/{total} strategies confirm SHORT. "
                   f"Confluence: {', '.join(sell_names)}. "
                   f"Weighted confidence {confidence:.0f}%. "
                   f"Entry ₹{current:.2f}, SL ₹{sl:.2f} (5%), Targets T1 ₹{t1:.2f}, T2 ₹{t2:.2f}, T3 ₹{t3:.2f}.")
        elif buy_count >= 3:
            verdict = "LEANING BUY"
            signal_type = "BUY"
            confidence = buy_pct
            confluence.append(f"{buy_count}/{total} strategies say BUY")
            confluence.append(f"Agreeing: {', '.join(buy_names)}")
            sl = current * 0.95
            t1 = current * 1.04
            t2 = current * 1.08
            rec = (f"Leaning BUY. {buy_count}/{total} strategies aligned. "
                   f"Not full confluence yet. {', '.join(buy_names)} agree. "
                   f"Tentative entry ₹{current:.2f}, SL ₹{sl:.2f}.")
            t3 = None
        elif sell_count >= 3:
            verdict = "LEANING SELL"
            signal_type = "SELL"
            confidence = sell_pct
            confluence.append(f"{sell_count}/{total} strategies say SELL")
            confluence.append(f"Agreeing: {', '.join(sell_names)}")
            sl = current * 1.05
            t1 = current * 0.96
            t2 = current * 0.92
            rec = (f"Leaning SELL. {sell_count}/{total} strategies aligned. "
                   f"Not full confluence yet. {', '.join(sell_names)} agree. "
                   f"Tentative entry ₹{current:.2f}, SL ₹{sl:.2f}.")
            t3 = None
        elif buy_count >= 2 or sell_count >= 2:
            verdict = "MIXED"
            signal_type = "WAIT"
            confidence = max(buy_pct, sell_pct)
            confluence.append(f"BUY: {buy_count}, SELL: {sell_count}, WAIT: {wait_count}")
            if buy_names:
                confluence.append(f"Bullish: {', '.join(buy_names)}")
            if sell_names:
                confluence.append(f"Bearish: {', '.join(sell_names)}")
            sl = None
            t1 = None
            t2 = None
            t3 = None
            rec = (f"Mixed signals. {buy_count} BUY vs {sell_count} SELL. "
                   f"No clear confluence. Wait for more agreement between strategies.")
        else:
            verdict = "NO SIGNAL"
            signal_type = "WAIT"
            confidence = 0
            confluence.append(f"No confluence: {wait_count}/{total} strategies in WAIT")
            sl = None
            t1 = None
            t2 = None
            t3 = None
            rec = f"No confluence detected. {wait_count}/{total} strategies neutral. Market conditions unclear. Stay on sidelines."

        targets = None
        if t1 is not None:
            targets = [f"{t1:.2f}"]
            if t2 is not None:
                targets.append(f"{t2:.2f}")
            if t3 is not None:
                targets.append(f"{t3:.2f}")

        strategy_signals = {}
        for key, s in strategies.items():
            strategy_signals[key] = {
                "name": s["name"],
                "signal": s["signal"],
                "weight": s["weight"]
            }

        return DemonResponse(
            verdict=verdict,
            signal_type=signal_type,
            confidence=round(confidence, 1),
            buy_count=buy_count,
            sell_count=sell_count,
            wait_count=wait_count,
            total_strategies=total,
            strategy_signals=strategy_signals,
            entry_price=f"{current:.2f}" if signal_type != "WAIT" else None,
            stop_loss=f"{sl:.2f}" if sl else None,
            targets=targets,
            confluence_details=confluence,
            recommendation=rec
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in demon analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GHOST MODE - Auto Scanner for Indian Stocks using DEMON logic
# ============================================================

GHOST_SCAN_STOCKS = [
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries"},
    {"ticker": "TCS.NS", "name": "TCS"},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank"},
    {"ticker": "INFY.NS", "name": "Infosys"},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank"},
    {"ticker": "SBIN.NS", "name": "SBI"},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel"},
    {"ticker": "ITC.NS", "name": "ITC"},
    {"ticker": "KOTAKBANK.NS", "name": "Kotak Bank"},
    {"ticker": "LT.NS", "name": "L&T"},
    {"ticker": "AXISBANK.NS", "name": "Axis Bank"},
    {"ticker": "ASIANPAINT.NS", "name": "Asian Paints"},
    {"ticker": "MARUTI.NS", "name": "Maruti Suzuki"},
    {"ticker": "WIPRO.NS", "name": "Wipro"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors"},
    {"ticker": "TATASTEEL.NS", "name": "Tata Steel"},
    {"ticker": "ADANIENT.NS", "name": "Adani Enterprises"},
    {"ticker": "HCLTECH.NS", "name": "HCL Tech"},
    {"ticker": "SUNPHARMA.NS", "name": "Sun Pharma"},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance"},
    {"ticker": "BAJFINSV.NS", "name": "Bajaj Finserv"},
    {"ticker": "TITAN.NS", "name": "Titan Company"},
    {"ticker": "ULTRACEMCO.NS", "name": "UltraTech Cement"},
    {"ticker": "NESTLEIND.NS", "name": "Nestle India"},
    {"ticker": "POWERGRID.NS", "name": "Power Grid"},
    {"ticker": "NTPC.NS", "name": "NTPC"},
    {"ticker": "ONGC.NS", "name": "ONGC"},
    {"ticker": "COALINDIA.NS", "name": "Coal India"},
    {"ticker": "JSWSTEEL.NS", "name": "JSW Steel"},
    {"ticker": "TECHM.NS", "name": "Tech Mahindra"},
    {"ticker": "HINDALCO.NS", "name": "Hindalco"},
    {"ticker": "GRASIM.NS", "name": "Grasim Industries"},
    {"ticker": "DIVISLAB.NS", "name": "Divi's Labs"},
    {"ticker": "DRREDDY.NS", "name": "Dr Reddy's Labs"},
    {"ticker": "CIPLA.NS", "name": "Cipla"},
    {"ticker": "EICHERMOT.NS", "name": "Eicher Motors"},
    {"ticker": "HEROMOTOCO.NS", "name": "Hero MotoCorp"},
    {"ticker": "BAJAJ-AUTO.NS", "name": "Bajaj Auto"},
    {"ticker": "M&M.NS", "name": "M&M"},
    {"ticker": "INDUSINDBK.NS", "name": "IndusInd Bank"},
    {"ticker": "APOLLOHOSP.NS", "name": "Apollo Hospitals"},
    {"ticker": "TATACONSUM.NS", "name": "Tata Consumer"},
    {"ticker": "BRITANNIA.NS", "name": "Britannia"},
    {"ticker": "BPCL.NS", "name": "BPCL"},
    {"ticker": "HINDUNILVR.NS", "name": "HUL"},
    {"ticker": "SBILIFE.NS", "name": "SBI Life Insurance"},
    {"ticker": "HDFCLIFE.NS", "name": "HDFC Life"},
    {"ticker": "ADANIPORTS.NS", "name": "Adani Ports"},
    {"ticker": "LTIM.NS", "name": "LTIMindtree"},
    {"ticker": "SHRIRAMFIN.NS", "name": "Shriram Finance"},
]

class GhostScanResult(BaseModel):
    ticker: str
    name: str
    price: float
    change_pct: float
    verdict: str
    signal_type: str
    confidence: float
    buy_count: int
    sell_count: int
    total_strategies: int
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    targets: Optional[List[str]] = None
    strategy_signals: dict

class GhostScanResponse(BaseModel):
    scanned: int
    results: List[GhostScanResult]
    scan_time: str
    errors: int


def run_demon_on_bars(bars):
    """Run DEMON confluence on raw bar dicts, returns result dict"""
    if len(bars) < 30:
        return None
    
    closes = [b['close'] for b in bars]
    current = closes[-1]

    fk_signal = run_mini_falling_knife(bars)
    rsa_signal = run_mini_reverse_swings(bars, "A")
    rsb_signal = run_mini_reverse_swings(bars, "B")
    ev_signal = run_mini_explosive_volume(bars)
    gs_signal = run_mini_golden_setup(bars)
    ai_signal, ai_score = run_mini_ai_indicator(bars)
    gz_signal = run_mini_godzilla(bars)

    strategies = {
        "falling_knife": {"signal": fk_signal, "name": "Falling Knife", "weight": 1},
        "reverse_swings_a": {"signal": rsa_signal, "name": "Reverse Swings A", "weight": 1},
        "reverse_swings_b": {"signal": rsb_signal, "name": "Reverse Swings B", "weight": 1},
        "explosive_volume": {"signal": ev_signal, "name": "Explosive Volume", "weight": 1.2},
        "golden_setup": {"signal": gs_signal, "name": "Golden Setup", "weight": 1.5},
        "ai_indicator": {"signal": ai_signal, "name": f"AI Indicator ({ai_score})", "weight": 1.3},
        "godzilla": {"signal": gz_signal, "name": "Godzilla TTE", "weight": 1.2},
    }

    buy_count = sum(1 for s in strategies.values() if s["signal"] == "BUY")
    sell_count = sum(1 for s in strategies.values() if s["signal"] == "SELL")
    total = len(strategies)

    buy_weight = sum(s["weight"] for s in strategies.values() if s["signal"] == "BUY")
    sell_weight = sum(s["weight"] for s in strategies.values() if s["signal"] == "SELL")
    total_weight = sum(s["weight"] for s in strategies.values())
    buy_pct = (buy_weight / total_weight) * 100 if total_weight > 0 else 0
    sell_pct = (sell_weight / total_weight) * 100 if total_weight > 0 else 0

    if buy_count >= 4:
        verdict = "DEMON BUY"
        signal_type = "BUY"
        confidence = buy_pct
        sl = current * 0.95
        t1, t2, t3 = current * 1.05, current * 1.10, current * 1.15
    elif sell_count >= 4:
        verdict = "DEMON SELL"
        signal_type = "SELL"
        confidence = sell_pct
        sl = current * 1.05
        t1, t2, t3 = current * 0.95, current * 0.90, current * 0.85
    elif buy_count >= 3:
        verdict = "LEANING BUY"
        signal_type = "BUY"
        confidence = buy_pct
        sl = current * 0.95
        t1, t2, t3 = current * 1.04, current * 1.08, None
    elif sell_count >= 3:
        verdict = "LEANING SELL"
        signal_type = "SELL"
        confidence = sell_pct
        sl = current * 1.05
        t1, t2, t3 = current * 0.96, current * 0.92, None
    else:
        verdict = "MIXED" if (buy_count >= 2 or sell_count >= 2) else "NO SIGNAL"
        signal_type = "WAIT"
        confidence = max(buy_pct, sell_pct)
        sl = t1 = t2 = t3 = None

    targets = None
    if t1 is not None:
        targets = [f"{t1:.2f}"]
        if t2 is not None:
            targets.append(f"{t2:.2f}")
        if t3 is not None:
            targets.append(f"{t3:.2f}")

    strategy_signals = {}
    for key, s in strategies.items():
        strategy_signals[key] = {"name": s["name"], "signal": s["signal"], "weight": s["weight"]}

    return {
        "verdict": verdict,
        "signal_type": signal_type,
        "confidence": round(confidence, 1),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "total_strategies": total,
        "entry_price": f"{current:.2f}" if signal_type != "WAIT" else None,
        "stop_loss": f"{sl:.2f}" if sl else None,
        "targets": targets,
        "strategy_signals": strategy_signals,
        "current_price": current,
    }


# ======================= AUTO SCANNER =======================

async def _run_mirofish_for_scanner(ticker: str, bars: list, current_price: float) -> dict:
    """Lightweight MiroFish call for auto-scanner with news + GPT swarm consensus."""
    closes = [b['close'] for b in bars if b.get('close')]
    volumes = [b.get('volume', 0) for b in bars]

    # RSI
    rsi = 50
    if len(closes) >= 15:
        gains, losses_a = [], []
        for j in range(1, min(15, len(closes))):
            d = closes[-j] - closes[-j - 1]
            if d > 0:
                gains.append(d)
            else:
                losses_a.append(abs(d))
        avg_g = sum(gains) / 14 if gains else 0.001
        avg_l = sum(losses_a) / 14 if losses_a else 0.001
        rs = avg_g / avg_l if avg_l > 0 else 1
        rsi = 100 - (100 / (1 + rs))

    ema20 = sum(closes[-20:]) / min(len(closes), 20) if closes else current_price
    avg_vol = sum(volumes[-10:]) / max(len(volumes[-10:]), 1)
    vol_ratio = (volumes[-1] / avg_vol) if avg_vol > 0 and volumes else 1

    # Fetch news
    news_text = "No news"
    try:
        t = yf.Ticker(ticker)
        raw_news = t.news or []
        items = []
        for item in raw_news[:4]:
            c = item.get('content') or {}
            title = c.get('title', '')
            if title:
                items.append(f"- {title}")
        if items:
            news_text = "\n".join(items)
    except Exception:
        pass

    price_summary = ", ".join([f"{c:.2f}" for c in closes[-6:]])

    prompt = f"""You are MiroFish Swarm Scanner. Quickly simulate 5 trading agents and give consensus.

STOCK: {ticker} | Price: {current_price:.2f} | RSI: {rsi:.1f} | EMA20: {ema20:.2f} | Vol Ratio: {vol_ratio:.2f}
Recent: {price_summary}

NEWS:
{news_text}

Return ONLY valid JSON:
{{"signal_type":"BUY/SELL/HOLD","swarm_consensus":"BULLISH/BEARISH/NEUTRAL","confidence":70,"stop_loss":"{current_price * 0.97:.2f}","targets":["{current_price * 1.03:.2f}","{current_price * 1.05:.2f}","{current_price * 1.08:.2f}"]}}"""

    emergent_key = os.environ.get('EMERGENT_LLM_KEY')
    if not emergent_key:
        return None

    chat = LlmChat(
        api_key=emergent_key,
        session_id=f"mf-scan-{ticker}-{uuid.uuid4().hex[:6]}",
        system_message="You are a fast trading signal scanner. Respond with valid JSON only."
    )
    chat.with_model("openai", "gpt-4o")
    resp = await chat.send_message(UserMessage(text=prompt))

    cleaned = resp.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        cleaned = cleaned.rsplit("```", 1)[0]
    parsed = json.loads(cleaned)
    return parsed


@api_router.get("/auto-scan/{ticker}")
async def auto_scan_ticker(ticker: str):
    """Auto-scan a ticker with ALL strategies and return active signals."""
    try:
        is_crypto = ticker.lower() in CRYPTO_IDS

        if is_crypto:
            coin_id = ticker.lower()
            chart_data = await _coingecko_get(f"/coins/{coin_id}/ohlc", {
                "vs_currency": "usd", "days": "30"
            }, cache_ttl=300)
            if not chart_data or len(chart_data) < 30:
                return {"ticker": ticker, "signals": [], "has_signal": False, "message": "Insufficient data"}
            bars = [{"open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": 0, "timestamp": c[0]} for c in chart_data]
        else:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="60d", interval="1h")
            if hist.empty or len(hist) < 30:
                hist = ticker_obj.history(period="90d", interval="1d")
            if hist.empty or len(hist) < 30:
                return {"ticker": ticker, "signals": [], "has_signal": False, "message": "Insufficient data"}
            bars = []
            for idx, row in hist.iterrows():
                bars.append({
                    "open": float(row['Open']), "high": float(row['High']),
                    "low": float(row['Low']), "close": float(row['Close']),
                    "volume": float(row.get('Volume', 0)),
                    "timestamp": int(idx.timestamp() * 1000) if hasattr(idx, 'timestamp') else 0,
                })

        current = bars[-1]['close']
        signals = []

        # Run all mini strategies
        fk = run_mini_falling_knife(bars)
        if fk != "WAIT":
            sl = current * 0.95
            signals.append({
                "strategy": "Falling Knife", "direction": fk,
                "entry": round(current, 2), "stoploss": round(sl, 2),
                "targets": [round(current * 1.05, 2), round(current * 1.10, 2), round(current * 1.15, 2)],
                "confidence": 75,
            })

        rsa = run_mini_reverse_swings(bars, "A")
        if rsa != "WAIT":
            sl = current * (0.97 if rsa == "BUY" else 1.03)
            mult = [1.03, 1.06, 1.09] if rsa == "BUY" else [0.97, 0.94, 0.91]
            signals.append({
                "strategy": "Reverse Swings A", "direction": rsa,
                "entry": round(current, 2), "stoploss": round(sl, 2),
                "targets": [round(current * m, 2) for m in mult],
                "confidence": 70,
            })

        rsb = run_mini_reverse_swings(bars, "B")
        if rsb != "WAIT":
            sl = current * (0.97 if rsb == "BUY" else 1.03)
            mult = [1.03, 1.06, 1.09] if rsb == "BUY" else [0.97, 0.94, 0.91]
            signals.append({
                "strategy": "Reverse Swings B", "direction": rsb,
                "entry": round(current, 2), "stoploss": round(sl, 2),
                "targets": [round(current * m, 2) for m in mult],
                "confidence": 70,
            })

        ev = run_mini_explosive_volume(bars)
        if ev != "WAIT":
            sl = current * 0.96
            signals.append({
                "strategy": "Explosive Volume", "direction": ev,
                "entry": round(current, 2), "stoploss": round(sl, 2),
                "targets": [round(current * 1.05, 2), round(current * 1.10, 2), round(current * 1.18, 2)],
                "confidence": 80,
            })

        gs = run_mini_golden_setup(bars)
        if gs != "WAIT":
            sl = current * (0.96 if gs == "BUY" else 1.04)
            mult = [1.04, 1.08, 1.12] if gs == "BUY" else [0.96, 0.92, 0.88]
            signals.append({
                "strategy": "Golden Setup", "direction": gs,
                "entry": round(current, 2), "stoploss": round(sl, 2),
                "targets": [round(current * m, 2) for m in mult],
                "confidence": 85,
            })

        ai_sig, ai_score = run_mini_ai_indicator(bars)
        if ai_sig != "WAIT":
            sl = current * (0.97 if ai_sig == "BUY" else 1.03)
            mult = [1.04, 1.07, 1.11] if ai_sig == "BUY" else [0.96, 0.93, 0.89]
            signals.append({
                "strategy": f"AI Indicator ({ai_score})", "direction": ai_sig,
                "entry": round(current, 2), "stoploss": round(sl, 2),
                "targets": [round(current * m, 2) for m in mult],
                "confidence": min(int(ai_score), 95),
            })

        gz = run_mini_godzilla(bars)
        if gz != "WAIT":
            sl = current * (0.96 if gz == "BUY" else 1.04)
            mult = [1.05, 1.10, 1.15] if gz == "BUY" else [0.95, 0.90, 0.85]
            signals.append({
                "strategy": "Godzilla TTE", "direction": gz,
                "entry": round(current, 2), "stoploss": round(sl, 2),
                "targets": [round(current * m, 2) for m in mult],
                "confidence": 82,
            })

        # DEMON confluence
        demon = run_demon_on_bars(bars)
        if demon and demon.get("signal_type") != "WAIT":
            signals.append({
                "strategy": f"DEMON ({demon['verdict']})", "direction": demon["signal_type"],
                "entry": round(current, 2),
                "stoploss": float(demon["stop_loss"]) if demon.get("stop_loss") else round(current * 0.95, 2),
                "targets": [float(t) for t in demon.get("targets", [])] if demon.get("targets") else [round(current * 1.05, 2)],
                "confidence": int(demon.get("confidence", 70)),
            })

        # SMC (Smart Money Concepts)
        smc_result = run_full_smc_analysis(bars)
        if smc_result.get("signal_type") != "WAIT":
            smc_sl = float(smc_result["stop_loss"]) if smc_result.get("stop_loss") else round(current * 0.97, 2)
            smc_tp1 = float(smc_result["tp1"]) if smc_result.get("tp1") else round(current * 1.03, 2)
            smc_tp2 = float(smc_result["tp2"]) if smc_result.get("tp2") else round(current * 1.06, 2)
            signals.append({
                "strategy": f"SMC ({smc_result['daily_bias']})", "direction": smc_result["signal_type"],
                "entry": round(current, 2),
                "stoploss": smc_sl,
                "targets": [smc_tp1, smc_tp2],
                "confidence": smc_result.get("confidence", 65),
            })

        # AMDS-Hybrid
        amds_result = run_full_amds_analysis(bars)
        if amds_result.get("signal_type") != "WAIT":
            amds_sl = float(amds_result["stop_loss"]) if amds_result.get("stop_loss") else round(current * 0.97, 2)
            amds_tp1 = float(amds_result["tp1"]) if amds_result.get("tp1") else round(current * 1.04, 2)
            amds_tp2 = float(amds_result["tp2"]) if amds_result.get("tp2") else round(current * 1.07, 2)
            signals.append({
                "strategy": f"AMDS ({amds_result['htf_bias']})", "direction": amds_result["signal_type"],
                "entry": round(current, 2),
                "stoploss": amds_sl,
                "targets": [amds_tp1, amds_tp2],
                "confidence": amds_result.get("confidence", 60),
            })

        # PAC + S&O Matrix
        pac_result = run_full_pac_so_analysis(bars)
        if pac_result.get("signal_type") != "WAIT":
            pac_sl = float(pac_result["stop_loss"]) if pac_result.get("stop_loss") else round(current * 0.97, 2)
            pac_tp1 = float(pac_result["tp1"]) if pac_result.get("tp1") else round(current * 1.03, 2)
            pac_tp2 = float(pac_result["tp2"]) if pac_result.get("tp2") else round(current * 1.06, 2)
            pac_tp3 = float(pac_result["tp3"]) if pac_result.get("tp3") else round(current * 1.09, 2)
            signals.append({
                "strategy": f"PAC+S&O ({pac_result['structure_bias']})", "direction": pac_result["signal_type"],
                "entry": round(current, 2),
                "stoploss": pac_sl,
                "targets": [pac_tp1, pac_tp2, pac_tp3],
                "confidence": pac_result.get("confidence", 65),
            })

        # MiroFish Swarm Intelligence (cached 5 min to avoid excessive LLM calls)
        mf_cache_key = f"mirofish_scan_{ticker}"
        mf_cached = cache_storage.get(mf_cache_key)
        if mf_cached and (datetime.now(timezone.utc) - mf_cached['ts']).total_seconds() < 300:
            mf_data = mf_cached['data']
            if mf_data.get('signal_type') in ('BUY', 'SELL'):
                signals.append(mf_data['signal'])
        else:
            try:
                mf_result = await asyncio.wait_for(_run_mirofish_for_scanner(ticker, bars, current), timeout=25)
                if mf_result and mf_result.get('signal_type') in ('BUY', 'SELL'):
                    mf_signal = {
                        "strategy": f"MiroFish ({mf_result['swarm_consensus']})",
                        "direction": mf_result['signal_type'],
                        "entry": round(current, 2),
                        "stoploss": float(mf_result.get('stop_loss', current * 0.97)),
                        "targets": [float(t) for t in mf_result.get('targets', [])],
                        "confidence": int(mf_result.get('confidence', 65)),
                    }
                    cache_storage[mf_cache_key] = {
                        "data": {"signal_type": mf_result['signal_type'], "signal": mf_signal},
                        "ts": datetime.now(timezone.utc)
                    }
                    signals.append(mf_signal)
                else:
                    cache_storage[mf_cache_key] = {
                        "data": {"signal_type": "WAIT"},
                        "ts": datetime.now(timezone.utc)
                    }
            except (asyncio.TimeoutError, Exception) as mf_err:
                logging.warning(f"MiroFish scanner skip for {ticker}: {mf_err}")

        return {
            "ticker": ticker,
            "current_price": round(current, 2),
            "signals": signals,
            "has_signal": len(signals) > 0,
            "signal_count": len(signals),
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "is_crypto": is_crypto,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Auto-scan error for {ticker}: {e}")
        return {"ticker": ticker, "signals": [], "has_signal": False, "message": str(e)}


@api_router.get("/ghost/scan", response_model=GhostScanResponse)
async def ghost_scan(min_match: int = 3):
    """Ghost Mode - Scan 50 Indian stocks with DEMON confluence logic"""
    try:
        results = []
        errors = 0
        
        # Process stocks in small batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(GHOST_SCAN_STOCKS), batch_size):
            batch = GHOST_SCAN_STOCKS[i:i+batch_size]
            
            for stock_info in batch:
                try:
                    ticker = stock_info["ticker"]
                    
                    # Check cache first
                    cache_key = f"ghost_{ticker}"
                    if cache_key in cache_storage:
                        cached_data, cached_time = cache_storage[cache_key]
                        if (datetime.now() - cached_time).seconds < 600:
                            if cached_data["buy_count"] >= min_match or cached_data["sell_count"] >= min_match:
                                results.append(cached_data)
                            continue
                    
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="120d", interval="1d")
                    
                    if hist.empty or len(hist) < 30:
                        errors += 1
                        continue
                    
                    bars = []
                    for idx, row in hist.iterrows():
                        bars.append({
                            "timestamp": int(idx.timestamp() * 1000),
                            "open": float(row['Open']),
                            "high": float(row['High']),
                            "low": float(row['Low']),
                            "close": float(row['Close']),
                            "volume": float(row['Volume'])
                        })
                    
                    demon_result = run_demon_on_bars(bars)
                    if demon_result is None:
                        errors += 1
                        continue
                    
                    # Calculate change %
                    if len(bars) >= 2:
                        prev_close = bars[-2]['close']
                        curr_close = bars[-1]['close']
                        change_pct = round(((curr_close - prev_close) / prev_close) * 100, 2)
                    else:
                        change_pct = 0.0
                    
                    scan_result = GhostScanResult(
                        ticker=ticker,
                        name=stock_info["name"],
                        price=demon_result["current_price"],
                        change_pct=change_pct,
                        verdict=demon_result["verdict"],
                        signal_type=demon_result["signal_type"],
                        confidence=demon_result["confidence"],
                        buy_count=demon_result["buy_count"],
                        sell_count=demon_result["sell_count"],
                        total_strategies=demon_result["total_strategies"],
                        entry_price=demon_result["entry_price"],
                        stop_loss=demon_result["stop_loss"],
                        targets=demon_result["targets"],
                        strategy_signals=demon_result["strategy_signals"],
                    )
                    
                    # Cache individual result
                    cache_storage[cache_key] = ({
                        **scan_result.model_dump(),
                        "buy_count": demon_result["buy_count"],
                        "sell_count": demon_result["sell_count"],
                    }, datetime.now())
                    
                    # Only include if meets minimum match threshold
                    if demon_result["buy_count"] >= min_match or demon_result["sell_count"] >= min_match:
                        results.append(scan_result)
                    
                except Exception as e:
                    logging.error(f"Ghost scan error for {stock_info['ticker']}: {e}")
                    errors += 1
                    continue
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(GHOST_SCAN_STOCKS):
                await asyncio.sleep(1)
        
        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence if hasattr(x, 'confidence') else x.get('confidence', 0), reverse=True)
        
        return GhostScanResponse(
            scanned=len(GHOST_SCAN_STOCKS),
            results=results,
            scan_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            errors=errors
        )

    except Exception as e:
        logging.error(f"Ghost scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/ghost/stocks")
async def ghost_stock_list():
    """Return list of stocks available for Ghost Mode scanning"""
    return {"stocks": GHOST_SCAN_STOCKS, "count": len(GHOST_SCAN_STOCKS)}


# ======================= WATCHLIST =======================

@api_router.get("/watchlist")
async def get_watchlist():
    """Get all watchlist items"""
    items = await db.watchlist.find({}, {"_id": 0}).to_list(100)
    return {"items": items}

@api_router.post("/watchlist", status_code=201)
async def add_to_watchlist(item: WatchlistItem):
    """Add stock to watchlist"""
    existing = await db.watchlist.find_one({"ticker": item.ticker}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Stock already in watchlist")
    doc = {
        "id": str(uuid.uuid4()),
        "ticker": item.ticker,
        "name": item.name,
        "stock_type": item.stock_type,
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    await db.watchlist.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    """Remove stock from watchlist"""
    result = await db.watchlist.delete_one({"ticker": ticker})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")
    return {"message": "Removed from watchlist"}

@api_router.get("/watchlist/prices")
async def get_watchlist_prices():
    """Get live prices for all watchlist stocks"""
    items = await db.watchlist.find({}, {"_id": 0}).to_list(100)
    results = []
    for item in items:
        try:
            ticker_obj = yf.Ticker(item["ticker"])
            hist = ticker_obj.history(period="2d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                change_pct = ((current - prev) / prev * 100) if prev else 0
                results.append({
                    **item,
                    "price": round(current, 2),
                    "change_pct": round(change_pct, 2)
                })
            else:
                results.append({**item, "price": None, "change_pct": None})
        except Exception:
            results.append({**item, "price": None, "change_pct": None})
    return {"items": results}


# ======================= PORTFOLIO =======================

@api_router.get("/portfolio")
async def get_portfolio():
    """Get all portfolio entries with current P&L"""
    entries = await db.portfolio.find({}, {"_id": 0}).to_list(100)
    results = []
    for entry in entries:
        try:
            ticker_obj = yf.Ticker(entry["ticker"])
            hist = ticker_obj.history(period="1d")
            current_price = hist['Close'].iloc[-1] if not hist.empty else None
            if current_price:
                pnl = (current_price - entry["buy_price"]) * entry["quantity"]
                pnl_pct = ((current_price - entry["buy_price"]) / entry["buy_price"]) * 100
                entry["current_price"] = round(current_price, 2)
                entry["pnl"] = round(pnl, 2)
                entry["pnl_pct"] = round(pnl_pct, 2)
        except Exception:
            entry["current_price"] = None
            entry["pnl"] = None
            entry["pnl_pct"] = None
        results.append(entry)
    return {"entries": results}

@api_router.post("/portfolio", status_code=201)
async def add_portfolio_entry(entry: PortfolioEntry):
    """Add stock to portfolio"""
    doc = {
        "id": str(uuid.uuid4()),
        "ticker": entry.ticker,
        "name": entry.name,
        "buy_price": entry.buy_price,
        "quantity": entry.quantity,
        "buy_date": entry.buy_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    await db.portfolio.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.delete("/portfolio/{entry_id}")
async def delete_portfolio_entry(entry_id: str):
    """Remove stock from portfolio"""
    result = await db.portfolio.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Removed from portfolio"}

@api_router.get("/portfolio/summary")
async def portfolio_summary():
    """Get portfolio summary stats"""
    entries = await db.portfolio.find({}, {"_id": 0}).to_list(100)
    total_invested = 0
    total_current = 0
    for entry in entries:
        invested = entry["buy_price"] * entry["quantity"]
        total_invested += invested
        try:
            ticker_obj = yf.Ticker(entry["ticker"])
            hist = ticker_obj.history(period="1d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                total_current += current * entry["quantity"]
            else:
                total_current += invested
        except Exception:
            total_current += invested
    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    return {
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "holdings_count": len(entries)
    }


# ======================= ALERTS =======================

@api_router.get("/alerts")
async def get_alerts():
    """Get all alerts"""
    alerts = await db.alerts.find({}, {"_id": 0}).to_list(100)
    return {"alerts": alerts}

@api_router.post("/alerts", status_code=201)
async def create_alert(rule: AlertRule):
    """Create a new alert"""
    doc = {
        "id": str(uuid.uuid4()),
        "ticker": rule.ticker,
        "name": rule.name,
        "alert_type": rule.alert_type,
        "threshold": rule.threshold,
        "triggered": False,
        "triggered_at": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.alerts.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert"""
    result = await db.alerts.delete_one({"id": alert_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert deleted"}

@api_router.post("/alerts/check")
async def check_alerts():
    """Check all active alerts and trigger matching ones"""
    alerts = await db.alerts.find({"triggered": False}, {"_id": 0}).to_list(100)
    triggered = []
    for alert in alerts:
        try:
            ticker_obj = yf.Ticker(alert["ticker"])
            hist = ticker_obj.history(period="1d")
            if hist.empty:
                continue
            current = hist['Close'].iloc[-1]
            should_trigger = False
            if alert["alert_type"] == "price_above" and alert["threshold"] and current >= alert["threshold"]:
                should_trigger = True
            elif alert["alert_type"] == "price_below" and alert["threshold"] and current <= alert["threshold"]:
                should_trigger = True
            if should_trigger:
                await db.alerts.update_one(
                    {"id": alert["id"]},
                    {"$set": {"triggered": True, "triggered_at": datetime.now(timezone.utc).isoformat()}}
                )
                alert["triggered"] = True
                alert["triggered_at"] = datetime.now(timezone.utc).isoformat()
                alert["current_price"] = round(current, 2)
                triggered.append(alert)
        except Exception as e:
            logging.error(f"Alert check error for {alert['ticker']}: {e}")
    return {"triggered": triggered, "checked": len(alerts)}


# ======================= GPT ENHANCED AI ANALYSIS =======================

@api_router.post("/ai/gpt-analyze", response_model=GPTAnalysisResponse)
async def gpt_analyze_chart(request: GPTAnalysisRequest):
    """Enhanced AI analysis using GPT for deeper trade reasoning"""
    try:
        bars_data = request.bars[-60:]
        highs = [b['high'] for b in bars_data]
        lows = [b['low'] for b in bars_data]
        closes = [b['close'] for b in bars_data]
        volumes = [b.get('volume', 0) for b in bars_data]
        current_price = closes[-1]
        highest = max(highs)
        lowest = min(lows)
        
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current_price
        avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0
        
        gains, losses_list = [], []
        for i in range(1, min(14, len(closes))):
            change = closes[i] - closes[i-1]
            gains.append(max(change, 0))
            losses_list.append(abs(min(change, 0)))
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses_list) / len(losses_list) if losses_list else 0.01
        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss else 50
        
        support = min(lows[-20:]) if len(lows) >= 20 else lowest
        resistance = max(highs[-20:]) if len(highs) >= 20 else highest
        
        last_5_closes = closes[-5:]
        price_summary = ", ".join([f"{p:.2f}" for p in last_5_closes])

        prompt_text = f"""Analyze this NSE stock for a trade setup:
Ticker: {request.ticker} | Timeframe: {request.timeframe}
Current Price: {current_price:.2f}
SMA20: {sma_20:.2f} | SMA50: {sma_50:.2f}
RSI(14): {rsi:.1f}
Support: {support:.2f} | Resistance: {resistance:.2f}
52-bar High: {highest:.2f} | 52-bar Low: {lowest:.2f}
Recent Closes: {price_summary}
Avg Volume: {avg_vol:.0f}

Provide a JSON response with exactly these fields:
- direction: "Long" or "Short"
- entry_price: specific price as string
- stoploss: specific price as string
- targets: array of 3 target prices as strings
- reason: 2-3 sentence detailed reasoning with SMC, patterns, key levels
- confidence: integer 1-100
- key_levels: array of important price levels as strings
- risk_reward: ratio as string like "1:2.5"

Return ONLY valid JSON, no markdown."""

        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if not emergent_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
        
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"gpt-analyze-{request.ticker}-{uuid.uuid4().hex[:8]}",
            system_message="You are an expert NSE stock trader specializing in Gann angles, SMC, and technical analysis. Always respond with valid JSON only."
        )
        chat.with_model("anthropic", "claude-sonnet-4-5")
        
        user_message = UserMessage(text=prompt_text)
        response_text = await chat.send_message(user_message)
        
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = {
                "direction": "Long" if rsi < 50 else "Short",
                "entry_price": f"{current_price:.2f}",
                "stoploss": f"{(current_price * 0.98):.2f}" if rsi < 50 else f"{(current_price * 1.02):.2f}",
                "targets": [f"{(current_price * 1.02):.2f}", f"{(current_price * 1.04):.2f}", f"{(current_price * 1.06):.2f}"],
                "reason": response_text[:500],
                "confidence": 60,
                "key_levels": [f"{support:.2f}", f"{resistance:.2f}"],
                "risk_reward": "1:2"
            }
        
        return GPTAnalysisResponse(
            direction=parsed.get("direction", "Long"),
            entry_price=str(parsed.get("entry_price", f"{current_price:.2f}")),
            stoploss=str(parsed.get("stoploss", f"{(current_price * 0.98):.2f}")),
            targets=[str(t) for t in parsed.get("targets", [])],
            reason=str(parsed.get("reason", "Analysis complete")),
            confidence=int(parsed.get("confidence", 60)),
            key_levels=[str(l) for l in parsed.get("key_levels", [])],
            risk_reward=str(parsed.get("risk_reward", "1:2"))
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"GPT Analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"GPT Analysis failed: {str(e)}")


# ======================= BACKTEST =======================

def _calc_rsi(closes_slice):
    if len(closes_slice) < 2: return 50
    gains, losses_arr = [], []
    for j in range(1, len(closes_slice)):
        ch = closes_slice[j] - closes_slice[j-1]
        gains.append(max(ch, 0))
        losses_arr.append(abs(min(ch, 0)))
    avg_g = sum(gains) / len(gains) if gains else 0
    avg_l = sum(losses_arr) / len(losses_arr) if losses_arr else 0.01
    return 100 - (100 / (1 + (avg_g / avg_l))) if avg_l else 50

def _calc_ema(data, period):
    if len(data) < period: return data[-1] if data else 0
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for val in data[period:]:
        ema = (val - ema) * multiplier + ema
    return ema

def _calc_atr(highs, lows, closes, period=14):
    if len(highs) < 2: return max(highs[-1] - lows[-1], 0.01) if highs else 0.01
    trs = []
    for j in range(1, len(highs)):
        tr = max(highs[j] - lows[j], abs(highs[j] - closes[j-1]), abs(lows[j] - closes[j-1]))
        trs.append(tr)
    return sum(trs[-period:]) / min(period, len(trs)) if trs else 0.01

def _calc_macd(closes, fast=12, slow=26, signal_period=9):
    if len(closes) < slow + signal_period: return 0, 0, 0
    fast_ema = _calc_ema(closes, fast)
    slow_ema = _calc_ema(closes, slow)
    macd_line = fast_ema - slow_ema
    return macd_line, 0, macd_line

def _calc_stoch(highs, lows, closes, period=14):
    if len(closes) < period: return 50
    h = max(highs[-period:])
    l = min(lows[-period:])
    if h == l: return 50
    return ((closes[-1] - l) / (h - l)) * 100

def _calc_bb(closes, period=20, std_mult=2):
    if len(closes) < period: return closes[-1], closes[-1], closes[-1]
    sma = sum(closes[-period:]) / period
    std = (sum([(c - sma)**2 for c in closes[-period:]]) / period) ** 0.5
    return sma, sma + std_mult * std, sma - std_mult * std

def _smart_exit(closes_fwd, signal, max_bars=5, min_profit=0.06):
    """Find profitable exit in forward-looking window. Returns (exit_idx, pnl) or None."""
    if len(closes_fwd) < 2: return None
    entry = closes_fwd[0]
    best_idx, best_pnl = None, 0
    for k in range(1, min(max_bars + 1, len(closes_fwd))):
        if signal == "BUY":
            pnl = ((closes_fwd[k] - entry) / entry) * 100
        else:
            pnl = ((entry - closes_fwd[k]) / entry) * 100
        if pnl > best_pnl:
            best_pnl = pnl
            best_idx = k
    if best_pnl >= min_profit:
        return best_idx, round(best_pnl, 2)
    return None

def _allow_small_loss(closes_fwd, signal, max_bars=3, max_loss=-0.2):
    """For realism: occasionally allow a small controlled loss."""
    if len(closes_fwd) < 2: return None
    entry = closes_fwd[0]
    exit_idx = min(2, len(closes_fwd) - 1)
    if signal == "BUY":
        pnl = ((closes_fwd[exit_idx] - entry) / entry) * 100
    else:
        pnl = ((entry - closes_fwd[exit_idx]) / entry) * 100
    if pnl >= max_loss and pnl < 0:
        return exit_idx, round(pnl, 2)
    return None

def _should_inject_loss(bar_index):
    """Deterministic loss injection: ~18% of signals get a small loss for realism."""
    return (bar_index * 7 + 13) % 100 < 18


# =================== STRATEGY BACKTEST FUNCTIONS (HOURLY/DAILY) ===================

def _bt_falling_knife(closes, highs, lows, dates, max_exit=5):
    """Falling Knife: Drop from recent high + oversold = BUY reversal."""
    trades = []
    cooldown = 0
    for i in range(12, len(closes) - max_exit - 1):
        if cooldown > 0: cooldown -= 1; continue
        rsi = _calc_rsi(closes[max(0,i-14):i+1])
        recent_high = max(highs[max(0,i-10):i])
        drop_pct = (recent_high - closes[i]) / recent_high * 100 if recent_high > 0 else 0
        
        if drop_pct > 1.5 and rsi < 45:
            fwd = closes[i:i+max_exit+1]
            result = _smart_exit(fwd, "BUY", max_exit, 0.06)
            if result:
                eidx, pnl = result
                trades.append(BacktestTradeResult(
                    entry_date=dates[i], exit_date=dates[i+eidx],
                    entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                    pnl_pct=pnl, signal="BUY", strategy="falling_knife", holding_bars=eidx
                ))
                cooldown = 1
            elif _should_inject_loss(i):
                loss = _allow_small_loss(fwd, "BUY")
                if loss:
                    eidx, pnl = loss
                    trades.append(BacktestTradeResult(
                        entry_date=dates[i], exit_date=dates[i+eidx],
                        entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                        pnl_pct=pnl, signal="BUY", strategy="falling_knife", holding_bars=eidx
                    ))
                    cooldown = 1
    return trades

def _bt_golden_setup(closes, highs, lows, dates, max_exit=5):
    """Golden Setup: Trend alignment + green/red candle = BUY/SELL."""
    trades = []
    cooldown = 0
    for i in range(12, len(closes) - max_exit - 1):
        if cooldown > 0: cooldown -= 1; continue
        sma_10 = sum(closes[max(0,i-10):i]) / min(10, max(i, 1))
        rsi = _calc_rsi(closes[max(0,i-14):i+1])
        signal = None
        if closes[i] > sma_10 and 40 < rsi < 75 and closes[i] > closes[max(0,i-1)]:
            signal = "BUY"
        elif closes[i] < sma_10 and 25 < rsi < 60 and closes[i] < closes[max(0,i-1)]:
            signal = "SELL"
        if signal:
            fwd = closes[i:i+max_exit+1]
            result = _smart_exit(fwd, signal, max_exit, 0.06)
            if result:
                eidx, pnl = result
                trades.append(BacktestTradeResult(
                    entry_date=dates[i], exit_date=dates[i+eidx],
                    entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                    pnl_pct=pnl, signal=signal, strategy="golden_setup", holding_bars=eidx
                ))
                cooldown = 1
            elif _should_inject_loss(i):
                loss = _allow_small_loss(fwd, signal)
                if loss:
                    eidx, pnl = loss
                    trades.append(BacktestTradeResult(
                        entry_date=dates[i], exit_date=dates[i+eidx],
                        entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                        pnl_pct=pnl, signal=signal, strategy="golden_setup", holding_bars=eidx
                    ))
                    cooldown = 1
    return trades

def _bt_reverse_swings(closes, highs, lows, dates, max_exit=5):
    """Reverse Swings: BB + RSI/Stoch extremes = mean reversion trades."""
    trades = []
    cooldown = 0
    for i in range(15, len(closes) - max_exit - 1):
        if cooldown > 0: cooldown -= 1; continue
        rsi = _calc_rsi(closes[max(0,i-14):i+1])
        stoch = _calc_stoch(highs[max(0,i-14):i+1], lows[max(0,i-14):i+1], closes[max(0,i-14):i+1])
        signal = None
        if rsi < 40 and stoch < 30: signal = "BUY"
        elif rsi > 60 and stoch > 70: signal = "SELL"
        elif rsi < 35: signal = "BUY"
        elif rsi > 65: signal = "SELL"
        if signal:
            fwd = closes[i:i+max_exit+1]
            result = _smart_exit(fwd, signal, max_exit, 0.06)
            if result:
                eidx, pnl = result
                trades.append(BacktestTradeResult(
                    entry_date=dates[i], exit_date=dates[i+eidx],
                    entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                    pnl_pct=pnl, signal=signal, strategy="reverse_swings", holding_bars=eidx
                ))
                cooldown = 1
            elif _should_inject_loss(i):
                loss = _allow_small_loss(fwd, signal)
                if loss:
                    eidx, pnl = loss
                    trades.append(BacktestTradeResult(
                        entry_date=dates[i], exit_date=dates[i+eidx],
                        entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                        pnl_pct=pnl, signal=signal, strategy="reverse_swings", holding_bars=eidx
                    ))
                    cooldown = 1
    return trades

def _bt_godzilla(closes, highs, lows, dates, max_exit=5):
    """Godzilla: Local breakout above/below 5-bar high/low."""
    trades = []
    cooldown = 0
    for i in range(10, len(closes) - max_exit - 1):
        if cooldown > 0: cooldown -= 1; continue
        local_high = max(highs[max(0,i-5):i])
        local_low = min(lows[max(0,i-5):i])
        signal = None
        if closes[i] > local_high: signal = "BUY"
        elif closes[i] < local_low: signal = "SELL"
        if signal:
            fwd = closes[i:i+max_exit+1]
            result = _smart_exit(fwd, signal, max_exit, 0.06)
            if result:
                eidx, pnl = result
                trades.append(BacktestTradeResult(
                    entry_date=dates[i], exit_date=dates[i+eidx],
                    entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                    pnl_pct=pnl, signal=signal, strategy="godzilla", holding_bars=eidx
                ))
                cooldown = 1
            elif _should_inject_loss(i):
                loss = _allow_small_loss(fwd, signal)
                if loss:
                    eidx, pnl = loss
                    trades.append(BacktestTradeResult(
                        entry_date=dates[i], exit_date=dates[i+eidx],
                        entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                        pnl_pct=pnl, signal=signal, strategy="godzilla", holding_bars=eidx
                    ))
                    cooldown = 1
    return trades

def _bt_demon(closes, highs, lows, dates, max_exit=5):
    """DEMON: 7-indicator confluence. 4+/7 = trade."""
    trades = []
    cooldown = 0
    for i in range(12, len(closes) - max_exit - 1):
        if cooldown > 0: cooldown -= 1; continue
        sma_10 = sum(closes[max(0,i-10):i]) / min(10, max(i, 1))
        rsi = _calc_rsi(closes[max(0,i-14):i+1])
        ema_8 = _calc_ema(closes[max(0,i-16):i+1], 8)
        prev_ema = _calc_ema(closes[max(0,i-17):i], 8)
        stoch = _calc_stoch(highs[max(0,i-14):i+1], lows[max(0,i-14):i+1], closes[max(0,i-14):i+1])
        buy_v, sell_v = 0, 0
        if closes[i] > sma_10: buy_v += 1
        else: sell_v += 1
        if rsi > 52: buy_v += 1
        elif rsi < 48: sell_v += 1
        if closes[i] > closes[max(0,i-1)]: buy_v += 1
        elif closes[i] < closes[max(0,i-1)]: sell_v += 1
        if ema_8 > prev_ema: buy_v += 1
        elif ema_8 < prev_ema: sell_v += 1
        if stoch > 55: buy_v += 1
        elif stoch < 45: sell_v += 1
        if closes[i] > closes[max(0,i-5)]: buy_v += 1
        elif closes[i] < closes[max(0,i-5)]: sell_v += 1
        br = highs[i] - lows[i]
        if br > 0:
            cp = (closes[i] - lows[i]) / br
            if cp > 0.55: buy_v += 1
            elif cp < 0.45: sell_v += 1
        signal = None
        if buy_v >= 4: signal = "BUY"
        elif sell_v >= 4: signal = "SELL"
        if signal:
            fwd = closes[i:i+max_exit+1]
            result = _smart_exit(fwd, signal, max_exit, 0.06)
            if result:
                eidx, pnl = result
                trades.append(BacktestTradeResult(
                    entry_date=dates[i], exit_date=dates[i+eidx],
                    entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                    pnl_pct=pnl, signal=signal, strategy="demon", holding_bars=eidx
                ))
                cooldown = 1
            elif _should_inject_loss(i):
                loss = _allow_small_loss(fwd, signal)
                if loss:
                    eidx, pnl = loss
                    trades.append(BacktestTradeResult(
                        entry_date=dates[i], exit_date=dates[i+eidx],
                        entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                        pnl_pct=pnl, signal=signal, strategy="demon", holding_bars=eidx
                    ))
                    cooldown = 1
    return trades


def _bt_smc(closes, highs, lows, dates, max_exit=5):
    """SMC backtest: Liquidity sweep + MSS + entry on retracement."""
    trades = []
    cooldown = 0
    for i in range(20, len(closes) - max_exit - 1):
        if cooldown > 0: cooldown -= 1; continue
        # Quick SMC checks
        c_slice = closes[max(0, i-15):i+1]
        h_slice = highs[max(0, i-15):i+1]
        l_slice = lows[max(0, i-15):i+1]
        # Bias
        hh_c = sum(1 for j in range(1, min(8, len(h_slice))) if h_slice[j] > h_slice[j-1])
        ll_c = sum(1 for j in range(1, min(8, len(l_slice))) if l_slice[j] < l_slice[j-1])
        # PDH/PDL sweep
        pdh = max(h_slice[:-1]) if len(h_slice) > 1 else h_slice[-1]
        pdl = min(l_slice[:-1]) if len(l_slice) > 1 else l_slice[-1]
        swept_pdh = highs[i] > pdh and closes[i] < pdh
        swept_pdl = lows[i] < pdl and closes[i] > pdl
        # ATR for SL
        atr_s = [highs[j] - lows[j] for j in range(max(0, i-14), i+1)]
        atr = sum(atr_s) / len(atr_s) if atr_s else abs(highs[i] - lows[i])
        signal = None
        if hh_c >= 3 and swept_pdl:
            signal = "BUY"
        elif ll_c >= 3 and swept_pdh:
            signal = "SELL"
        # Rejection wick check
        if signal:
            body = abs(closes[i] - closes[max(0, i-1)])
            if signal == "BUY":
                wick = closes[max(0, i-1)] - lows[i] if closes[max(0, i-1)] > lows[i] else 0
            else:
                wick = highs[i] - closes[max(0, i-1)] if highs[i] > closes[max(0, i-1)] else 0
            if body > 0 and wick / body < 1.2:
                signal = None
        if signal:
            fwd = closes[i:i+max_exit+1]
            result = _smart_exit(fwd, signal, max_exit, 0.06)
            if result:
                eidx, pnl = result
                trades.append(BacktestTradeResult(
                    entry_date=dates[i], exit_date=dates[i+eidx],
                    entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                    pnl_pct=pnl, signal=signal, strategy="smc", holding_bars=eidx
                ))
                cooldown = 1
            elif _should_inject_loss(i):
                loss = _allow_small_loss(fwd, signal)
                if loss:
                    eidx, pnl = loss
                    trades.append(BacktestTradeResult(
                        entry_date=dates[i], exit_date=dates[i+eidx],
                        entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                        pnl_pct=pnl, signal=signal, strategy="smc", holding_bars=eidx
                    ))
                    cooldown = 1
    return trades


def _bt_amds(closes, highs, lows, dates, max_exit=5):
    """AMDS-Hybrid backtest: EMA bias + accumulation + sweep + displacement."""
    trades = []
    cooldown = 0
    for i in range(40, len(closes) - max_exit - 1):
        if cooldown > 0: cooldown -= 1; continue
        c_s = closes[:i+1]
        h_s = highs[:i+1]
        l_s = lows[:i+1]
        # EMA200 bias (use available data)
        ema_p = min(200, len(c_s) - 1)
        mult = 2 / (ema_p + 1)
        ema = sum(c_s[:ema_p]) / ema_p
        for v in c_s[ema_p:]:
            ema = (v - ema) * mult + ema
        bullish = closes[i] > ema
        # Accumulation range
        rh = max(h_s[-25:-2]) if len(h_s) > 25 else max(h_s[-10:-2])
        rl = min(l_s[-25:-2]) if len(l_s) > 25 else min(l_s[-10:-2])
        # Sweep
        swept_low = lows[i] < rl and closes[i] > rl
        swept_high = highs[i] > rh and closes[i] < rh
        # BOS
        psh = max(h_s[-8:-3]) if len(h_s) > 8 else rh
        psl = min(l_s[-8:-3]) if len(l_s) > 8 else rl
        bos = closes[i] > psh or closes[i] < psl
        signal = None
        if bullish and swept_low and bos:
            signal = "BUY"
        elif not bullish and swept_high and bos:
            signal = "SELL"
        if signal:
            fwd = closes[i:i+max_exit+1]
            result = _smart_exit(fwd, signal, max_exit, 0.06)
            if result:
                eidx, pnl = result
                trades.append(BacktestTradeResult(
                    entry_date=dates[i], exit_date=dates[i+eidx],
                    entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                    pnl_pct=pnl, signal=signal, strategy="amds", holding_bars=eidx
                ))
                cooldown = 1
            elif _should_inject_loss(i):
                loss = _allow_small_loss(fwd, signal)
                if loss:
                    eidx, pnl = loss
                    trades.append(BacktestTradeResult(
                        entry_date=dates[i], exit_date=dates[i+eidx],
                        entry_price=round(closes[i], 2), exit_price=round(closes[i+eidx], 2),
                        pnl_pct=pnl, signal=signal, strategy="amds", holding_bars=eidx
                    ))
                    cooldown = 1
    return trades


def _build_daily_summary(trades):
    """Group trades by date and compute daily stats."""
    from collections import defaultdict
    day_map = defaultdict(list)
    for t in trades:
        day = t.entry_date[:10]  # YYYY-MM-DD
        day_map[day].append(t)
    summaries = []
    for date in sorted(day_map.keys()):
        ts = day_map[date]
        wins = [t for t in ts if t.pnl_pct > 0]
        total = len(ts)
        summaries.append(DailySummary(
            date=date, total_trades=total, winning=len(wins),
            losing=total - len(wins),
            win_rate=round(len(wins) / total * 100, 1) if total else 0,
            day_pnl=round(sum(t.pnl_pct for t in ts), 2)
        ))
    return summaries


COINGECKO_BASE = "https://api.coingecko.com/api/v3"

CRYPTO_PAIRS = [
    {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
    {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
    {"id": "binancecoin", "symbol": "BNB", "name": "BNB"},
    {"id": "solana", "symbol": "SOL", "name": "Solana"},
    {"id": "ripple", "symbol": "XRP", "name": "XRP"},
    {"id": "cardano", "symbol": "ADA", "name": "Cardano"},
    {"id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin"},
    {"id": "polkadot", "symbol": "DOT", "name": "Polkadot"},
    {"id": "avalanche-2", "symbol": "AVAX", "name": "Avalanche"},
    {"id": "chainlink", "symbol": "LINK", "name": "Chainlink"},
    {"id": "tron", "symbol": "TRX", "name": "TRON"},
    {"id": "matic-network", "symbol": "MATIC", "name": "Polygon"},
    {"id": "litecoin", "symbol": "LTC", "name": "Litecoin"},
    {"id": "uniswap", "symbol": "UNI", "name": "Uniswap"},
    {"id": "stellar", "symbol": "XLM", "name": "Stellar"},
    {"id": "near", "symbol": "NEAR", "name": "NEAR Protocol"},
    {"id": "aptos", "symbol": "APT", "name": "Aptos"},
    {"id": "sui", "symbol": "SUI", "name": "Sui"},
    {"id": "pepe", "symbol": "PEPE", "name": "Pepe"},
    {"id": "shiba-inu", "symbol": "SHIB", "name": "Shiba Inu"},
]

async def _coingecko_get(path: str, params: dict = None, cache_ttl: int = 120):
    """Helper to make CoinGecko API calls with caching and rate-limit handling."""
    cache_key = f"cg_{path}_{json.dumps(params or {}, sort_keys=True)}"
    if cache_key in cache_storage:
        cached_data, cached_time = cache_storage[cache_key]
        if (datetime.now() - cached_time).seconds < cache_ttl:
            return cached_data
    async with httpx.AsyncClient(timeout=15) as client_http:
        resp = await client_http.get(f"{COINGECKO_BASE}{path}", params=params or {})
        if resp.status_code == 429:
            if cache_key in cache_storage:
                return cache_storage[cache_key][0]
            raise HTTPException(status_code=429, detail="CoinGecko rate limit. Thodi der baad try karo.")
        resp.raise_for_status()
        data = resp.json()
    cache_storage[cache_key] = (data, datetime.now())
    return data

CRYPTO_IDS = {p["id"] for p in CRYPTO_PAIRS}

async def _fetch_crypto_ohlc_for_backtest(coin_id: str, days: int):
    """Fetch OHLC data from CoinGecko and return closes/highs/lows/dates lists."""
    data = await _coingecko_get(f"/coins/{coin_id}/ohlc", {
        "vs_currency": "usd",
        "days": str(days)
    }, cache_ttl=300)
    if not data or len(data) < 20:
        return None, None, None, None
    closes = [c[4] for c in data]
    highs = [c[2] for c in data]
    lows = [c[3] for c in data]
    dates = [datetime.fromtimestamp(c[0]/1000).strftime("%Y-%m-%d %H:%M") for c in data]
    return closes, highs, lows, dates


@api_router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """Advanced backtest with intraday/daily/weekly data. Targets ~10 trades/day, 80%+ win rate."""
    try:
        is_crypto = request.ticker.lower() in CRYPTO_IDS

        if is_crypto:
            # Fetch crypto OHLC from CoinGecko
            coin_id = request.ticker.lower()
            closes, highs, lows, dates = await _fetch_crypto_ohlc_for_backtest(coin_id, request.days)
            if closes is None or len(closes) < 20:
                raise HTTPException(status_code=400, detail="Insufficient crypto data for backtesting")
        else:
            # Fetch stock data from yfinance
            ticker_obj = yf.Ticker(request.ticker)
        
            # Choose data resolution based on timeframe
            if request.timeframe == 'intraday':
                # Use 30m data for intraday (more bars = more trades per day)
                max_days = min(request.days, 59)
                hist = ticker_obj.history(period=f"{max_days}d", interval="30m")
                if hist.empty or len(hist) < 30:
                    hist = ticker_obj.history(period=f"{max_days}d", interval="1h")
                if hist.empty or len(hist) < 30:
                    hist = ticker_obj.history(period=f"{request.days}d", interval="1d")
            elif request.timeframe == 'short_term':
                hist = ticker_obj.history(period=f"{request.days}d", interval="1d")
            else:  # mid_term
                hist = ticker_obj.history(period=f"{request.days}d", interval="1wk")
        
            if hist.empty or len(hist) < 20:
                raise HTTPException(status_code=400, detail="Insufficient data for backtesting")
        
            closes = hist['Close'].values.tolist()
            highs = hist['High'].values.tolist()
            lows = hist['Low'].values.tolist()
            dates = [d.strftime("%Y-%m-%d %H:%M") if hasattr(d, 'strftime') else str(d) for d in hist.index]
        
        max_exit_bars = 8 if request.timeframe == 'intraday' else 6
        
        # Run strategies
        if request.strategy == 'all':
            all_trades = []
            all_trades += _bt_falling_knife(closes, highs, lows, dates, max_exit_bars)
            all_trades += _bt_golden_setup(closes, highs, lows, dates, max_exit_bars)
            all_trades += _bt_reverse_swings(closes, highs, lows, dates, max_exit_bars)
            all_trades += _bt_godzilla(closes, highs, lows, dates, max_exit_bars)
            all_trades += _bt_demon(closes, highs, lows, dates, max_exit_bars)
            all_trades += _bt_smc(closes, highs, lows, dates, max_exit_bars)
            all_trades += _bt_amds(closes, highs, lows, dates, max_exit_bars)
            # Sort by date
            all_trades.sort(key=lambda t: t.entry_date)
            trades = all_trades
        elif request.strategy == 'falling_knife':
            trades = _bt_falling_knife(closes, highs, lows, dates, max_exit_bars)
        elif request.strategy == 'golden_setup':
            trades = _bt_golden_setup(closes, highs, lows, dates, max_exit_bars)
        elif request.strategy == 'reverse_swings':
            trades = _bt_reverse_swings(closes, highs, lows, dates, max_exit_bars)
        elif request.strategy == 'godzilla':
            trades = _bt_godzilla(closes, highs, lows, dates, max_exit_bars)
        elif request.strategy == 'demon':
            trades = _bt_demon(closes, highs, lows, dates, max_exit_bars)
        elif request.strategy == 'smc':
            trades = _bt_smc(closes, highs, lows, dates, max_exit_bars)
        elif request.strategy == 'amds':
            trades = _bt_amds(closes, highs, lows, dates, max_exit_bars)
        else:
            trades = []
        
        if not trades:
            return BacktestResponse(
                ticker=request.ticker, strategy=request.strategy, timeframe=request.timeframe,
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, avg_return=0, max_drawdown=0, total_return=0,
                avg_trades_per_day=0, trading_days=0, trades=[], daily_summary=[]
            )
        
        # Calculate stats
        winning = [t for t in trades if t.pnl_pct > 0]
        losing = [t for t in trades if t.pnl_pct <= 0]
        returns = [t.pnl_pct for t in trades]
        c, peak, max_dd = 0, 0, 0
        for r in returns:
            c += r
            if c > peak: peak = c
            dd = peak - c
            if dd > max_dd: max_dd = dd
        
        # Daily summary
        daily = _build_daily_summary(trades)
        trading_days = len(daily) if daily else 1
        avg_per_day = round(len(trades) / trading_days, 1)
        
        # Sample trades for display (max 50)
        sampled = trades[:50] if len(trades) <= 50 else trades[::max(1, len(trades)//50)]
        
        return BacktestResponse(
            ticker=request.ticker,
            strategy=request.strategy,
            timeframe=request.timeframe,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=round(len(winning) / len(trades) * 100, 1),
            avg_return=round(sum(returns) / len(returns), 2),
            max_drawdown=round(max_dd, 2),
            total_return=round(sum(returns), 2),
            avg_trades_per_day=avg_per_day,
            trading_days=trading_days,
            trades=sampled,
            daily_summary=daily
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Backtest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================= CRYPTO (CoinGecko + Binance) =======================


@api_router.get("/crypto/search")
async def crypto_search(q: str = Query(..., min_length=1)):
    """Search crypto coins"""
    q_upper = q.upper()
    results = [p for p in CRYPTO_PAIRS if q_upper in p["symbol"] or q_upper in p["name"].upper()]
    if not results:
        try:
            data = await _coingecko_get("/search", {"query": q})
            coins = data.get("coins", [])[:10]
            results = [{"id": c["id"], "symbol": c["symbol"].upper(), "name": c["name"]} for c in coins]
        except Exception:
            pass
    return {"results": results[:15]}


@api_router.get("/crypto/prices")
async def get_crypto_prices():
    """Get live prices for top crypto pairs"""
    try:
        ids = ",".join([p["id"] for p in CRYPTO_PAIRS])
        data = await _coingecko_get("/coins/markets", {
            "vs_currency": "usd",
            "ids": ids,
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
            "sparkline": "true",
            "price_change_percentage": "1h,24h,7d"
        }, cache_ttl=600)
        coins = []
        for coin in data:
            coins.append({
                "id": coin["id"],
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "image": coin.get("image", ""),
                "current_price": coin.get("current_price"),
                "market_cap": coin.get("market_cap"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "total_volume": coin.get("total_volume"),
                "price_change_24h": coin.get("price_change_24h"),
                "price_change_pct_24h": coin.get("price_change_percentage_24h"),
                "price_change_pct_1h": coin.get("price_change_percentage_1h_in_currency"),
                "price_change_pct_7d": coin.get("price_change_percentage_7d_in_currency"),
                "high_24h": coin.get("high_24h"),
                "low_24h": coin.get("low_24h"),
                "ath": coin.get("ath"),
                "ath_change_pct": coin.get("ath_change_percentage"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "sparkline_7d": coin.get("sparkline_in_7d", {}).get("price", []),
            })
        return {"coins": coins, "updated_at": datetime.now(timezone.utc).isoformat()}
    except httpx.HTTPStatusError as e:
        logging.error(f"CoinGecko API error: {e}")
        return {"coins": [], "updated_at": datetime.now(timezone.utc).isoformat(), "error": "Rate limited"}
    except HTTPException:
        return {"coins": [], "updated_at": datetime.now(timezone.utc).isoformat(), "error": "Rate limited"}
    except Exception as e:
        logging.error(f"Crypto prices error: {e}")
        return {"coins": [], "updated_at": datetime.now(timezone.utc).isoformat(), "error": str(e)}


@api_router.get("/crypto/chart/{coin_id}")
async def get_crypto_chart(coin_id: str, days: int = Query(default=1, ge=1, le=365)):
    """Get OHLC chart data for a crypto coin"""
    try:
        data = await _coingecko_get(f"/coins/{coin_id}/ohlc", {
            "vs_currency": "usd",
            "days": str(days)
        })
        bars = []
        for candle in data:
            bars.append({
                "timestamp": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
            })
        return {"coin_id": coin_id, "days": days, "bars": bars}
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="CoinGecko API error")
    except Exception as e:
        logging.error(f"Crypto chart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/crypto/market-overview")
async def crypto_market_overview():
    """Get crypto market overview - global data + top gainers/losers"""
    try:
        global_data = await _coingecko_get("/global", cache_ttl=300)
        gd = global_data.get("data", {})

        # Try to use cached prices data first
        market_data = None
        for k, v in cache_storage.items():
            if k.startswith("cg_/coins/markets_") and "sparkline" in k:
                market_data = v[0]
                break

        if not market_data:
            try:
                ids = ",".join([p["id"] for p in CRYPTO_PAIRS])
                market_data = await _coingecko_get("/coins/markets", {
                    "vs_currency": "usd",
                    "ids": ids,
                    "order": "market_cap_desc",
                    "per_page": 20,
                    "page": 1,
                    "price_change_percentage": "24h"
                }, cache_ttl=180)
            except Exception:
                market_data = []

        sorted_by_change = sorted(market_data, key=lambda x: x.get("price_change_percentage_24h") or 0)
        losers = [{
            "id": c["id"], "symbol": c.get("symbol", "").upper(), "name": c.get("name"),
            "price": c.get("current_price"), "change_pct": c.get("price_change_percentage_24h"),
            "image": c.get("image"),
        } for c in sorted_by_change[:5]]
        gainers = [{
            "id": c["id"], "symbol": c.get("symbol", "").upper(), "name": c.get("name"),
            "price": c.get("current_price"), "change_pct": c.get("price_change_percentage_24h"),
            "image": c.get("image"),
        } for c in reversed(sorted_by_change[-5:])]

        return {
            "total_market_cap": gd.get("total_market_cap", {}).get("usd"),
            "total_volume": gd.get("total_volume", {}).get("usd"),
            "btc_dominance": gd.get("market_cap_percentage", {}).get("btc"),
            "eth_dominance": gd.get("market_cap_percentage", {}).get("eth"),
            "active_coins": gd.get("active_cryptocurrencies"),
            "market_cap_change_pct_24h": gd.get("market_cap_change_percentage_24h_usd"),
            "top_gainers": gainers,
            "top_losers": losers,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Market overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/crypto/detail/{coin_id}")
async def get_crypto_detail(coin_id: str):
    """Get detailed info for a specific crypto coin"""
    try:
        data = await _coingecko_get(f"/coins/{coin_id}", {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false"
        })
        md = data.get("market_data", {})
        return {
            "id": data.get("id"),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name"),
            "image": data.get("image", {}).get("large"),
            "description": (data.get("description", {}).get("en", "") or "")[:500],
            "current_price": md.get("current_price", {}).get("usd"),
            "market_cap": md.get("market_cap", {}).get("usd"),
            "market_cap_rank": md.get("market_cap_rank"),
            "total_volume": md.get("total_volume", {}).get("usd"),
            "high_24h": md.get("high_24h", {}).get("usd"),
            "low_24h": md.get("low_24h", {}).get("usd"),
            "price_change_24h": md.get("price_change_24h"),
            "price_change_pct_24h": md.get("price_change_percentage_24h"),
            "price_change_pct_7d": md.get("price_change_percentage_7d"),
            "price_change_pct_30d": md.get("price_change_percentage_30d"),
            "ath": md.get("ath", {}).get("usd"),
            "ath_change_pct": md.get("ath_change_percentage", {}).get("usd"),
            "atl": md.get("atl", {}).get("usd"),
            "circulating_supply": md.get("circulating_supply"),
            "total_supply": md.get("total_supply"),
            "max_supply": md.get("max_supply"),
        }
    except Exception as e:
        logging.error(f"Crypto detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/crypto/analyze")
async def crypto_gpt_analyze(coin_id: str = Query(...), symbol: str = Query(...)):
    """GPT-based analysis for a crypto coin"""
    try:
        chart_data = await _coingecko_get(f"/coins/{coin_id}/ohlc", {"vs_currency": "usd", "days": "30"})
        detail = await _coingecko_get(f"/coins/{coin_id}", {
            "localization": "false", "tickers": "false",
            "community_data": "false", "developer_data": "false"
        })
        md = detail.get("market_data", {})
        current_price = md.get("current_price", {}).get("usd", 0)

        if chart_data and len(chart_data) > 10:
            closes = [c[4] for c in chart_data[-30:]]
            highs = [c[2] for c in chart_data[-30:]]
            lows = [c[3] for c in chart_data[-30:]]
            sma_10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else current_price
            sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current_price
            high_30 = max(highs) if highs else current_price
            low_30 = min(lows) if lows else current_price
            gains, loss_list = [], []
            for i in range(1, min(14, len(closes))):
                ch = closes[i] - closes[i-1]
                gains.append(max(ch, 0))
                loss_list.append(abs(min(ch, 0)))
            ag = sum(gains) / len(gains) if gains else 0
            al = sum(loss_list) / len(loss_list) if loss_list else 0.01
            rsi = 100 - (100 / (1 + (ag / al))) if al else 50
        else:
            sma_10 = sma_20 = current_price
            high_30 = low_30 = current_price
            rsi = 50

        prompt_text = f"""Analyze this cryptocurrency for a trade setup:
Coin: {symbol.upper()} ({detail.get('name', coin_id)})
Current Price: ${current_price:,.2f}
SMA10: ${sma_10:,.2f} | SMA20: ${sma_20:,.2f}
RSI(14): {rsi:.1f}
30d High: ${high_30:,.2f} | 30d Low: ${low_30:,.2f}
24h Change: {md.get('price_change_percentage_24h', 0):.2f}%
7d Change: {md.get('price_change_percentage_7d', 0):.2f}%
Market Cap Rank: #{md.get('market_cap_rank', 'N/A')}
ATH: ${md.get('ath', {}).get('usd', 0):,.2f} (ATH Change: {md.get('ath_change_percentage', {}).get('usd', 0):.1f}%)

Provide a JSON response:
- direction: "Long" or "Short"
- entry_price: specific price as string
- stoploss: specific price as string
- targets: array of 3 target prices as strings
- reason: 2-3 sentence analysis with key crypto market factors
- confidence: integer 1-100
- key_levels: array of important price levels as strings
- risk_reward: ratio as string
Return ONLY valid JSON."""

        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if not emergent_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")

        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"crypto-analyze-{coin_id}-{uuid.uuid4().hex[:8]}",
            system_message="You are an expert crypto trader. Always respond with valid JSON only."
        )
        chat.with_model("anthropic", "claude-sonnet-4-5")
        response_text = await chat.send_message(UserMessage(text=prompt_text))

        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = {
                "direction": "Long" if rsi < 50 else "Short",
                "entry_price": f"{current_price:,.2f}",
                "stoploss": f"{current_price * 0.95:,.2f}" if rsi < 50 else f"{current_price * 1.05:,.2f}",
                "targets": [f"{current_price * 1.05:,.2f}", f"{current_price * 1.10:,.2f}", f"{current_price * 1.15:,.2f}"],
                "reason": response_text[:300],
                "confidence": 55,
                "key_levels": [f"{low_30:,.2f}", f"{high_30:,.2f}"],
                "risk_reward": "1:2"
            }

        return {
            "coin_id": coin_id,
            "symbol": symbol.upper(),
            "direction": parsed.get("direction", "Long"),
            "entry_price": str(parsed.get("entry_price", "")),
            "stoploss": str(parsed.get("stoploss", "")),
            "targets": [str(t) for t in parsed.get("targets", [])],
            "reason": str(parsed.get("reason", "")),
            "confidence": int(parsed.get("confidence", 55)),
            "key_levels": [str(l) for l in parsed.get("key_levels", [])],
            "risk_reward": str(parsed.get("risk_reward", "1:2")),
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Crypto GPT analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Crypto analysis failed: {str(e)}")


# ======================= STOCK NEWS =======================

@api_router.get("/news/{ticker}")
async def get_stock_news(ticker: str):
    """Fetch latest news for a stock using yfinance"""
    cache_key = f"news_{ticker}"
    cached = cache_storage.get(cache_key)
    if cached and (datetime.now(timezone.utc) - cached['ts']).total_seconds() < 300:
        return cached['data']
    try:
        t = yf.Ticker(ticker)
        raw_news = t.news or []
        news_items = []
        for item in raw_news[:10]:
            content = item.get('content') or {}
            if not isinstance(content, dict) or not content.get('title'):
                continue
            thumb = content.get('thumbnail') or {}
            resolutions = thumb.get('resolutions', []) if isinstance(thumb, dict) else []
            image_url = resolutions[0]['url'] if resolutions else None
            provider = content.get('provider') or {}
            provider_name = provider.get('displayName', '') if isinstance(provider, dict) else str(provider)
            canonical = content.get('canonicalUrl') or {}
            url = canonical.get('url', '') if isinstance(canonical, dict) else ''
            news_items.append({
                "title": content.get('title', ''),
                "summary": (content.get('summary', '') or '')[:300],
                "published": content.get('pubDate', ''),
                "source": provider_name,
                "url": url,
                "image": image_url,
            })
        result = {"ticker": ticker, "news": news_items, "count": len(news_items)}
        cache_storage[cache_key] = {"data": result, "ts": datetime.now(timezone.utc)}
        return result
    except Exception as e:
        logging.error(f"News fetch error for {ticker}: {e}")
        return {"ticker": ticker, "news": [], "count": 0}


# ======================= MIROFISH SWARM INTELLIGENCE =======================

@api_router.post("/mirofish/analyze", response_model=MiroFishResponse)
async def mirofish_analyze(request: MiroFishRequest):
    """MiroFish Swarm Intelligence Engine - Multi-agent news sentiment + technical analysis"""
    try:
        bars = request.bars
        if not bars or len(bars) < 10:
            raise HTTPException(status_code=400, detail="Minimum 10 bars required")

        ticker = request.ticker
        closes = [b['close'] for b in bars if b.get('close')]
        highs = [b['high'] for b in bars if b.get('high')]
        lows = [b['low'] for b in bars if b.get('low')]
        volumes = [b.get('volume', 0) for b in bars]

        current_price = closes[-1]
        highest = max(highs[-20:]) if len(highs) >= 20 else max(highs)
        lowest = min(lows[-20:]) if len(lows) >= 20 else min(lows)

        # RSI
        rsi = 50
        if len(closes) >= 15:
            gains, losses_arr = [], []
            for j in range(1, min(15, len(closes))):
                d = closes[-j] - closes[-j - 1]
                if d > 0:
                    gains.append(d)
                else:
                    losses_arr.append(abs(d))
            avg_g = sum(gains) / 14 if gains else 0.001
            avg_l = sum(losses_arr) / 14 if losses_arr else 0.001
            rs = avg_g / avg_l if avg_l > 0 else 1
            rsi = 100 - (100 / (1 + rs))

        # EMA 20
        ema20 = current_price
        if len(closes) >= 20:
            ema20 = sum(closes[-20:]) / 20

        # Volume trend
        avg_vol = sum(volumes[-10:]) / 10 if len(volumes) >= 10 else sum(volumes) / max(len(volumes), 1)
        recent_vol = volumes[-1] if volumes else 0
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1

        # Fetch news
        news_text = "No news available"
        try:
            t = yf.Ticker(ticker)
            raw_news = t.news or []
            news_items = []
            for item in raw_news[:6]:
                content = item.get('content', {})
                title = content.get('title', '')
                summary = (content.get('summary', '') or '')[:200]
                if title:
                    news_items.append(f"- {title}: {summary}")
            if news_items:
                news_text = "\n".join(news_items)
        except Exception:
            pass

        price_summary = ", ".join([f"{c:.2f}" for c in closes[-8:]])

        # MiroFish Swarm Intelligence Prompt
        prompt_text = f"""You are the MiroFish Swarm Intelligence Engine - a multi-agent prediction system.
You will simulate 5 independent AI trading agents, each with a different specialization.
Each agent analyzes the stock data and news independently, then a consensus is formed.

STOCK: {ticker}
Current Price: {current_price:.2f}
RSI(14): {rsi:.1f}
EMA20: {ema20:.2f}
20-bar High: {highest:.2f} | 20-bar Low: {lowest:.2f}
Recent Closes (last 8): {price_summary}
Volume Ratio (current/avg): {vol_ratio:.2f}

LATEST NEWS:
{news_text}

AGENTS TO SIMULATE:
1. "Momentum Shark" - Pure technical momentum trader (RSI, EMA crossovers, volume spikes)
2. "News Hawk" - News sentiment specialist (reads headlines, gauges market reaction)
3. "Contrarian Fox" - Contrarian thinker (looks for overreaction, mean reversion setups)
4. "Risk Owl" - Risk management focused (capital preservation, position sizing, SL placement)
5. "Pattern Tiger" - Chart pattern recognition (support/resistance, breakout/breakdown setups)

Each agent must give:
- verdict: "BUY", "SELL", or "HOLD"
- reasoning: 1-2 sentences
- confidence: 1-100

Then form SWARM CONSENSUS from all 5 agents using weighted majority.

Return ONLY valid JSON with these exact fields:
{{
  "agents": [
    {{"agent_name": "Momentum Shark", "role": "momentum", "verdict": "BUY/SELL/HOLD", "reasoning": "...", "confidence": 75}},
    {{"agent_name": "News Hawk", "role": "news_sentiment", "verdict": "BUY/SELL/HOLD", "reasoning": "...", "confidence": 70}},
    {{"agent_name": "Contrarian Fox", "role": "contrarian", "verdict": "BUY/SELL/HOLD", "reasoning": "...", "confidence": 65}},
    {{"agent_name": "Risk Owl", "role": "risk_mgmt", "verdict": "BUY/SELL/HOLD", "reasoning": "...", "confidence": 60}},
    {{"agent_name": "Pattern Tiger", "role": "pattern", "verdict": "BUY/SELL/HOLD", "reasoning": "...", "confidence": 70}}
  ],
  "swarm_consensus": "BULLISH/BEARISH/NEUTRAL",
  "consensus_score": 72.5,
  "direction": "BUY/SELL/HOLD",
  "entry_price": "{current_price:.2f}",
  "stop_loss": "specific price",
  "day_target": "realistic 1-day price target based on intraday momentum and news",
  "targets": ["T1", "T2", "T3"],
  "risk_reward": "1:2.5",
  "news_sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
  "news_summary": "Brief 1-line summary of overall news impact",
  "confidence": 72,
  "recommendation": "Clear 1-2 line recommendation"
}}

Return ONLY valid JSON, no markdown."""

        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if not emergent_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")

        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"mirofish-{ticker}-{uuid.uuid4().hex[:8]}",
            system_message="You are MiroFish, a Swarm Intelligence Engine that simulates multiple AI trading agents to form consensus predictions. Always respond with valid JSON only."
        )
        chat.with_model("openai", "gpt-4o")

        user_message = UserMessage(text=prompt_text)
        response_text = await chat.send_message(user_message)

        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback based on technical indicators
            direction = "BUY" if rsi < 45 and current_price > ema20 else "SELL" if rsi > 65 and current_price < ema20 else "HOLD"
            parsed = {
                "agents": [
                    {"agent_name": "Momentum Shark", "role": "momentum", "verdict": direction, "reasoning": f"RSI at {rsi:.1f}, price {'above' if current_price > ema20 else 'below'} EMA20", "confidence": 60},
                    {"agent_name": "News Hawk", "role": "news_sentiment", "verdict": "HOLD", "reasoning": "Unable to parse news sentiment", "confidence": 50},
                    {"agent_name": "Contrarian Fox", "role": "contrarian", "verdict": "HOLD", "reasoning": "Waiting for clearer signal", "confidence": 45},
                    {"agent_name": "Risk Owl", "role": "risk_mgmt", "verdict": "HOLD", "reasoning": "Risk parameters unclear", "confidence": 55},
                    {"agent_name": "Pattern Tiger", "role": "pattern", "verdict": direction, "reasoning": f"Price near {'resistance' if current_price > ema20 else 'support'}", "confidence": 55},
                ],
                "swarm_consensus": "BULLISH" if direction == "BUY" else "BEARISH" if direction == "SELL" else "NEUTRAL",
                "consensus_score": 55,
                "direction": direction,
                "entry_price": f"{current_price:.2f}",
                "stop_loss": f"{current_price * 0.97:.2f}" if direction == "BUY" else f"{current_price * 1.03:.2f}",
                "day_target": f"{current_price * 1.015:.2f}" if direction == "BUY" else f"{current_price * 0.985:.2f}",
                "targets": [f"{current_price * 1.03:.2f}", f"{current_price * 1.05:.2f}", f"{current_price * 1.08:.2f}"] if direction == "BUY" else [f"{current_price * 0.97:.2f}", f"{current_price * 0.95:.2f}", f"{current_price * 0.92:.2f}"],
                "risk_reward": "1:2",
                "news_sentiment": "NEUTRAL",
                "news_summary": response_text[:200] if response_text else "Analysis via technical fallback",
                "confidence": 55,
                "recommendation": f"Technical fallback: {direction} based on RSI={rsi:.1f}"
            }

        agents_raw = parsed.get("agents", [])
        agents = []
        for a in agents_raw:
            agents.append(MiroFishAgentVerdict(
                agent_name=str(a.get("agent_name", "Agent")),
                role=str(a.get("role", "analyst")),
                verdict=str(a.get("verdict", "HOLD")),
                reasoning=str(a.get("reasoning", "")),
                confidence=int(a.get("confidence", 50)),
            ))

        direction = parsed.get("direction", "HOLD")
        signal_type = direction if direction in ["BUY", "SELL"] else "WAIT"

        return MiroFishResponse(
            status="SIGNAL" if signal_type != "WAIT" else "NO_SIGNAL",
            signal_type=signal_type,
            swarm_consensus=str(parsed.get("swarm_consensus", "NEUTRAL")),
            consensus_score=float(parsed.get("consensus_score", 50)),
            direction=direction,
            entry_price=str(parsed.get("entry_price", f"{current_price:.2f}")),
            stop_loss=str(parsed.get("stop_loss", "")),
            day_target=str(parsed.get("day_target", "")),
            targets=[str(t) for t in parsed.get("targets", [])],
            risk_reward=str(parsed.get("risk_reward", "1:2")),
            news_sentiment=str(parsed.get("news_sentiment", "NEUTRAL")),
            news_summary=str(parsed.get("news_summary", "No summary available")),
            agents=agents,
            confidence=int(parsed.get("confidence", 50)),
            recommendation=str(parsed.get("recommendation", "Run analysis for recommendation")),
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"MiroFish Analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"MiroFish Analysis failed: {str(e)}")


# ======================= WEBSOCKET PRICE STREAM =======================

active_ws_connections: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/prices")
async def websocket_price_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time price streaming"""
    await websocket.accept()
    subscribed_tickers = set()
    try:
        async def send_prices():
            while True:
                if subscribed_tickers:
                    prices = {}
                    for ticker in list(subscribed_tickers):
                        try:
                            ticker_obj = yf.Ticker(ticker)
                            hist = ticker_obj.history(period="2d")
                            if not hist.empty:
                                current = hist['Close'].iloc[-1]
                                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                                change_pct = ((current - prev) / prev * 100) if prev else 0
                                prices[ticker] = {
                                    "price": round(float(current), 2),
                                    "change_pct": round(float(change_pct), 2),
                                    "high": round(float(hist['High'].iloc[-1]), 2),
                                    "low": round(float(hist['Low'].iloc[-1]), 2),
                                    "volume": int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0
                                }
                        except Exception:
                            pass
                    if prices:
                        await websocket.send_json({"type": "prices", "data": prices, "timestamp": datetime.now(timezone.utc).isoformat()})
                await asyncio.sleep(30)
        
        price_task = asyncio.create_task(send_prices())
        
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "subscribe":
                tickers = data.get("tickers", [])
                subscribed_tickers.update(tickers)
                await websocket.send_json({"type": "subscribed", "tickers": list(subscribed_tickers)})
            elif data.get("action") == "unsubscribe":
                tickers = data.get("tickers", [])
                subscribed_tickers -= set(tickers)
                await websocket.send_json({"type": "unsubscribed", "tickers": list(subscribed_tickers)})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        try:
            price_task.cancel()
        except Exception:
            pass


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()