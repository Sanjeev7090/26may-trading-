import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { ChartLine, TrendUp, TrendDown, PencilLine, Trash } from '@phosphor-icons/react';

const ChartPanel = ({
  stockData, loading, selectedStock, onPivotSelect, pivotPoint, gannFan,
  semiLogScale, setSemiLogScale, timeframe, onTimeframeChange, isCrypto
}) => {
  const chartContainerRef = useRef();
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const gannLineSeriesRef = useRef([]);
  const [selectMode, setSelectMode] = useState(null);
  const [showGannLines, setShowGannLines] = useState(true);
  const [lineExtension, setLineExtension] = useState(50);
  const [isMovingMode, setIsMovingMode] = useState(false);

  const timeframes = [
    { multiplier: 5, timespan: 'minute', label: '5M' },
    { multiplier: 10, timespan: 'minute', label: '10M' },
    { multiplier: 15, timespan: 'minute', label: '15M' },
    { multiplier: 30, timespan: 'minute', label: '30M' },
    { multiplier: 1, timespan: 'hour', label: '1H' },
    { multiplier: 4, timespan: 'hour', label: '4H' },
    { multiplier: 1, timespan: 'day', label: '1D' },
    { multiplier: 1, timespan: 'week', label: '1W' },
    { multiplier: 1, timespan: 'day', label: '1M', days: 30 },
    { multiplier: 1, timespan: 'day', label: '6M', days: 180 },
    { multiplier: 1, timespan: 'week', label: '1Y', days: 365 },
  ];

  const clearGannLines = () => {
    if (chartRef.current && gannLineSeriesRef.current.length > 0) {
      gannLineSeriesRef.current.forEach(series => {
        try { chartRef.current.removeSeries(series); } catch (e) {}
      });
      gannLineSeriesRef.current = [];
    }
  };

  const drawGannLines = (pivot, extension) => {
    if (!chartRef.current || !pivot || !stockData || !showGannLines) return;
    clearGannLines();
    const bars = stockData.bars;
    const pivotIndex = bars.findIndex(b => Math.abs(b.timestamp - pivot.timestamp) < 86400000);
    if (pivotIndex === -1) return;
    const pivotPrice = pivot.price;
    const isBullish = pivot.type === 'low';
    const priceRange = Math.max(...bars.map(b => b.high)) - Math.min(...bars.map(b => b.low));
    const avgPricePerBar = priceRange / bars.length;
    const angles = [
      { name: '1x1', ratio: 1.0, color: '#3B82F6', width: 3 },
      { name: '2x1', ratio: 2.0, color: '#A855F7', width: 2 },
      { name: '1x2', ratio: 0.5, color: '#FF0055', width: 2 },
      { name: '3x1', ratio: 3.0, color: '#F5A623', width: 1 },
      { name: '1x3', ratio: 0.333, color: '#00E676', width: 1 },
    ];
    const direction = isBullish ? 1 : -1;
    const barsToProject = Math.min(extension, bars.length - pivotIndex);

    angles.forEach(angle => {
      try {
        const lineSeries = chartRef.current.addLineSeries({
          color: angle.color, lineWidth: angle.width, lineStyle: 0,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: angle.name,
        });
        const lineData = [{ time: bars[pivotIndex].timestamp / 1000, value: pivotPrice }];
        for (let i = 1; i <= barsToProject; i++) {
          const barIndex = pivotIndex + i;
          if (barIndex >= bars.length) break;
          lineData.push({
            time: bars[barIndex].timestamp / 1000,
            value: pivotPrice + (i * avgPricePerBar * angle.ratio * direction)
          });
        }
        if (lineData.length >= 2) {
          lineSeries.setData(lineData);
          gannLineSeriesRef.current.push(lineSeries);
        }
      } catch (e) {}
    });
  };

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      layout: { background: { color: '#0A0A0A' }, textColor: '#52525B' },
      grid: { vertLines: { color: 'rgba(255,255,255,0.03)' }, horzLines: { color: 'rgba(255,255,255,0.03)' } },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.08)', mode: semiLogScale ? 2 : 0 },
      timeScale: { borderColor: 'rgba(255,255,255,0.08)', timeVisible: true, rightOffset: 10, barSpacing: 6, minBarSpacing: 0.5 },
      crosshair: { mode: 1 },
      localization: { locale: 'en-US' },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });
    chartRef.current = chart;
    const cs = chart.addCandlestickSeries({
      upColor: '#00E676', downColor: '#FF3B30', borderVisible: false,
      wickUpColor: '#00E676', wickDownColor: '#FF3B30',
    });
    candlestickSeriesRef.current = cs;
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth, height: chartContainerRef.current.clientHeight });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); clearGannLines(); if (chart) chart.remove(); };
  }, []);

  useEffect(() => {
    if (chartRef.current) chartRef.current.applyOptions({ rightPriceScale: { mode: semiLogScale ? 2 : 0 } });
  }, [semiLogScale]);

  useEffect(() => {
    if (!stockData || !candlestickSeriesRef.current) return;
    const chartData = stockData.bars.map(bar => ({ time: bar.timestamp / 1000, open: bar.open, high: bar.high, low: bar.low, close: bar.close }));
    candlestickSeriesRef.current.setData(chartData);
    chartRef.current.timeScale().fitContent();
  }, [stockData]);

  useEffect(() => {
    if (showGannLines && pivotPoint && stockData) {
      setTimeout(() => drawGannLines(pivotPoint, lineExtension), 50);
    } else { clearGannLines(); }
  }, [pivotPoint, showGannLines, stockData, lineExtension]);

  const handleChartClick = (param) => {
    if (!stockData || !param.time) return;
    const clickedTime = param.time * 1000;
    const bar = stockData.bars.find(b => Math.abs(b.timestamp - clickedTime) < 86400000);
    if (!bar) return;
    if (isMovingMode && pivotPoint) {
      const price = pivotPoint.type === 'high' ? bar.high : bar.low;
      onPivotSelect({ price, timestamp: bar.timestamp, type: pivotPoint.type });
      return;
    }
    if (selectMode) {
      const price = selectMode === 'high' ? bar.high : bar.low;
      onPivotSelect({ price, timestamp: bar.timestamp, type: selectMode });
      setSelectMode(null);
      setIsMovingMode(true);
    }
  };

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.subscribeClick(handleChartClick);
    return () => { if (chartRef.current) { try { chartRef.current.unsubscribeClick(handleChartClick); } catch (e) {} } };
  }, [selectMode, stockData, isMovingMode, pivotPoint]);

  const handleDeleteGann = () => { onPivotSelect(null); clearGannLines(); setIsMovingMode(false); };

  return (
    <div className="flex flex-col h-full" data-testid="chart-panel">
      {/* Chart Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-white/10 bg-[#0A0A0A] shrink-0 flex-wrap gap-1">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Timeframes */}
          {timeframes.map((tf) => (
            <button
              key={tf.label}
              onClick={() => onTimeframeChange(tf)}
              className={`px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider transition-all ${
                timeframe.label === tf.label
                  ? 'bg-white text-black'
                  : 'text-zinc-500 hover:text-white'
              }`}
              data-testid={`tf-${tf.label}`}
            >
              {tf.label}
            </button>
          ))}
          <div className="w-px h-4 bg-white/10 mx-1" />
          {/* Gann toggle */}
          <button
            onClick={() => setShowGannLines(!showGannLines)}
            className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 ${
              showGannLines ? 'text-[#3B82F6]' : 'text-zinc-500'
            }`}
            data-testid="gann-toggle"
          >
            <ChartLine size={12} weight="bold" />
            GANN
          </button>
          {/* Log toggle */}
          <button
            onClick={() => setSemiLogScale(!semiLogScale)}
            className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider transition-all ${
              semiLogScale ? 'text-[#F5A623]' : 'text-zinc-500'
            }`}
            data-testid="log-toggle"
          >
            LOG
          </button>
        </div>

        <div className="flex items-center gap-1">
          {!pivotPoint && (
            <>
              <button
                onClick={() => setSelectMode('high')}
                className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 ${
                  selectMode === 'high' ? 'bg-[#FF3B30] text-white' : 'text-zinc-500 hover:text-white'
                }`}
                data-testid="select-high-btn"
              >
                <TrendUp size={12} weight="bold" /> HIGH
              </button>
              <button
                onClick={() => setSelectMode('low')}
                className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1 ${
                  selectMode === 'low' ? 'bg-[#00E676] text-black' : 'text-zinc-500 hover:text-white'
                }`}
                data-testid="select-low-btn"
              >
                <TrendDown size={12} weight="bold" /> LOW
              </button>
            </>
          )}
          {pivotPoint && (
            <>
              <span className="text-[10px] font-mono text-zinc-400">
                Pivot: {pivotPoint.price.toFixed(2)}
              </span>
              <button
                onClick={() => setIsMovingMode(!isMovingMode)}
                className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                  isMovingMode ? 'bg-[#F5A623] text-black' : 'text-zinc-500 hover:text-white'
                }`}
                data-testid="move-pivot-btn"
              >
                {isMovingMode ? 'MOVING' : 'MOVE'}
              </button>
              <button onClick={handleDeleteGann} className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 hover:text-[#FF3B30]" data-testid="clear-gann-btn">
                <Trash size={12} weight="bold" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Extension slider */}
      {pivotPoint && showGannLines && (
        <div className="flex items-center gap-3 px-3 py-1 border-b border-white/10 bg-[#0A0A0A] shrink-0">
          <span className="text-[10px] text-zinc-500 font-mono whitespace-nowrap">Ext: {lineExtension}</span>
          <input
            type="range"
            min={10} max={100} step={5}
            value={lineExtension}
            onChange={(e) => setLineExtension(Number(e.target.value))}
            className="flex-1 h-1 accent-[#3B82F6]"
            data-testid="line-extension-slider"
          />
          <div className="flex items-center gap-2 text-[9px] font-mono">
            <span className="text-[#3B82F6]">1x1</span>
            <span className="text-[#A855F7]">2x1</span>
            <span className="text-[#FF0055]">1x2</span>
            <span className="text-[#F5A623]">3x1</span>
            <span className="text-[#00E676]">1x3</span>
          </div>
        </div>
      )}

      {/* Chart area */}
      <div className="flex-1 relative" ref={chartContainerRef}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0A0A0A]/80 z-10">
            <p className="text-xs font-mono text-zinc-400 animate-pulse">Loading chart data...</p>
          </div>
        )}
        {!loading && !stockData && (
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <ChartLine size={48} className="text-zinc-700 mb-3" />
            <p className="text-sm text-zinc-500">Select a stock or crypto to view chart</p>
            <p className="text-[10px] text-zinc-600 mt-1 font-mono">Scroll to zoom / Drag to pan</p>
          </div>
        )}
      </div>

      {/* Status bar */}
      {selectMode && (
        <div className="px-3 py-1 border-t border-white/10 bg-[#141414] text-[10px] font-mono text-[#F5A623] shrink-0">
          Click on chart to select {selectMode === 'high' ? 'swing high' : 'swing low'} point
        </div>
      )}
      {isMovingMode && pivotPoint && (
        <div className="px-3 py-1 border-t border-white/10 bg-[#141414] text-[10px] font-mono text-[#F5A623] shrink-0">
          Click anywhere on chart to move pivot
        </div>
      )}
    </div>
  );
};

export default ChartPanel;
