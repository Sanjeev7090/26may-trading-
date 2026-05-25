import { Fragment, useMemo, useState } from "react";

function colorFor(v) {
  // v in [-1, 1] → red (loss) through dark → blue (profit)
  const t = Math.max(-1, Math.min(1, v));
  if (t >= 0) {
    const a = t; // 0..1
    return `rgba(51,102,255,${0.15 + a * 0.75})`;
  }
  const a = -t;
  return `rgba(255,51,51,${0.15 + a * 0.75})`;
}

export default function CorrelationHeatmap({ data }) {
  const { symbols = [], cells = [] } = data || {};
  const [hover, setHover] = useState(null);

  const matrix = useMemo(() => {
    const m = {};
    for (const s of symbols) m[s] = {};
    for (const c of cells) {
      m[c.a][c.b] = c;
      m[c.b][c.a] = c;
    }
    return m;
  }, [symbols, cells]);

  return (
    <div className="qsc-card" data-testid="correlation-heatmap">
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-400">Correlation Matrix • Classical × Quantum Kernel</span>
        <div className="flex items-center gap-3 text-[10px] font-mono uppercase tracking-widest text-neutral-500">
          <span>−1 <span className="inline-block w-4 h-2 align-middle" style={{ background: "rgba(255,51,51,0.9)" }} /></span>
          <span><span className="inline-block w-4 h-2 align-middle" style={{ background: "rgba(51,102,255,0.9)" }} /> +1</span>
        </div>
      </div>
      <div className="p-4 overflow-x-auto">
        <div
          className="grid gap-px min-w-[640px]"
          style={{ gridTemplateColumns: `80px repeat(${symbols.length}, minmax(48px, 1fr))` }}
        >
          <div />
          {symbols.map((s) => (
            <div key={`h-${s}`} className="text-[10px] font-mono text-neutral-500 text-center px-1 py-1 truncate">{s.replace("USDT","")}</div>
          ))}
          {symbols.map((row) => (
            <Fragment key={`row-${row}`}>
              <div className="text-[10px] font-mono text-neutral-500 px-2 py-1 truncate">{row.replace("USDT","")}</div>
              {symbols.map((col) => {
                const c = matrix[row]?.[col];
                const v = c ? c.fused : 0;
                return (
                  <div
                    key={`${row}-${col}`}
                    className="heat-cell"
                    style={{ background: colorFor(v) }}
                    onMouseEnter={() => setHover({ row, col, c })}
                    onMouseLeave={() => setHover(null)}
                    data-testid={`heat-${row}-${col}`}
                  >
                    {v.toFixed(2)}
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>
        {hover?.c && (
          <div className="mt-4 font-mono text-[11px] text-neutral-300 border-t border-white/10 pt-3 flex items-center gap-6">
            <span><span className="text-neutral-500">PAIR</span> {hover.row} ↔ {hover.col}</span>
            <span><span className="text-neutral-500">CLASSICAL</span> {hover.c.classical}</span>
            <span><span className="text-neutral-500">QUANTUM</span> {hover.c.quantum}</span>
            <span><span className="text-neutral-500">FUSED</span> <span className="text-white">{hover.c.fused}</span></span>
          </div>
        )}
      </div>
    </div>
  );
}
