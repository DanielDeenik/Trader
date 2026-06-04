import { useState, useEffect } from 'react';
import { useApi } from '../hooks';
import { api } from '../api';
import { Link } from 'react-router-dom';

const SOURCE_COLORS = {
  yfinance: 'bg-blue-400/15 text-blue-300',
  reddit: 'bg-orange-400/15 text-orange-300',
  sec_edgar: 'bg-amber-400/15 text-amber-300',
  google_trends: 'bg-emerald-400/15 text-emerald-300',
  github: 'bg-purple-400/15 text-purple-300',
  coingecko: 'bg-cyan-400/15 text-cyan-300',
  defillama: 'bg-pink-400/15 text-pink-300',
};

export default function SignalRadar() {
  const [grouped, setGrouped] = useState([]);
  const [detailed, setDetailed] = useState({});
  const [expanded, setExpanded] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await api.getSignalsGrouped();
        setGrouped(data || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function toggleExpand(symbol) {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(symbol)) {
      newExpanded.delete(symbol);
      setExpanded(newExpanded);
    } else {
      newExpanded.add(symbol);
      setExpanded(newExpanded);
      if (!detailed[symbol]) {
        try {
          const signals = await api.getSignals({ symbol });
          setDetailed(prev => ({
            ...prev,
            [symbol]: signals || []
          }));
        } catch (err) {
          console.error(`Failed to load signals for ${symbol}:`, err);
        }
      }
    }
  }

  const getDirectionColor = (direction) => {
    if (direction === 'bullish') return 'bg-emerald-400/20 text-emerald-300';
    if (direction === 'bearish') return 'bg-red-400/20 text-red-300';
    return 'bg-white/[0.08] text-white/60';
  };

  const getDirectionIcon = (direction) => {
    if (direction === 'bullish') return <span className="text-emerald-400">↑</span>;
    if (direction === 'bearish') return <span className="text-red-400">↓</span>;
    return <span className="text-gray-400">—</span>;
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  if (loading) {
    return <div className="text-white/60 text-[13px] py-8">Loading signals...</div>;
  }

  if (error) {
    return <div className="text-red-400 text-[13px] py-8">Error: {error}</div>;
  }

  return (
    <div className="space-y-4">
        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Total Symbols</div>
            <div className="text-white text-[20px] font-mono">{grouped.length}</div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Total Signals</div>
            <div className="text-white text-[20px] font-mono">{grouped.reduce((sum, g) => sum + g.total, 0)}</div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Bullish</div>
            <div className="text-emerald-400 text-[20px] font-mono">{grouped.reduce((sum, g) => sum + g.bullish, 0)}</div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Bearish</div>
            <div className="text-red-400 text-[20px] font-mono">{grouped.reduce((sum, g) => sum + g.bearish, 0)}</div>
          </div>
        </div>

        {/* Signals Table */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl overflow-hidden">
          <div className="bg-white/[0.03] border-b border-white/[0.06] px-6 py-3">
            <div className="grid grid-cols-12 gap-4 text-white/50 text-[12px] font-mono uppercase tracking-wider">
              <div className="col-span-2">Symbol</div>
              <div className="col-span-1 text-right">Total</div>
              <div className="col-span-2">Direction</div>
              <div className="col-span-2">Sources</div>
              <div className="col-span-3">Latest</div>
              <div className="col-span-2 text-right">Action</div>
            </div>
          </div>

          <div>
            {grouped.map((item, idx) => {
              const isExpanded = expanded.has(item.symbol);
              const directionPercent = item.total > 0 ? {
                bullish: (item.bullish / item.total) * 100,
                bearish: (item.bearish / item.total) * 100,
                neutral: (item.neutral / item.total) * 100
              } : { bullish: 0, bearish: 0, neutral: 0 };

              return (
                <div key={item.symbol}>
                  {/* Main Row */}
                  <div
                    className="border-b border-white/[0.06] hover:bg-white/[0.04] cursor-pointer transition-colors"
                    onClick={() => toggleExpand(item.symbol)}
                  >
                    <div className="px-6 py-4 grid grid-cols-12 gap-4 items-center">
                      {/* Symbol */}
                      <div className="col-span-2 flex items-center gap-2">
                        <div className={isExpanded ? 'text-emerald-400' : 'text-white/40'}>
                          {isExpanded ? <span className="text-xs">▲</span> : <span className="text-xs">▼</span>}
                        </div>
                        <span className="text-white font-mono text-[13px] font-semibold">{item.symbol}</span>
                      </div>

                      {/* Total Count */}
                      <div className="col-span-1 text-right">
                        <span className="text-white/70 font-mono text-[13px]">{item.total}</span>
                      </div>

                      {/* Direction Bar */}
                      <div className="col-span-2">
                        <div className="flex gap-1 h-5 rounded-full overflow-hidden bg-white/[0.05]">
                          {item.bullish > 0 && (
                            <div
                              className="bg-emerald-400 transition-all"
                              style={{ width: `${directionPercent.bullish}%` }}
                              title={`${item.bullish} bullish`}
                            />
                          )}
                          {item.bearish > 0 && (
                            <div
                              className="bg-red-400 transition-all"
                              style={{ width: `${directionPercent.bearish}%` }}
                              title={`${item.bearish} bearish`}
                            />
                          )}
                          {item.neutral > 0 && (
                            <div
                              className="bg-white/30 transition-all"
                              style={{ width: `${directionPercent.neutral}%` }}
                              title={`${item.neutral} neutral`}
                            />
                          )}
                        </div>
                      </div>

                      {/* Source Tags */}
                      <div className="col-span-2 flex flex-wrap gap-1">
                        {(() => {
                          const srcArr = Array.isArray(item.sources) ? item.sources : (typeof item.sources === 'string' && item.sources ? item.sources.split(',') : []);
                          return <>
                            {srcArr.slice(0, 2).map((source, i) => (
                              <span key={i} className={`text-[11px] px-2 py-1 rounded-full ${SOURCE_COLORS[source.trim()] || 'bg-white/[0.08] text-white/70'}`}>
                                {source.trim()}
                              </span>
                            ))}
                            {srcArr.length > 2 && (
                              <span className="bg-white/[0.06] text-white/50 text-[11px] px-2 py-1 rounded-full">
                                +{srcArr.length - 2}
                              </span>
                            )}
                          </>;
                        })()}
                      </div>

                      {/* Latest Signal Time */}
                      <div className="col-span-3">
                        <span className="text-white/60 text-[13px]">{formatTime(item.latest_signal)}</span>
                      </div>

                      {/* Action Links */}
                      <div className="col-span-2 flex justify-end gap-2">
                        <Link
                          to={`/gate/review?gate=L1_triage&symbol=${item.symbol}&entity_type=signal_cluster`}
                          className="text-emerald-400 hover:text-emerald-300 text-[13px] font-mono transition-colors"
                        >
                          Review →
                        </Link>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && detailed[item.symbol] && (
                    <div className="bg-white/[0.02] border-b border-white/[0.06]">
                      <div className="px-6 py-4">
                        <div className="text-white/70 text-[11px] uppercase tracking-wider mb-4 font-mono">Signal Details</div>
                        <div className="space-y-3">
                          {detailed[item.symbol].slice(0, 10).map((signal) => (
                            <div
                              key={signal.id}
                              className="bg-[#111827]/60 border border-white/[0.04] rounded-lg p-3 text-[12px]"
                            >
                              <div className="flex justify-between items-start mb-2">
                                <div className="flex gap-2 items-center">
                                  <span
                                    className={`flex items-center gap-1 px-2 py-1 rounded-full text-[11px] ${getDirectionColor(signal.direction)}`}
                                  >
                                    {getDirectionIcon(signal.direction)}
                                    {signal.direction}
                                  </span>
                                  <span className={`text-[11px] px-2 py-1 rounded-full ${SOURCE_COLORS[signal.source] || 'bg-white/[0.08] text-white/70'}`}>
                                    {signal.source}
                                  </span>
                                </div>
                                <span className="text-white/40 font-mono text-[11px]">{formatTime(signal.timestamp)}</span>
                              </div>
                              <div className="flex flex-wrap gap-3 text-white/60">
                                <span>Type: <span className="text-white/80 font-mono">{signal.signal_type}</span></span>
                                <span>Strength: <span className="text-white/80 font-mono">{Math.round(signal.strength * 100)}%</span></span>
                                <span>Confidence: <span className="text-white/80 font-mono">{Math.round(signal.confidence * 100)}%</span></span>
                              </div>
                            </div>
                          ))}
                          {detailed[item.symbol].length > 10 && (
                            <div className="text-white/40 text-[11px] text-center py-2">
                              ... and {detailed[item.symbol].length - 10} more
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {grouped.length === 0 && (
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
            <p className="text-white/50 text-[13px]">No signals collected yet. Collectors are running...</p>
          </div>
        )}
    </div>
  );
}
