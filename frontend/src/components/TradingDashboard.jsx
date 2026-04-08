import React, { useState, useEffect } from 'react';
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
import { Toaster } from 'sonner';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TradingDashboard = () => {
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockData, setStockData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pivotPoint, setPivotPoint] = useState(null);
  const [gannFan, setGannFan] = useState(null);
  const [signal, setSignal] = useState(null);
  const [semiLogScale, setSemiLogScale] = useState(false);
  const [timeframe, setTimeframe] = useState({ multiplier: 1, timespan: 'day', label: '1D' });
  const [activeTab, setActiveTab] = useState('strategies');

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

  const handleStockSelect = (stock) => {
    setStockData(null);
    setPivotPoint(null);
    setGannFan(null);
    setSignal(null);
    setSelectedStock(stock);
    const defaultTf = { multiplier: 1, timespan: 'day', label: '1D' };
    setTimeframe(defaultTf);
    fetchStockData(stock.ticker, defaultTf);
  };

  const handleTimeframeChange = (tf) => {
    setTimeframe(tf);
    if (selectedStock) {
      setPivotPoint(null);
      setGannFan(null);
      setSignal(null);
      fetchStockData(selectedStock.ticker, tf);
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
    if (!selectedStock || !pivot) return;
    try {
      const response = await axios.get(`${API}/signal/${selectedStock.ticker}`, {
        params: { pivot_price: pivot.price, pivot_timestamp: pivot.timestamp }
      });
      setSignal(response.data);
    } catch (error) { /* silent */ }
  };

  useEffect(() => {
    if (pivotPoint && selectedStock) {
      const interval = setInterval(() => fetchSignal(pivotPoint), 60000);
      return () => clearInterval(interval);
    }
  }, [pivotPoint, selectedStock]);

  const tabs = [
    { id: 'strategies', label: 'STRATEGIES' },
    { id: 'ghost', label: 'GHOST' },
    { id: 'tools', label: 'TOOLS' },
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex flex-col" data-testid="trading-dashboard">
      <Toaster theme="dark" position="top-right" richColors />

      {/* Header */}
      <header className="h-14 border-b border-white/10 flex items-center justify-between px-4 lg:px-6 bg-[#0A0A0A]/90 backdrop-blur-md z-50 shrink-0" data-testid="dashboard-header">
        <div className="flex items-center gap-4">
          <h1 className="text-base lg:text-lg font-black tracking-tighter uppercase" style={{ fontFamily: "'Chivo', sans-serif" }}>
            <span className="text-white">GANN</span>
            <span className="text-[#00E676] ml-1">TRADER</span>
          </h1>
          <span className="hidden md:inline text-[10px] text-zinc-500 font-mono tracking-wider border border-white/10 px-2 py-0.5">NSE</span>
        </div>
        <div className="flex items-center gap-3">
          {selectedStock && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-[#00E676]" data-testid="selected-ticker">{selectedStock.ticker}</span>
              <span className="text-[10px] text-zinc-500">{selectedStock.name}</span>
            </div>
          )}
        </div>
      </header>

      {/* Main Grid */}
      <div className="flex-1 flex flex-col lg:grid lg:grid-cols-12 overflow-hidden">

        {/* Left Sidebar */}
        <aside className="lg:col-span-3 xl:col-span-2 border-b lg:border-b-0 lg:border-r border-white/10 flex flex-col overflow-y-auto" data-testid="left-sidebar">
          <div className="p-3 border-b border-white/10">
            <StockSearch onStockSelect={handleStockSelect} selectedStock={selectedStock} />
          </div>

          {signal && (
            <div className="border-b border-white/10">
              <SignalDashboard signal={signal} />
            </div>
          )}

          {stockData && (
            <div className="border-b border-white/10">
              <SquareOf9Calculator currentPrice={stockData.bars[stockData.bars.length - 1]?.close} />
            </div>
          )}

          {selectedStock && selectedStock.type === 'INDEX' && (
            <div className="border-b border-white/10">
              <OIAnalysis symbol={selectedStock.ticker.replace('.NS', '')} />
            </div>
          )}
        </aside>

        {/* Center Chart */}
        <main className="lg:col-span-6 xl:col-span-7 flex flex-col relative min-h-[400px] lg:min-h-0" data-testid="center-chart">
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
          />
        </main>

        {/* Right Sidebar */}
        <aside className="lg:col-span-3 border-t lg:border-t-0 lg:border-l border-white/10 flex flex-col overflow-hidden" data-testid="right-sidebar">
          {/* Tabs */}
          <div className="flex border-b border-white/10 shrink-0">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-2.5 text-[10px] font-bold uppercase tracking-[0.2em] transition-colors ${
                  activeTab === tab.id
                    ? 'text-white border-b-2 border-white bg-white/5'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
                data-testid={`tab-${tab.id}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'strategies' && (
              <div className="divide-y divide-white/10">
                {selectedStock && stockData && (
                  <>
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
                    <p className="text-zinc-500 text-sm">Select a stock to view strategies</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'ghost' && (
              <GhostModeScanner onStockSelect={handleStockSelect} />
            )}

            {activeTab === 'tools' && (
              <div className="divide-y divide-white/10">
                {selectedStock && selectedStock.type === 'INDEX' && (
                  <OIAnalysis symbol={selectedStock.ticker.replace('.NS', '')} />
                )}
                {stockData && (
                  <SquareOf9Calculator currentPrice={stockData.bars[stockData.bars.length - 1]?.close} />
                )}
                {!selectedStock && (
                  <div className="p-6 text-center">
                    <p className="text-zinc-500 text-sm">Select a stock to use tools</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

export default TradingDashboard;
