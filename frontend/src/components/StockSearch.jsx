import React, { useState } from 'react';
import axios from 'axios';
import { MagnifyingGlass } from '@phosphor-icons/react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const StockSearch = ({ onStockSelect, selectedStock }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = async (searchQuery) => {
    if (searchQuery.length < 1) { setResults([]); return; }
    setSearching(true);
    try {
      const response = await axios.get(`${API}/stock/search`, { params: { q: searchQuery } });
      setResults(response.data.results || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value.toUpperCase();
    setQuery(value);
    if (value.length >= 1) {
      setTimeout(() => handleSearch(value), 600);
    } else {
      setResults([]);
    }
  };

  const selectStock = (stock) => {
    onStockSelect(stock);
    setQuery('');
    setResults([]);
  };

  return (
    <div data-testid="stock-search">
      <div className="relative">
        <MagnifyingGlass className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" size={14} weight="bold" />
        <input
          type="text"
          value={query}
          onChange={handleInputChange}
          placeholder="Search stocks..."
          className="w-full bg-black border border-white/10 focus:border-white/40 pl-8 pr-3 py-2 text-xs font-mono text-white placeholder:text-zinc-600 outline-none transition-colors"
          data-testid="stock-search-input"
        />
      </div>

      {searching && <p className="text-[10px] text-zinc-500 mt-2 font-mono animate-pulse">Searching...</p>}

      {results.length > 0 && (
        <div className="mt-1 max-h-48 overflow-y-auto" data-testid="search-results">
          {results.map((stock, idx) => (
            <button
              key={idx}
              onClick={() => selectStock(stock)}
              className="w-full text-left px-3 py-2 hover:bg-white/5 border-b border-white/5 transition-colors flex items-center justify-between"
              data-testid={`search-result-${idx}`}
            >
              <span className="text-xs font-mono font-bold text-white">{stock.ticker}</span>
              <span className="text-[10px] text-zinc-500 truncate ml-2">{stock.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default StockSearch;
