export default function OrderBook({ book }) {
  if (!book) {
    return (
      <div className="qsc-card p-5" data-testid="orderbook-card">
        <div className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-400 mb-2">Order Book</div>
        <div className="text-neutral-500 font-mono text-xs">Loading...</div>
      </div>
    );
  }
  const maxBidQty = Math.max(...book.bids.map((b) => b.qty), 0.0001);
  const maxAskQty = Math.max(...book.asks.map((a) => a.qty), 0.0001);
  return (
    <div className="qsc-card" data-testid="orderbook-card">
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-400">Order Book / L2</span>
        <span className="text-[10px] font-mono text-neutral-500">{book.symbol}</span>
      </div>
      <div className="px-4 py-2 grid grid-cols-3 text-[10px] font-mono uppercase text-neutral-600 tracking-widest">
        <div>Price</div><div className="text-right">Qty</div><div className="text-right">Depth</div>
      </div>
      <div className="px-2">
        {book.asks.slice().reverse().map((a, i) => (
          <Row key={`a${i}`} side="ask" price={a.price} qty={a.qty} pct={a.qty / maxAskQty} />
        ))}
      </div>
      <div className="px-4 py-2 border-y border-white/10 font-mono text-xs flex items-center justify-between bg-white/[0.02]">
        <span className="text-neutral-500 uppercase tracking-widest text-[10px]">Mid</span>
        <span className="text-white" data-testid="ob-mid-price">{book.mid?.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
      </div>
      <div className="px-2 pb-3">
        {book.bids.map((b, i) => (
          <Row key={`b${i}`} side="bid" price={b.price} qty={b.qty} pct={b.qty / maxBidQty} />
        ))}
      </div>
    </div>
  );
}

function Row({ side, price, qty, pct }) {
  const color = side === "bid" ? "#3366FF" : "#FF3333";
  return (
    <div className="relative grid grid-cols-3 items-center py-1 px-2 font-mono text-[11px]">
      <div className="absolute inset-y-0 right-0" style={{ width: `${Math.min(pct * 100, 100)}%`, background: `${color}1A` }} />
      <div className="relative" style={{ color }}>{price.toFixed(2)}</div>
      <div className="relative text-right text-neutral-300">{qty.toFixed(3)}</div>
      <div className="relative text-right text-neutral-500">{(qty * price).toFixed(0)}</div>
    </div>
  );
}
