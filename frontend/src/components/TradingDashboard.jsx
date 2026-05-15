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

  const fetchStockData = async (ticker, tf) => {
    setLoading(true);
    try {
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
    if (!selectedStock || !pivot || selectedStock.type === 'CRYPTO') return;
    try {
      const response = await axios.get(`${API}/signal/${selectedStock.ticker}`, {
        params: { pivot_price: pivot.price, pivot_timestamp: pivot.timestamp }
      });
      setSignal(response.data);
    } catch (error) { /* silent */ }
  };

  useEffect(() => {
    if (pivotPoint && selectedStock && selectedStock.type !== 'CRYPTO') {
      const interval = setInterval(() => fetchSignal(pivotPoint), 60000);
      return () => clearInterval(interval);
    }
  }, [pivotPoint, selectedStock]);

  const isCrypto = selectedStock?.type === 'CRYPTO';

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
    { id: 'portfolio', label: 'Portfolio', icon: Wallet },
    { id: 'alerts', label: 'Alerts', icon: Bell },
  ];

  const mobilePanels = [
    { id: 'left', label: 'Menu', icon: List },
    { id: 'chart', label: 'Chart', icon: ChartLineUp },
    { id: 'right', label: 'Strategies', icon: Star },
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex flex-col" data-testid="trading-dashboard">
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
                {isCrypto ? selectedStock.symbol?.toUpperCase() : selectedStock.ticker}
              </span>
              <span className="hidden sm:inline text-[10px] text-zinc-500">{selectedStock.name}</span>
              {!isCrypto && (
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

      {/* Mobile Tab Bar */}
      <div className="flex lg:hidden border-b border-white/10 shrink-0">
        {mobilePanels.map(p => (
          <button key={p.id} onClick={() => setMobilePanel(p.id)}
            className={`flex-1 py-2 flex items-center justify-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.15em] transition-colors ${
              mobilePanel === p.id ? 'text-white border-b-2 border-white bg-white/5' : 'text-zinc-500'
            }`}
            data-testid={`mobile-panel-${p.id}`}>
            <p.icon size={12} weight={mobilePanel === p.id ? 'fill' : 'regular'} />
            {p.label}
          </button>
        ))}
      </div>

      {/* Main Grid */}
      <div className="flex-1 flex flex-col lg:grid lg:grid-cols-12 overflow-hidden" style={{ height: 'calc(100vh - 56px)' }}>

        {/* Left Sidebar */}
        <aside className={`lg:col-span-3 xl:col-span-2 border-r border-white/10 flex flex-col overflow-y-auto ${mobilePanel !== 'left' ? 'hidden lg:flex' : 'flex'}`} data-testid="left-sidebar">
          {/* Left Tabs */}
          <div className="flex border-b border-white/10 shrink-0">
            {leftTabs.map(tab => (
              <button key={tab.id} onClick={() => setLeftTab(tab.id)}
                className={`flex-1 py-2 text-[9px] font-bold uppercase tracking-[0.15em] transition-colors ${
                  leftTab === tab.id ? 'text-white border-b-2 border-white bg-white/5' : 'text-zinc-500 hover:text-zinc-300'
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
                {signal && <div className="border-b border-white/10"><SignalDashboard signal={signal} /></div>}
                {stockData && !isCrypto && <div className="border-b border-white/10"><SquareOf9Calculator currentPrice={stockData.bars[stockData.bars.length - 1]?.close} /></div>}
                {selectedStock && selectedStock.type === 'INDEX' && <div className="border-b border-white/10"><OIAnalysis symbol={selectedStock.ticker.replace('.NS', '')} /></div>}
              </>
            )}
            {leftTab === 'crypto' && (
              <CryptoList onCryptoSelect={handleCryptoSelect} selectedCrypto={isCrypto ? selectedStock : null} />
            )}
            {leftTab === 'watchlist' && <Watchlist onStockSelect={handleStockSelect} selectedStock={selectedStock} />}
            {leftTab === 'portfolio' && <PortfolioTracker selectedStock={selectedStock} />}
            {leftTab === 'alerts' && <AlertSystem selectedStock={selectedStock} />}
          </div>
        </aside>

        {/* Center Chart */}
        <main className={`lg:col-span-6 xl:col-span-7 flex flex-col relative min-h-[300px] lg:min-h-0 ${mobilePanel !== 'chart' ? 'hidden lg:flex' : 'flex'}`} data-testid="center-chart">
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
          />
        </main>

        {/* Right Sidebar */}
        <aside className={`lg:col-span-3 border-l border-white/10 flex flex-col overflow-hidden ${mobilePanel !== 'right' ? 'hidden lg:flex' : 'flex'}`} data-testid="right-sidebar">
          {/* Tabs */}
          <div className="flex border-b border-white/10 shrink-0">
            {rightTabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-2.5 text-[9px] font-bold uppercase tracking-[0.15em] transition-colors ${
                  activeTab === tab.id ? 'text-white border-b-2 border-white bg-white/5' : 'text-zinc-500 hover:text-zinc-300'
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
      {showNews && selectedStock && !isCrypto && (
        <StockNewsPopup
          ticker={selectedStock.ticker}
          onClose={() => setShowNews(false)}
        />
      )}
    </>)}
    </div>
  );
};

export default TradingDashboard;
