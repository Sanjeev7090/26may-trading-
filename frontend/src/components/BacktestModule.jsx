import React, { useState } from 'react';
import axios from 'axios';
import { ChartLineUp, TrendUp, TrendDown, Target } from '@phosphor-icons/react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const strategies = [
  { id: 'falling_knife', label: 'Falling Knife', color: '#FF3B30' },
  { id: 'golden_setup', label: 'Golden Setup', color: '#F5A623' },
  { id: 'reverse_swings', label: 'Reverse Swings', color: '#A855F7' },
  { id: 'godzilla', label: 'Godzilla', color: '#FF0055' },
  { id: 'demon', label: 'DEMON', color: '#007AFF' },
];

const BacktestModule = ({ selectedStock }) => {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState('demon');
  const [days, setDays] = useState(365);
  const [showTrades, setShowTrades] = useState(false);

  const runBacktest = async () => {
    if (!selectedStock) { toast.error('Select a stock first'); return; }
    setLoading(true);
    setResults(null);
    try {
      const response = await axios.post(`${API}/backtest`, {
        ticker: selectedStock.ticker,
        strategy: selectedStrategy,
        days: days
      });
      setResults(response.data);
      toast.success(`Backtest complete: ${response.data.total_trades} trades`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Backtest failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-3" data-testid="backtest-module">
      <div className="flex items-center gap-2 mb-3">
        <ChartLineUp size={14} className="text-[#00E676]" weight="bold" />
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">Backtest</span>
      </div>

      {/* Strategy Selector */}
      <div className="flex flex-wrap gap-1 mb-2">
        {strategies.map(s => (
          <button key={s.id} onClick={() => setSelectedStrategy(s.id)}
            className={`px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider transition-all ${
              selectedStrategy === s.id ? 'text-black' : 'text-zinc-500 hover:text-white'
            }`}
            style={selectedStrategy === s.id ? { backgroundColor: s.color } : {}}
            data-testid={`backtest-strategy-${s.id}`}>
            {s.label}
          </button>
        ))}
      </div>

      {/* Period + Run */}
      <div className="flex items-center gap-2 mb-3">
        <div className="flex gap-1">
          {[90, 180, 365, 730].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-1.5 py-0.5 text-[9px] font-mono font-bold transition-all ${
                days === d ? 'bg-white text-black' : 'text-zinc-500 hover:text-white'
              }`}
              data-testid={`backtest-days-${d}`}>
              {d < 365 ? `${d}D` : `${Math.round(d/365)}Y`}
            </button>
          ))}
        </div>
        <button onClick={runBacktest} disabled={loading || !selectedStock}
          className="flex-1 py-1 text-[10px] font-bold uppercase tracking-wider bg-[#00E676] text-black hover:bg-[#00C864] transition-colors disabled:opacity-50"
          data-testid="backtest-run-btn">
          {loading ? 'Running...' : 'Run Backtest'}
        </button>
      </div>

      {loading && (
        <div className="py-4 text-center">
          <p className="text-[10px] text-zinc-500 font-mono animate-pulse">Analyzing {days} days of historical data...</p>
        </div>
      )}

      {/* Results */}
      {results && !loading && (
        <div className="animate-fade-in space-y-2">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-1" data-testid="backtest-results">
            <div className="border border-white/5 p-1.5 text-center">
              <p className="text-[9px] text-zinc-500">Trades</p>
              <p className="text-sm font-mono font-bold text-white">{results.total_trades}</p>
            </div>
            <div className="border border-white/5 p-1.5 text-center">
              <p className="text-[9px] text-zinc-500">Win Rate</p>
              <p className={`text-sm font-mono font-bold ${results.win_rate >= 50 ? 'text-[#00E676]' : 'text-[#FF3B30]'}`} data-testid="backtest-winrate">
                {results.win_rate}%
              </p>
            </div>
            <div className="border border-white/5 p-1.5 text-center">
              <p className="text-[9px] text-zinc-500">Total Return</p>
              <p className={`text-sm font-mono font-bold ${results.total_return >= 0 ? 'text-[#00E676]' : 'text-[#FF3B30]'}`} data-testid="backtest-return">
                {results.total_return >= 0 ? '+' : ''}{results.total_return}%
              </p>
            </div>
            <div className="border border-white/5 p-1.5 text-center">
              <p className="text-[9px] text-zinc-500">Max Drawdown</p>
              <p className="text-sm font-mono font-bold text-[#FF3B30]">{results.max_drawdown}%</p>
            </div>
          </div>

          {/* Win/Loss Bar */}
          <div>
            <div className="flex justify-between text-[9px] font-mono text-zinc-500 mb-0.5">
              <span>{results.winning_trades}W</span><span>{results.losing_trades}L</span>
            </div>
            <div className="flex h-2 overflow-hidden">
              <div className="bg-[#00E676]" style={{ width: `${results.win_rate}%` }} />
              <div className="bg-[#FF3B30]" style={{ width: `${100 - results.win_rate}%` }} />
            </div>
          </div>

          {/* Avg Return */}
          <div className="text-center py-1 border border-white/5">
            <p className="text-[9px] text-zinc-500">Avg Return/Trade</p>
            <p className={`text-xs font-mono font-bold ${results.avg_return >= 0 ? 'text-[#00E676]' : 'text-[#FF3B30]'}`}>
              {results.avg_return >= 0 ? '+' : ''}{results.avg_return}%
            </p>
          </div>

          {/* Toggle Trades */}
          {results.trades.length > 0 && (
            <>
              <button onClick={() => setShowTrades(!showTrades)}
                className="w-full py-1 text-[10px] font-bold uppercase tracking-wider text-zinc-500 hover:text-white border border-white/5 transition-colors"
                data-testid="backtest-toggle-trades">
                {showTrades ? 'Hide' : 'Show'} Trades ({results.trades.length})
              </button>
              {showTrades && (
                <div className="max-h-40 overflow-y-auto space-y-0.5">
                  {results.trades.map((trade, idx) => (
                    <div key={idx} className="flex items-center justify-between py-1 px-1.5 text-[9px] border border-white/5 font-mono">
                      <div className="flex items-center gap-1">
                        {trade.pnl_pct >= 0 ? <TrendUp size={8} className="text-[#00E676]" weight="bold" /> : <TrendDown size={8} className="text-[#FF3B30]" weight="bold" />}
                        <span className="text-zinc-500">{trade.entry_date}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-zinc-400">{trade.entry_price} &rarr; {trade.exit_price}</span>
                        <span className={trade.pnl_pct >= 0 ? 'text-[#00E676]' : 'text-[#FF3B30]'}>
                          {trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {!results && !loading && (
        <p className="text-[10px] text-zinc-600">Validate strategies against historical data</p>
      )}
    </div>
  );
};

export default BacktestModule;
