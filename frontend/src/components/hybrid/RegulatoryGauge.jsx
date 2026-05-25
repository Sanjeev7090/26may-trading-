import { ShieldStarIcon as ShieldStar } from "@phosphor-icons/react";

export default function RegulatoryGauge({ data }) {
  if (!data) {
    return <div className="qsc-card p-5"><div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-400">Regulatory Watchdog</div><div className="text-neutral-500 font-mono text-xs mt-2">Loading...</div></div>;
  }
  const angle = ((data.score + 1) / 2) * 180 - 90; // -90..+90
  const color = data.score > 0.1 ? "#3366FF" : data.score < -0.1 ? "#FF3333" : "#FFCC00";
  return (
    <div className="qsc-card" data-testid="regulatory-gauge">
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <ShieldStar size={14} className="text-neutral-400" />
        <span className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-400">Regulatory Watchdog</span>
      </div>
      <div className="p-4">
        <div className="relative w-full h-24 flex items-end justify-center">
          <svg viewBox="0 0 200 110" className="w-full h-full">
            <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2" />
            <path d="M 10 100 A 90 90 0 0 1 100 10" fill="none" stroke="#FF3333" strokeWidth="2" opacity="0.4"/>
            <path d="M 100 10 A 90 90 0 0 1 190 100" fill="none" stroke="#3366FF" strokeWidth="2" opacity="0.4"/>
            <line
              x1="100" y1="100"
              x2={100 + 80 * Math.cos((angle - 90) * Math.PI/180)}
              y2={100 + 80 * Math.sin((angle - 90) * Math.PI/180)}
              stroke={color} strokeWidth="2"
            />
            <circle cx="100" cy="100" r="3" fill={color} />
          </svg>
        </div>
        <div className="text-center mt-2">
          <div className="font-display text-2xl tracking-tighter" style={{ color }} data-testid="reg-label">{data.label}</div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-neutral-500 mt-1">
            Score {data.score} / Mult {data.aggressiveness_multiplier}x
          </div>
        </div>
        <div className="border-t border-white/10 mt-3 pt-3 space-y-2">
          {data.headlines.slice(0, 3).map((h, i) => (
            <div key={i} className="text-[10px] font-mono">
              <span className="text-neutral-500 uppercase tracking-widest mr-2">{h.src}</span>
              <span className="text-neutral-300">{h.headline}</span>
              <span className="ml-2" style={{ color: h.weight >= 0 ? "#3366FF" : "#FF3333" }}>
                {h.weight >= 0 ? "+" : ""}{h.weight}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
