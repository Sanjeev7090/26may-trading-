import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import StockSearch from './StockSearch';
import ChartPanel from './ChartPanel';
import SignalDashboard from './SignalDashboard';
import SquareOf9Calculator from './SquareOf9Calculator';
import OIAnalysis from './OIAnalysis';
import AITradeAnalysis from './AITradeAnalysis';
import FallingKnifeAnalysis from './FallingKnifeAnalysis';
import ReversePriceSwings from './ReversePriceSwings';
import ExplosiveVolumeAnalysis from './ExplosiveVolumeAnalysis';
import GoldenSetupAnalysis from './GoldenSetupAnalysis';
import AIIndicatorScore from './AIIndicatorScore';
import GodzillaSetupAnalysis from './GodzillaSetupAnalysis';
import DemonAnalysis from './DemonAnalysis';
import GhostModeScanner from './GhostModeScanner';
import Watchlist from './Watchlist';
import PortfolioTracker from './PortfolioTracker';
import AlertSystem from './AlertSystem';
import GPTAnalysis from './GPTAnalysis';
import BacktestModule from './BacktestModule';
import CryptoList from './CryptoList';
import CryptoDashboard from './CryptoDashboard';
import AutoScanner from './AutoScanner';
import SMCAnalysis from './SMCAnalysis';
import AMDSAnalysis from './AMDSAnalysis';
import MiroFishAnalysis from './MiroFishAnalysis';
import PACSOAnalysis from './PACSOAnalysis';
import StockNewsPopup from './StockNewsPopup';
import HybridDashboard from './hybrid/HybridDashboard';
import GannQSCPanel from './GannQSCPanel';
import RegulatoryWatchdogPanel from './RegulatoryWatchdogPanel';
import NarrativeSwingAnalysis from './NarrativeSwingAnalysis';
import OrderFlowPanel from './OrderFlowPanel';
import GrowwPortfolio from './GrowwPortfolio';
import IndicesTickerBar from './IndicesTickerBar';
import TopOptionsSheet from './TopOptionsSheet';
import { Toaster, toast } from 'sonner';
import { Star, Wallet, Bell, ChartLineUp, List, CurrencyBtc, Lightning, Newspaper, ArrowsLeftRight } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TradingDashboard = () => {
  const [hybridMode, setHybridMode] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockData, setStockData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pivotPoint, setPivotPoint] = useState(null);
  const [gannFan, setGannFan] = useState(null);
  const [signal, setSignal] = useState(null);
  const [semiLogScale, setSemiLogScale] = useState(false);
  const [timeframe, setTimeframe] = useState({ multiplier: 1, timespan: 'day', label: '1D' });
  const [activeTab, setActiveTab] = useState('scanner');
  const [leftTab, setLeftTab] = useState('search');
  const [mobilePanel, setMobilePanel] = useState('chart');
  const [cryptoChartDays, setCryptoChartDays] = useState(7);
  const [showNews, setShowNews] = useState(false);
  const [dataSource, setDataSource] = useState('yahoo'); // 'yahoo' | 'groww'
  const [optionsSheet, setOptionsSheet] = useState(null); // { symbol, name } | null
  const wsRef = useRef(null);

  // WebSocket connection for real-time prices
  useEffect(() => {
    const wsUrl = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws/prices';
    try {
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => { wsRef.current = ws; };
      ws.onclose = () => { wsRef.current = null; };
      ws.onerror = () => {};
      return () => { if (ws.readyState === WebSocket.OPEN) ws.close(); };
    } catch { /* WebSocket not critical */ }
  }, []);

  const subscribeWS = (ticker) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'subscribe', tickers: [ticker] }));
    }
  };

  const fetchStockData = async (ticker, tf, sourceOverride) => {
    setLoading(true);
    try {
      const src = sourceOverride || dataSource;
      if (src === 'groww') {
        const intvMap = {
          '1MIN':'1m',
          '5M':'5m','10M':'10m','15M':'15m','30M':'30m',
          '1H':'1h','4H':'4h','1D':'1d','1W':'1w',
          '1M':'1d','6M':'1d','1Y':'1w',
        };
        const daysMap = {
          '1MIN':7,
          '5M':10,'10M':15,'15M':15,'30M':25,
          '1H':60,'4H':150,'1D':120,'1W':400,
          '1M':30,'6M':180,'1Y':365,
        };
        const interval = intvMap[tf.label] || '1d';
        const days = daysMap[tf.label] || 120;
        const groww_symbol = selectedStock?.groww_symbol
          || (ticker || '').replace('.NS','').replace('.BO','').replace(/^\^/,'');
        const exchange = selectedStock?.exchange
          || (ticker.endsWith('.BO') ? 'BSE' : 'NSE');
        const response = await axios.get(`${API}/groww/candles/${groww_symbol}`, {
          params: { interval, days_back: days, exchange }
        });
        setStockData({ ticker, bars: response.data.bars || [] });
        toast.success(`Loaded ${tf.label} (Groww) for ${groww_symbol}`);
        return;
      }
      const params = { timespan: tf.timespan, multiplier: tf.multiplier, limit: 120 };
      if (tf.days) {
        const fromDate = new Date();
        fromDate.setDate(fromDate.getDate() - tf.days);
        params.from_date = fromDate.toISOString().split('T')[0];
        params.to_date = new Date().toISOString().split('T')[0];
      }
      const response = await axios.get(`${API}/stock/bars/${ticker}`, { params });
      setStockData(response.data);
      toast.success(`Loaded ${tf.label} data for ${ticker}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load stock data');
    } finally {
      setLoading(false);
    }
  };

  // Fetch crypto chart data and convert to stockData format
  const fetchCryptoData = async (coinId, days) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/crypto/chart/${coinId}?days=${days}`);
      const bars = (response.data.bars || []).map(b => ({
        timestamp: b.timestamp,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
        volume: 0,
      }));
      setStockData({ ticker: coinId.toUpperCase(), bars });
    } catch (error) {
      if (error?.response?.status !== 429) {
        toast.error('Failed to load crypto chart');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStockSelect = (stock) => {
    setStockData(null);
    setPivotPoint(null);
    setGannFan(null);
    setSignal(null);
    setSelectedStock(stock);
    const defaultTf = { multiplier: 1, timespan: 'day', label: '1D' };
    setTimeframe(defaultTf);
    fetchStockData(stock.ticker, defaultTf);
    subscribeWS(stock.ticker);
    setMobilePanel('chart');
    setShowNews(true);
  };

  // Map index symbol → underlying chart ticker
  const INDEX_TICKER_MAP = {
    NIFTY: { ticker: '^NSEI', name: 'NIFTY 50' },
    BANKNIFTY: { ticker: '^NSEBANK', name: 'BANK NIFTY' },
    FINNIFTY: { ticker: '^CNXFIN', name: 'FIN NIFTY' },
    SENSEX: { ticker: '^BSESN', name: 'SENSEX' },
  };

  const handleIndexClick = (symbol, name) => {
    setOptionsSheet({ symbol, name });
  };

  // Fetch intraday OHLC bars for an option (NSE chart-databyindex)
  const fetchOptionIntraday = async (option, intervalMin = 1) => {
    setLoading(true);
    try {
      const expiry = option.expiry_display || option.expiry;
      const response = await axios.get(`${API}/option/intraday`, {
        params: {
          underlying: option.underlying,
          strike: option.strike,
          option_type: option.type,
          expiry,
          interval_min: intervalMin,
        },
      });
      setStockData({
        ticker: response.data.ticker,
        bars: response.data.bars || [],
      });
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Failed to load option chart');
    } finally {
      setLoading(false);
    }
  };

  const handleOptionSelect = (option) => {
    const expiryNorm = option.expiry_display || option.expiry || '';
    // Build a synthetic stock object for the option so the chart panel knows
    // what to render. type='OPTION' lets us guard against stock-specific flows
    // (WS subscribe, signal/pivot, gann fan).
    const stock = {
      ticker: `OPT_${option.underlying}_${option.strike}_${option.type}_${expiryNorm}`,
      name: option.instrument,
      type: 'OPTION',
      underlying: option.underlying,
      strike: option.strike,
      optionType: option.type,
      expiry: expiryNorm,
      last_price: option.last_price,
      change_pct: option.change_pct,
      selectedOption: option,
    };
    setStockData(null);
    setPivotPoint(null);
    setGannFan(null);
    setSignal(null);
    setSelectedStock(stock);
    setOptionsSheet(null);
    const optTf = { multiplier: 1, timespan: 'minute', label: '1MIN' };
    setTimeframe(optTf);
    fetchOptionIntraday(option, 1);
    setMobilePanel('chart');
    toast.success(
      `${option.instrument} chart loaded`,
      {
        description: `₹${option.last_price.toFixed(2)} (${option.change_pct >= 0 ? '+' : ''}${option.change_pct.toFixed(2)}%) · Exp ${expiryNorm}`,
      }
    );
  };

  const handleCryptoSelect = (crypto) => {
    setStockData(null);
    setPivotPoint(null);
    setGannFan(null);
    setSignal(null);
    setSelectedStock(crypto);
    setCryptoChartDays(7);
    fetchCryptoData(crypto.coin_id, 7);
    setMobilePanel('chart');
  };

  const handleTimeframeChange = (tf) => {
    setTimeframe(tf);
    if (selectedStock) {
      setPivotPoint(null);
      setGannFan(null);
      setSignal(null);
      if (selectedStock.type === 'CRYPTO') {
        // Map timeframe to crypto days
        const daysMap = { '5M': 1, '10M': 1, '15M': 1, '30M': 1, '1H': 1, '4H': 1, '1D': 7, '1W': 30, '1M': 30, '6M': 180, '1Y': 365 };
        const days = daysMap[tf.label] || 7;
        setCryptoChartDays(days);
        fetchCryptoData(selectedStock.coin_id, days);
      } else if (selectedStock.type === 'OPTION' && selectedStock.selectedOption) {
        // Options support 1m / 5m / 15m intraday only (NSE chart-databyindex tick data)
        const optIntervalMap = { '1MIN': 1, '5M': 5, '10M': 10, '15M': 15 };
        const ivm = optIntervalMap[tf.label] || 1;
        fetchOptionIntraday(selectedStock.selectedOption, ivm);
      } else {
        fetchStockData(selectedStock.ticker, tf);
      }
    }
  };

  const handlePivotSelect = async (pivot) => {
    setPivotPoint(pivot);
    if (!pivot) return;
    try {
      const response = await axios.post(`${API}/gann/fan`, {
        ticker: selectedStock.ticker,
        pivot_price: pivot.price,
        pivot_timestamp: pivot.timestamp,
        bars_count: 50
      });
      setGannFan(response.data);
      toast.success('Gann Fan calculated');
      fetchSignal(pivot);
    } catch (error) {
      toast.error('Failed to calculate Gann Fan');
    }
  };

  const fetchSignal = async (pivot) => {
    if (!selectedStock || !pivot || selectedStock.type === 'CRYPTO' || selectedStock.type === 'OPTION') return;
    try {
      const response = await axios.get(`${API}/signal/${selectedStock.ticker}`, {
        params: { pivot_price: pivot.price, pivot_timestamp: pivot.timestamp }
      });
      setSignal(response.data);
    } catch (error) { /* silent */ }
  };

  useEffect(() => {
    if (pivotPoint && selectedStock && selectedStock.type !== 'CRYPTO' && selectedStock.type !== 'OPTION') {
      const interval = setInterval(() => fetchSignal(pivotPoint), 60000);
      return () => clearInterval(interval);
    }
  }, [pivotPoint, selectedStock]);

  const isCrypto = selectedStock?.type === 'CRYPTO';
  const isOption = selectedStock?.type === 'OPTION';

  const rightTabs = [
    { id: 'scanner', label: 'SCANNER' },
    { id: 'strategies', label: 'STRATEGIES' },
    { id: 'ghost', label: 'GHOST' },
    { id: 'backtest', label: 'BACKTEST' },
  ];

  const leftTabs = [
    { id: 'search', label: 'Search' },
    { id: 'crypto', label: 'Crypto', icon: CurrencyBtc },
    { id: 'watchlist', label: 'Watchlist', icon: Star },
    { id: 'groww', label: 'Groww', icon: Lightning },
    { id: 'portfolio', label: 'Portfolio', icon: Wallet },
    { id: 'alerts', label: 'Alerts', icon: Bell },
  ];

  const mobilePanels = [
    { id: 'left', label: 'Menu', icon: List },
    { id: 'chart', label: 'Chart', icon: ChartLineUp },
    { id: 'right', label: 'Strategies', icon: Star },
  ];

  return (
    <div className="h-screen overflow-hidden bg-[#0A0A0A] text-white flex flex-col" data-testid="trading-dashboard">
      <Toaster theme="dark" position="top-right" richColors />

      {/* HYBRID MODE OVERLAY */}
      {hybridMode && (
        <HybridDashboard onBack={() => setHybridMode(false)} />
      )}

      {/* Normal Gann Trader UI (hidden when hybrid mode is on) */}
      {!hybridMode && (<>

      {/* Header */}
      <header className="h-12 md:h-14 border-b border-white/10 flex items-center justify-between px-3 lg:px-6 bg-[#0A0A0A]/90 backdrop-blur-md z-50 shrink-0" data-testid="dashboard-header">
        <div className="flex items-center gap-3">
          <h1 className="text-sm md:text-lg font-black tracking-tighter uppercase" style={{ fontFamily: "'Chivo', sans-serif" }}>
            <span className="text-white">GANN</span>
            <span className="text-[#00E676] ml-1">TRADER</span>
          </h1>
          <span className="hidden sm:inline text-[10px] text-zinc-500 font-mono tracking-wider border border-white/10 px-2 py-0.5">
            {isCrypto ? 'CRYPTO' : 'NSE'}
          </span>
        </div>
        <div className="flex items-center gap-2 md:gap-3">
          {selectedStock && (
            <div className="flex items-center gap-1.5">
              {isCrypto && selectedStock.image && (
                <img src={selectedStock.image} alt="" className="w-4 h-4 rounded-full" />
              )}
              <span className="text-[10px] md:text-xs font-mono text-[#00E676]" data-testid="selected-ticker">
                {isCrypto
                  ? selectedStock.symbol?.toUpperCase()
                  : isOption
                  ? selectedStock.name
                  : selectedStock.ticker}
              </span>
              {!isOption && (
                <span className="hidden sm:inline text-[10px] text-zinc-500">{selectedStock.name}</span>
              )}
              {isOption && selectedStock.expiry && (
                <span className="hidden sm:inline text-[10px] text-zinc-500">Exp {selectedStock.expiry}</span>
              )}
              {!isCrypto && !isOption && (
                <button
                  onClick={() => setShowNews(true)}
                  className="ml-1 p-1 rounded hover:bg-white/10 transition-colors"
                  title="View News"
                  data-testid="news-btn"
                >
                  <Newspaper size={14} className="text-sky-400" />
                </button>
              )}
            </div>
          )}
          {/* HYBRID MODE BUTTON */}
          <button
            onClick={() => setHybridMode(true)}
            className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest border border-[#3366FF]/50 text-[#3366FF] hover:bg-[#3366FF]/15 hover:border-[#3366FF] px-2.5 py-1.5 rounded transition-all duration-200"
            data-testid="hybrid-mode-btn"
            title="Switch to QSC Hybrid Mode"
          >
            <ArrowsLeftRight size={12} weight="bold" />
            <span className="hidden sm:inline">HYBRID</span>
          </button>
        </div>
      </header>

      {/* Indices Live Ticker — NIFTY 50 / SENSEX / BANK NIFTY (tap → top options) */}
      <IndicesTickerBar onIndexClick={handleIndexClick} />

      {/* Mobile Tab Bar — full-width 3-panel nav */}
      <div className="flex lg:hidden border-b border-white/10 shrink-0 bg-[#0D0D0D]">
        {mobilePanels.map(p => (
          <button key={p.id} onClick={() => setMobilePanel(p.id)}
            className={`flex-1 py-3 flex flex-col items-center justify-center gap-0.5 transition-colors ${
              mobilePanel === p.id
                ? 'text-white border-b-2 border-[#00E676] bg-white/5'
                : 'text-zinc-500'
            }`}
            data-testid={`mobile-panel-${p.id}`}>
            <p.icon size={16} weight={mobilePanel === p.id ? 'fill' : 'regular'} />
            <span className="text-[8px] font-bold uppercase tracking-widest">{p.label}</span>
          </button>
        ))}
      </div>

      {/* Main Grid — flex-1 to fill remaining space */}
      <div className="flex-1 flex flex-col lg:grid lg:grid-cols-12 overflow-hidden min-h-0">

        {/* Left Sidebar */}
        <aside className={`lg:col-span-3 xl:col-span-2 border-r border-white/10 flex flex-col overflow-y-auto ${mobilePanel !== 'left' ? 'hidden lg:flex' : 'flex'}`} data-testid="left-sidebar">
          {/* Left Tabs — horizontally scrollable on mobile */}
          <div className="flex border-b border-white/10 shrink-0 overflow-x-auto scrollbar-none">
            {leftTabs.map(tab => (
              <button key={tab.id} onClick={() => setLeftTab(tab.id)}
                className={`flex-shrink-0 flex-1 min-w-[56px] py-2.5 px-1 text-[9px] font-bold uppercase tracking-[0.1em] transition-colors whitespace-nowrap ${
                  leftTab === tab.id ? 'text-white border-b-2 border-[#00E676] bg-white/5' : 'text-zinc-500 active:text-zinc-300'
                }`}
                data-testid={`left-tab-${tab.id}`}>
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto">
            {leftTab === 'search' && (
              <>
                <div className="p-3 border-b border-white/10">
                  <StockSearch onStockSelect={handleStockSelect} selectedStock={selectedStock} />
                </div>
                {/* GannQSC — super-fast in-RAM signal (auto-feeds when chart loads) */}
                {stockData?.bars?.length > 0 && selectedStock && (
                  <div className="border-b border-white/10 p-3">
                    <GannQSCPanel
                      bars={stockData.bars}
                      ticker={isCrypto ? selectedStock.symbol : selectedStock.ticker}
                    />
                  </div>
                )}
                {/* Regulatory Watchdog — global + Indian market sentiment */}
                <div className="border-b border-white/10 p-3">
                  <RegulatoryWatchdogPanel />
                </div>
                {signal && <div className="border-b border-white/10"><SignalDashboard signal={signal} /></div>}
                {stockData && !isCrypto && <div className="border-b border-white/10"><SquareOf9Calculator currentPrice={stockData.bars[stockData.bars.length - 1]?.close} /></div>}
                {selectedStock && selectedStock.type === 'INDEX' && <div className="border-b border-white/10"><OIAnalysis symbol={selectedStock.ticker.replace('.NS', '')} /></div>}
              </>
            )}
            {leftTab === 'crypto' && (
              <CryptoList onCryptoSelect={handleCryptoSelect} selectedCrypto={isCrypto ? selectedStock : null} />
            )}
            {leftTab === 'watchlist' && <Watchlist onStockSelect={handleStockSelect} selectedStock={selectedStock} />}
            {leftTab === 'groww' && <GrowwPortfolio />}
            {leftTab === 'portfolio' && <PortfolioTracker selectedStock={selectedStock} />}
            {leftTab === 'alerts' && <AlertSystem selectedStock={selectedStock} />}
          </div>
        </aside>

        {/* Center Chart */}
        <main className={`flex-1 lg:col-span-6 xl:col-span-7 flex flex-col relative min-h-0 overflow-hidden ${mobilePanel !== 'chart' ? 'hidden lg:flex' : 'flex'}`} data-testid="center-chart">
          {/* Chart — flex-1 fills space above OrderFlow, minHeight ensures chart init works */}
          <div className="flex-1 min-h-0" style={{ minHeight: '200px' }}>
            <ChartPanel
              stockData={stockData}
              loading={loading}
              selectedStock={selectedStock}
              onPivotSelect={handlePivotSelect}
              pivotPoint={pivotPoint}
              gannFan={gannFan}
              semiLogScale={semiLogScale}
              setSemiLogScale={setSemiLogScale}
              timeframe={timeframe}
              onTimeframeChange={handleTimeframeChange}
              isCrypto={isCrypto}
              dataSource={dataSource}
              onDataSourceChange={(s) => {
                setDataSource(s);
                if (selectedStock && !isCrypto) {
                  fetchStockData(selectedStock.ticker, timeframe, s);
                }
              }}
            />
          </div>
          {/* Order Flow Panel — below chart, scroll to see */}
          {stockData?.bars?.length >= 30 && (
            <OrderFlowPanel stockData={stockData} selectedStock={selectedStock} />
          )}
        </main>

        {/* Right Sidebar */}
        <aside className={`lg:col-span-3 border-l border-white/10 flex flex-col overflow-hidden ${mobilePanel !== 'right' ? 'hidden lg:flex' : 'flex'}`} data-testid="right-sidebar">
          {/* Tabs — horizontally scrollable on mobile */}
          <div className="flex border-b border-white/10 shrink-0 overflow-x-auto scrollbar-none">
            {rightTabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex-shrink-0 flex-1 min-w-[64px] py-2.5 px-2 text-[9px] font-bold uppercase tracking-[0.1em] transition-colors whitespace-nowrap ${
                  activeTab === tab.id ? 'text-white border-b-2 border-[#00E676] bg-white/5' : 'text-zinc-500 active:text-zinc-300'
                }`}
                data-testid={`tab-${tab.id}`}>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'scanner' && (
              <AutoScanner selectedStock={selectedStock} />
            )}

            {activeTab === 'strategies' && (
              <div className="divide-y divide-white/10">
                {selectedStock && stockData && (
                  <>
                    {isCrypto && <CryptoDashboard preSelectedCoin={selectedStock} />}
                    <SMCAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <AMDSAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <MiroFishAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <PACSOAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <GPTAnalysis stockData={stockData} selectedStock={selectedStock} timeframe={timeframe} />
                    <AITradeAnalysis stockData={stockData} selectedStock={selectedStock} timeframe={timeframe} />
                    <FallingKnifeAnalysis stockData={stockData} selectedStock={selectedStock} timeframe={timeframe} />
                    <ReversePriceSwings stockData={stockData} selectedStock={selectedStock} />
                    <ExplosiveVolumeAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <GoldenSetupAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <AIIndicatorScore stockData={stockData} selectedStock={selectedStock} />
                    <GodzillaSetupAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <DemonAnalysis stockData={stockData} selectedStock={selectedStock} />
                    <NarrativeSwingAnalysis stockData={stockData} selectedStock={selectedStock} />
                  </>
                )}
                {!selectedStock && (
                  <div className="p-6 text-center">
                    <p className="text-zinc-500 text-sm">Select a stock or crypto to view strategies</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'ghost' && (
              <GhostModeScanner onStockSelect={handleStockSelect} />
            )}

            {activeTab === 'backtest' && (
              <BacktestModule selectedStock={selectedStock} />
            )}
          </div>
        </aside>
      </div>

      {/* News Popup */}
      {showNews && selectedStock && !isCrypto && !isOption && (
        <StockNewsPopup
          ticker={selectedStock.ticker}
          onClose={() => setShowNews(false)}
        />
      )}

      {/* Top Options Sheet (opens when an index pill is tapped) */}
      {optionsSheet && (
        <TopOptionsSheet
          symbol={optionsSheet.symbol}
          name={optionsSheet.name}
          onClose={() => setOptionsSheet(null)}
          onOptionSelect={handleOptionSelect}
        />
      )}
    </>)}
    </div>
  );
};

export default TradingDashboard;
