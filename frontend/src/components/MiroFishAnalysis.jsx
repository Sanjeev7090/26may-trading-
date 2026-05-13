import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { FishSimple, TrendUp, TrendDown, Minus, UserCircle, ShieldCheck, Eye, ChartLine, Newspaper } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const agentIcons = {
  momentum: ChartLine,
  news_sentiment: Newspaper,
  contrarian: Eye,
  risk_mgmt: ShieldCheck,
  pattern: ChartLine,
};

const agentColors = {
  momentum: 'text-orange-400',
  news_sentiment: 'text-sky-400',
  contrarian: 'text-purple-400',
  risk_mgmt: 'text-yellow-400',
  pattern: 'text-teal-400',
};

const VerdictBadge = ({ verdict }) => {
  const cls = verdict === 'BUY'
    ? 'bg-emerald-500/20 text-emerald-400'
    : verdict === 'SELL'
    ? 'bg-red-500/20 text-red-400'
    : 'bg-zinc-500/20 text-zinc-400';
  return (
    <span className={`px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider rounded ${cls}`} data-testid={`mirofish-verdict-${verdict.toLowerCase()}`}>
      {verdict}
    </span>
  );
};

const AgentCard = ({ agent }) => {
  const IconComp = agentIcons[agent.role] || UserCircle;
  const colorCls = agentColors[agent.role] || 'text-zinc-400';
  const bgVerdict = agent.verdict === 'BUY'
    ? 'border-emerald-500/15 bg-emerald-500/5'
    : agent.verdict === 'SELL'
    ? 'border-red-500/15 bg-red-500/5'
    : 'border-zinc-500/15 bg-zinc-500/5';

  return (
    <div className={`border rounded p-2 ${bgVerdict}`} data-testid={`mirofish-agent-${agent.role}`}>
      <div className="flex items-center gap-1.5 mb-1">
        <IconComp size={11} weight="fill" className={colorCls} />
        <span className="text-[9px] font-bold text-zinc-300 flex-1">{agent.agent_name}</span>
        <VerdictBadge verdict={agent.verdict} />
        <span className="text-[8px] font-mono text-zinc-500">{agent.confidence}%</span>
      </div>
      <p className="text-[9px] text-zinc-500 leading-relaxed">{agent.reasoning}</p>
    </div>
  );
};

