import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { MagnifyingGlass, ArrowsClockwise, TrendUp, TrendDown, CurrencyBtc } from '@phosphor-icons/react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtPrice = (v) => {
  if (v == null) return '-';
  if (v >= 1) return `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return `$${v.toFixed(6)}`;
};

const CryptoList = ({ onCryptoSelect, selectedCrypto }) => {
  const [coins, setCoins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQ, setSearchQ] = useState('');

  const fetchCoins = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/crypto/prices`);
      setCoins(data.coins || []);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchCoins();
    const iv = setInterval(fetchCoins, 120000);
    return () => clearInterval(iv);
  }, [fetchCoins]);

  const filtered = searchQ
    ? coins.filter(c => c.symbol?.includes(searchQ.toUpperCase()) || c.name?.toLowerCase().includes(searchQ.toLowerCase()))
    : coins;

  return (
    <div className="flex flex-col h-full" data-testid="crypto-list">
      {/* Search */}
      <div className="p-2 border-b border-white/10">
        <div className="relative">
          <MagnifyingGlass size={11} className="absolute left-2 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input type="text" value={searchQ} onChange={e => setSearchQ(e.target.value)}
            placeholder="Search crypto..."
            className="w-full bg-white/5 border border-white/10 rounded pl-6 pr-2 py-1.5 text-[10px] text-white placeholder:text-zinc-600 focus:outline-none focus:border-white/20"
            data-testid="crypto-list-search" />
        </div>
      </div>

      {/* Coin List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center">
            <ArrowsClockwise size={14} className="animate-spin text-[#00E676] mx-auto" />
          </div>
        ) : (
          filtered.map(coin => {
            const isSelected = selectedCrypto?.id === coin.id;
            const pct = coin.price_change_pct_24h || 0;
            return (
              <button key={coin.id}
                onClick={() => onCryptoSelect({
                  ticker: coin.id,
                  name: coin.name,
                  type: 'CRYPTO',
                  coin_id: coin.id,
                  symbol: coin.symbol,
                  image: coin.image,
                  current_price: coin.current_price,
                  price_change_pct_24h: coin.price_change_pct_24h,
                  market_cap: coin.market_cap,
                  high_24h: coin.high_24h,
                  low_24h: coin.low_24h,
                  ath: coin.ath,
                  ath_change_pct: coin.ath_change_pct,
                  price_change_pct_7d: coin.price_change_pct_7d,
                  total_volume: coin.total_volume,
                  sparkline_7d: coin.sparkline_7d,
                })}
                className={`w-full flex items-center justify-between px-2.5 py-2 text-left border-b border-white/5 transition-colors ${
                  isSelected ? 'bg-white/10' : 'hover:bg-white/5'
                }`}
                data-testid={`crypto-item-${coin.symbol}`}>
                <div className="flex items-center gap-2 min-w-0">
                  {coin.image ? (
                    <img src={coin.image} alt="" className="w-4 h-4 rounded-full shrink-0" />
                  ) : (
                    <CurrencyBtc size={14} className="text-orange-400 shrink-0" />
                  )}
                  <div className="min-w-0">
                    <span className="text-[10px] font-bold text-white block">{coin.symbol}</span>
                    <span className="text-[8px] text-zinc-600 block truncate">{coin.name}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-[10px] font-mono text-white block">{fmtPrice(coin.current_price)}</span>
                  <span className={`text-[9px] font-mono flex items-center justify-end gap-0.5 ${pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {pct >= 0 ? <TrendUp size={8} /> : <TrendDown size={8} />}
                    {Math.abs(pct).toFixed(2)}%
                  </span>
                </div>
              </button>
            );
          })
        )}
        {!loading && filtered.length === 0 && (
          <div className="text-center py-4 px-3">
            <p className="text-[10px] text-zinc-500 mb-2">Coins loading... CoinGecko rate limit</p>
            <button onClick={fetchCoins} className="text-[10px] text-[#00E676] hover:underline font-bold" data-testid="crypto-retry-btn">
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CryptoList;
