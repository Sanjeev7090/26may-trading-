"""
Groww Trade API wrapper.

- Auto-refreshes the short-lived access token from API_KEY + API_SECRET.
- Exposes candle/ltp/ohlc + portfolio + order placement helpers.
"""
import os
import time
import threading
from typing import Optional, List, Dict, Any
import datetime

from growwapi import GrowwAPI

_API_KEY = os.environ.get("GROWW_API_KEY", "").strip()
_API_SECRET = os.environ.get("GROWW_API_SECRET", "").strip()

# Module-level cache
_client: Optional[GrowwAPI] = None
_token_exp: float = 0.0          # epoch seconds when current access token expires
_lock = threading.Lock()


def _refresh_client() -> GrowwAPI:
    """Get a GrowwAPI client. Refreshes token 5 min before expiry."""
    global _client, _token_exp
    now = time.time()
    with _lock:
        if _client is not None and now < (_token_exp - 300):
            return _client
        if not _API_KEY or not _API_SECRET:
            raise RuntimeError("GROWW_API_KEY / GROWW_API_SECRET not configured in backend/.env")
        access = GrowwAPI.get_access_token(api_key=_API_KEY, secret=_API_SECRET)
        _client = GrowwAPI(access)
        # Access tokens last ~13.8h. Refresh 5 min early.
        _token_exp = now + 13 * 3600
        return _client


def client() -> GrowwAPI:
    return _refresh_client()


# ─── Live data ──────────────────────────────────────────────────────
def get_ltp(symbols: List[str], segment: str = "CASH") -> Dict[str, float]:
    """symbols: ['NSE_RELIANCE', 'NSE_TCS']"""
    g = client()
    seg = g.SEGMENT_FNO if segment == "FNO" else g.SEGMENT_CASH
    return g.get_ltp(segment=seg, exchange_trading_symbols=tuple(symbols))


def get_ohlc(symbols: List[str], segment: str = "CASH") -> Dict[str, Dict[str, float]]:
    g = client()
    seg = g.SEGMENT_FNO if segment == "FNO" else g.SEGMENT_CASH
    return g.get_ohlc(segment=seg, exchange_trading_symbols=tuple(symbols))


# ─── Historical candles ────────────────────────────────────────────
_INTERVAL_MAP = {
    "1m": 1, "5m": 5, "10m": 10, "15m": 15, "30m": 30,
    "1h": 60, "4h": 240, "1d": 1440, "1w": 10080,
}


def get_candles(
    symbol: str,
    interval: str = "1d",
    days_back: int = 120,
    exchange: str = "NSE",
    segment: str = "CASH",
) -> List[Dict[str, Any]]:
    """
    Returns a list of {timestamp, open, high, low, close, volume} dicts.
    timestamp is milliseconds (matches yfinance shape used in this app).
    """
    g = client()
    mins = _INTERVAL_MAP.get(interval.lower(), 1440)
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=max(1, days_back))
    exch = g.EXCHANGE_BSE if exchange.upper() == "BSE" else g.EXCHANGE_NSE
    seg = g.SEGMENT_FNO if segment == "FNO" else g.SEGMENT_CASH

    resp = g.get_historical_candle_data(
        trading_symbol=symbol.upper(),
        exchange=exch,
        segment=seg,
        start_time=start.strftime("%Y-%m-%d %H:%M:%S"),
        end_time=end.strftime("%Y-%m-%d %H:%M:%S"),
        interval_in_minutes=mins,
    )
    candles = resp.get("candles", []) if isinstance(resp, dict) else []
    out = []
    for c in candles:
        # c = [epoch_sec, o, h, l, close, volume]
        try:
            out.append({
                "timestamp": int(c[0]) * 1000,
                "open":   float(c[1]),
                "high":   float(c[2]),
                "low":    float(c[3]),
                "close":  float(c[4]),
                "volume": float(c[5]) if len(c) > 5 else 0.0,
            })
        except (ValueError, IndexError, TypeError):
            continue
    return out


# ─── Portfolio ──────────────────────────────────────────────────────
def get_holdings() -> List[Dict[str, Any]]:
    g = client()
    resp = g.get_holdings_for_user()
    return resp.get("holdings", []) if isinstance(resp, dict) else []


def get_positions() -> List[Dict[str, Any]]:
    g = client()
    resp = g.get_positions_for_user()
    if isinstance(resp, dict):
        return resp.get("positions", []) or resp.get("data", []) or []
    return []


def get_margin() -> Dict[str, Any]:
    g = client()
    return g.get_available_margin_details() or {}


def get_profile() -> Dict[str, Any]:
    g = client()
    return g.get_user_profile() or {}


# ─── Orders ─────────────────────────────────────────────────────────
def place_order(
    trading_symbol: str,
    quantity: int,
    transaction_type: str,   # BUY / SELL
    order_type: str = "MARKET",   # MARKET / LIMIT / SL / SL_M
    product: str = "CNC",         # CNC / MIS / NRML
    exchange: str = "NSE",
    segment: str = "CASH",
    validity: str = "DAY",
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    reference_id: Optional[str] = None,
) -> Dict[str, Any]:
    g = client()
    tx = g.TRANSACTION_TYPE_BUY if transaction_type.upper() == "BUY" else g.TRANSACTION_TYPE_SELL
    ot_map = {
        "MARKET": g.ORDER_TYPE_MARKET,
        "LIMIT":  g.ORDER_TYPE_LIMIT,
        "SL":     g.ORDER_TYPE_STOP_LOSS,
        "SL_M":   g.ORDER_TYPE_STOP_LOSS_MARKET,
    }
    pr_map = {
        "CNC":  g.PRODUCT_CNC,
        "MIS":  g.PRODUCT_MIS,
        "NRML": g.PRODUCT_NRML,
    }
    val_map = {
        "DAY": g.VALIDITY_DAY,
        "IOC": g.VALIDITY_IOC,
    }
    exch = g.EXCHANGE_BSE if exchange.upper() == "BSE" else g.EXCHANGE_NSE
    seg = g.SEGMENT_FNO if segment == "FNO" else g.SEGMENT_CASH

    kwargs = dict(
        trading_symbol=trading_symbol.upper(),
        quantity=int(quantity),
        validity=val_map.get(validity.upper(), g.VALIDITY_DAY),
        exchange=exch,
        segment=seg,
        product=pr_map.get(product.upper(), g.PRODUCT_CNC),
        order_type=ot_map.get(order_type.upper(), g.ORDER_TYPE_MARKET),
        transaction_type=tx,
    )
    if price is not None:
        kwargs["price"] = float(price)
    if trigger_price is not None:
        kwargs["trigger_price"] = float(trigger_price)
    if reference_id:
        kwargs["order_reference_id"] = reference_id

    return g.place_order(**kwargs)


def get_orders() -> List[Dict[str, Any]]:
    g = client()
    resp = g.get_order_list(segment=g.SEGMENT_CASH)
    if isinstance(resp, dict):
        return resp.get("order_list", []) or resp.get("orders", []) or []
    return resp or []


def cancel_order(order_id: str, segment: str = "CASH") -> Dict[str, Any]:
    g = client()
    seg = g.SEGMENT_FNO if segment == "FNO" else g.SEGMENT_CASH
    return g.cancel_order(groww_order_id=order_id, segment=seg)