const MiroFishAnalysis = ({ stockData, selectedStock }) => {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runAnalysis = async () => {
    if (!stockData?.bars?.length) { toast.error('No data loaded'); return; }
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/mirofish/analyze`, {
        ticker: selectedStock?.ticker || selectedStock?.coin_id || 'UNKNOWN',
        bars: stockData.bars.slice(-60),
        timeframe: '1D',
      });
      setResult(data);
      if (data.signal_type !== 'WAIT') {
        toast.success(`MiroFish ${data.signal_type} | Consensus: ${data.swarm_consensus} (${data.consensus_score}%)`);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'MiroFish Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const isBuy = result?.signal_type === 'BUY';
  const isSell = result?.signal_type === 'SELL';
  const hasSignal = isBuy || isSell;

  const consensusColor = result?.swarm_consensus === 'BULLISH'
    ? 'text-emerald-400'
    : result?.swarm_consensus === 'BEARISH'
    ? 'text-red-400'
    : 'text-zinc-400';

  const sentimentColor = result?.news_sentiment === 'POSITIVE'
    ? 'text-emerald-400'
    : result?.news_sentiment === 'NEGATIVE'
    ? 'text-red-400'
    : 'text-zinc-400';

  return (
    <div className="p-3" data-testid="mirofish-analysis">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FishSimple size={14} className="text-[#00BCD4]" weight="fill" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400">MiroFish</span>
          <span className="text-[8px] text-zinc-600 font-mono">Swarm AI</span>
        </div>
        <button onClick={runAnalysis} disabled={loading || !stockData}
          className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider bg-[#00BCD4]/20 text-[#00BCD4] rounded hover:bg-[#00BCD4]/30 disabled:opacity-40 transition-colors"
          data-testid="mirofish-run-btn">
          {loading ? 'Swarming...' : 'RUN SWARM'}
        </button>
      </div>

      {!result && !loading && (
        <div className="text-center py-3">
          <p className="text-[10px] text-zinc-500">Swarm Intelligence Engine — 5-Agent Consensus</p>
          <p className="text-[9px] text-zinc-600 mt-1">Momentum + News + Contrarian + Risk + Pattern Agents</p>
        </div>
      )}

      {loading && (
        <div className="py-4 text-center animate-pulse space-y-1">
          <FishSimple size={20} className="text-[#00BCD4] mx-auto animate-bounce" weight="fill" />
          <p className="text-[10px] text-[#00BCD4] font-mono">Agents forming consensus...</p>
        </div>
      )}

      {result && !loading && (
        <div className="space-y-2 animate-fade-in">
          {/* Consensus Banner */}
          <div className={`p-2 rounded border ${
            isBuy ? 'bg-emerald-500/10 border-emerald-500/30' : isSell ? 'bg-red-500/10 border-red-500/30' : 'bg-zinc-800/50 border-zinc-700'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isBuy ? <TrendUp size={16} className="text-emerald-400" weight="bold" /> :
                 isSell ? <TrendDown size={16} className="text-red-400" weight="bold" /> :
                 <Minus size={16} className="text-zinc-400" weight="bold" />}
                <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded ${
                  isBuy ? 'bg-emerald-500 text-black' : isSell ? 'bg-red-500 text-white' : 'bg-zinc-600 text-white'
                }`} data-testid="mirofish-signal">{result.signal_type}</span>
                <span className={`text-[10px] font-bold uppercase ${consensusColor}`} data-testid="mirofish-consensus">
                  {result.swarm_consensus}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-mono text-zinc-400">Score: </span>
                <span className={`text-[11px] font-bold font-mono ${consensusColor}`} data-testid="mirofish-score">
                  {result.consensus_score}%
                </span>
              </div>
            </div>
          </div>

          {/* News Sentiment */}
          <div className="flex items-center gap-2 px-1">
            <Newspaper size={11} className="text-sky-400" />
            <span className="text-[9px] text-zinc-500 uppercase tracking-wider">News:</span>
            <span className={`text-[9px] font-bold uppercase ${sentimentColor}`} data-testid="mirofish-news-sentiment">{result.news_sentiment}</span>
            <span className="text-[9px] text-zinc-600 flex-1 truncate">{result.news_summary}</span>
          </div>

          {/* Entry / SL / Targets */}
          {hasSignal && (
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <div>
                <p className="text-zinc-500 text-[9px]">Entry</p>
                <p className="font-mono font-bold text-white" data-testid="mirofish-entry">{result.entry_price}</p>
              </div>
              <div>
                <p className="text-zinc-500 text-[9px]">SL</p>
                <p className="font-mono font-bold text-red-400" data-testid="mirofish-sl">{result.stop_loss}</p>
              </div>
              <div>
                <p className="text-zinc-500 text-[9px]">Targets</p>
                {result.targets?.map((t, i) => (
                  <p key={i} className="font-mono text-emerald-400 text-[9px]">T{i + 1}: {t}</p>
                ))}
              </div>
            </div>
          )}

          {result.risk_reward && hasSignal && (
            <div className="flex items-center gap-2 px-1">
              <span className="text-[9px] text-zinc-500">R:R</span>
              <span className="text-[9px] font-mono font-bold text-[#00BCD4]">{result.risk_reward}</span>
            </div>
          )}

          {/* Agent Verdicts */}
          <div className="space-y-1.5">
            <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 px-1">Agent Verdicts</p>
            {result.agents?.map((agent, i) => (
              <AgentCard key={i} agent={agent} />
            ))}
          </div>

          {/* Recommendation */}
          <div className="p-2 bg-[#00BCD4]/5 border border-[#00BCD4]/20 rounded">
            <p className="text-[10px] text-zinc-300 leading-relaxed" data-testid="mirofish-recommendation">{result.recommendation}</p>
          </div>

          <p className="text-[9px] text-zinc-600 font-mono">MiroFish Swarm | GPT-4o | {new Date().toLocaleTimeString('en-US')}</p>
        </div>
      )}
    </div>
  );
};

export default MiroFishAnalysis;
