import { useEffect, useState, useRef, useCallback } from "react";
import {
  Lightning, ArrowsLeftRight, Shield, ChartLineUp, ChartBar,
  Database, List, ArrowLeft
} from "@phosphor-icons/react";
import {
  fetchAssets, fetchPriceSeries, fetchCorrelation, fetchRegulatory,
  fetchPositions, fetchPortfolio, listTrades, listSignals,
  openPriceSocket, executeTrade, closeTrade, generateSignal, fetchOrderBook,
} from "../../lib/hybridApi";
import { toast } from "sonner";

import TickerStrip   from "./TickerStrip";
import LivePriceChart from "./LivePriceChart";
import OrderBook     from "./OrderBook";
import QSCSignalPanel    from "./QSCSignalPanel";
import CorrelationHeatmap from "./CorrelationHeatmap";
import RegulatoryGauge   from "./RegulatoryGauge";
import PositionsTable    from "./PositionsTable";
import TradesLog         from "./TradesLog";
import ExecutionPanel    from "./ExecutionPanel";
import PortfolioSummary  from "./PortfolioSummary";

const CRYPTO_OPTIONS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"];

export default function HybridDashboard({ onBack }) {
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT");
  const [livePrices,  setLivePrices]  = useState({});
  const [assets,      setAssets]      = useState([]);
  const [series,      setSeries]      = useState([]);
  const [book,        setBook]        = useState(null);
  const [correlation, setCorrelation] = useState({ symbols: [], cells: [] });
  const [regulatory,  setRegulatory]  = useState(null);
  const [positions,   setPositions]   = useState([]);
  const [portfolio,   setPortfolio]   = useState({});
  const [trades,      setTrades]      = useState([]);
  const [signals,     setSignals]     = useState([]);
  const [genLoading,  setGenLoading]  = useState(false);
  const wsRef = useRef(null);

  const refreshAll = useCallback(async () => {
    try {
      const [a, c, r, p, port, t, sg] = await Promise.all([
        fetchAssets(), fetchCorrelation(), fetchRegulatory(),
        fetchPositions(), fetchPortfolio(), listTrades(), listSignals(),
      ]);
      setAssets(a); setCorrelation(c); setRegulatory(r);
      setPositions(p); setPortfolio(port); setTrades(t); setSignals(sg);
    } catch { /* noop */ }
  }, []);

  const refreshChart = useCallback(async () => {
    try {
      const [s, b] = await Promise.all([
        fetchPriceSeries(selectedSymbol, 120),
        fetchOrderBook(selectedSymbol),
      ]);
      setSeries(s); setBook(b);
    } catch { /* noop */ }
  }, [selectedSymbol]);

  useEffect(() => {
    refreshAll();
    const id = setInterval(refreshAll, 5000);
    return () => clearInterval(id);
  }, [refreshAll]);

  useEffect(() => {
    refreshChart();
    const id = setInterval(refreshChart, 2500);
    return () => clearInterval(id);
  }, [refreshChart]);

  useEffect(() => {
    const sock = openPriceSocket((msg) => {
      if (msg?.type === "tick") setLivePrices(msg.prices);
    });
    wsRef.current = sock;
    return () => { try { sock.close(); } catch {} };
  }, []);

  const onGenerateSignal = async () => {
    setGenLoading(true);
    try {
      const sig = await generateSignal(selectedSymbol);
      setSignals((prev) => [sig, ...prev].slice(0, 10));
      toast.success(`Signal: ${sig.direction} ${sig.symbol} • conf ${(sig.confidence * 100).toFixed(0)}%`);
    } catch { toast.error("Signal generation failed"); }
    finally { setGenLoading(false); }
  };

  const onExecute = async (payload) => {
    try {
      const t = await executeTrade(payload);
      toast.success(`Executed ${t.direction} ${t.total_volume} ${t.symbol} @ ${t.avg_price}`);
      refreshAll();
    } catch (e) { toast.error(e?.response?.data?.detail || "Trade failed"); }
  };

  const onClose = async (id) => {
    try {
      const r = await closeTrade(id);
      toast.success(`Closed • PnL ${r.pnl >= 0 ? "+" : ""}${r.pnl}`);
      refreshAll();
    } catch { toast.error("Close failed"); }
  };

  return (
    <div className="hybrid-mode min-h-screen w-full grid-bg" data-testid="hybrid-dashboard">
      {/* TOP BAR */}
      <header className="border-b border-white/10 px-4 lg:px-6 py-3 flex items-center justify-between bg-[#0A0A0A] sticky top-0 z-30">
        <div className="flex items-center gap-3">
          {/* Back button */}
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-widest text-zinc-400 hover:text-white border border-white/10 hover:border-white/30 px-2.5 py-1.5 transition-colors"
            data-testid="hybrid-back-btn"
          >
            <ArrowLeft size={12} />
            <span>Exit</span>
          </button>
          <div className="w-px h-5 bg-white/10" />
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-[#3366FF] pulse-dot rounded-full" />
            <span className="font-display text-xl tracking-tighter font-semibold">
              QSC<span className="text-[#3366FF]">.</span>ENGINE
            </span>
          </div>
          <span className="text-[10px] font-mono text-neutral-500 hidden md:inline" data-testid="hybrid-tagline">
            QUANTUM-CASCADE SIGNAL CORE / PAPER-TRADING SIMULATOR
          </span>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-mono uppercase tracking-widest text-neutral-400">
          <span className="flex items-center gap-1.5">
            <Lightning size={12} className="text-[#3366FF]" /> Live
          </span>
          <span className="hidden md:inline">SIM-MODE</span>
          <span className="text-white">{new Date().toUTCString().slice(17, 25)} UTC</span>
        </div>
      </header>

      {/* TICKER STRIP */}
      <TickerStrip assets={assets} livePrices={livePrices} />

      {/* MAIN GRID */}
      <main className="px-4 lg:px-6 py-5 grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT */}
        <aside className="lg:col-span-3 flex flex-col gap-4">
          <HybridWatchlist assets={assets} livePrices={livePrices} selected={selectedSymbol} onSelect={setSelectedSymbol} />
          <ExecutionPanel symbol={selectedSymbol} onExecute={onExecute} regulatory={regulatory} />
        </aside>

        {/* CENTER */}
        <section className="lg:col-span-6 flex flex-col gap-4">
          <LivePriceChart
            symbol={selectedSymbol}
            series={series}
            livePrice={livePrices[selectedSymbol]}
            onChangeSymbol={setSelectedSymbol}
            options={CRYPTO_OPTIONS}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <OrderBook book={book} />
            <QSCSignalPanel
              signals={signals}
              selectedSymbol={selectedSymbol}
              onGenerate={onGenerateSignal}
              loading={genLoading}
            />
          </div>
        </section>

        {/* RIGHT */}
        <aside className="lg:col-span-3 flex flex-col gap-4">
          <PortfolioSummary portfolio={portfolio} />
          <RegulatoryGauge data={regulatory} />
        </aside>

        {/* BOTTOM */}
        <div className="lg:col-span-7">
          <CorrelationHeatmap data={correlation} />
        </div>
        <div className="lg:col-span-5">
          <PositionsTable positions={positions} onClose={(id) => onClose(id)} />
        </div>
        <div className="lg:col-span-12">
          <TradesLog trades={trades} />
        </div>
      </main>

      <footer className="px-6 py-4 text-center text-[9px] font-mono uppercase tracking-widest text-neutral-700">
        QSC ENGINE V1.0 / PAPER-TRADING ONLY / NOT FINANCIAL ADVICE
      </footer>
    </div>
  );
}

/* ---- Watchlist sub-component ---- */
function HybridWatchlist({ assets, livePrices, selected, onSelect }) {
  const groups = { crypto: [], stock: [], commodity: [], macro: [] };
  for (const a of assets) groups[a.asset_class]?.push(a);

  const Section = ({ label, icon, items }) => (
    <div className="border-t border-white/5 first:border-t-0">
      <div className="px-4 py-2 text-[9px] font-bold uppercase tracking-[0.2em] text-neutral-500 flex items-center gap-1.5">
        {icon}{label}
      </div>
      {items.map((a) => {
        const price = livePrices[a.symbol] ?? a.price;
        const up = a.change_24h >= 0;
        const isSel = a.symbol === selected;
        return (
          <button
            key={a.symbol}
            onClick={() => onSelect(a.symbol)}
            data-testid={`hybrid-watch-${a.symbol}`}
            className={`w-full text-left px-4 py-2 flex items-center justify-between font-mono text-xs transition-colors ${isSel ? "bg-white/10" : "hover:bg-white/5"}`}
          >
            <div>
              <span className="text-white block">{a.symbol}</span>
              <span className="text-neutral-500 text-[9px]">{a.name}</span>
            </div>
            <div className="text-right">
              <span className="text-white block" data-testid={`hybrid-price-${a.symbol}`}>
                {price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </span>
              <span style={{ color: up ? "#3366FF" : "#FF3333" }} className="text-[9px]">
                {up ? "+" : ""}{a.change_24h?.toFixed(2)}%
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="qsc-card" data-testid="hybrid-watchlist">
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <Database size={13} className="text-neutral-400" />
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-400">Watchlist</span>
      </div>
      <Section label="Crypto"      icon={<ChartLineUp size={11} />}  items={groups.crypto} />
      <Section label="Equities"    icon={<ChartBar size={11} />}     items={groups.stock} />
      <Section label="Commodities" icon={<Lightning size={11} />}    items={groups.commodity} />
      <Section label="Macro"       icon={<Shield size={11} />}       items={groups.macro} />
    </div>
  );
}
