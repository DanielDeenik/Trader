import { useState, useEffect } from 'react';
import { api } from '../api';

export default function Positions() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('open');

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      setLoading(true);
      const data = await api.getPositions();
      setPositions(data || []);
    } catch (err) {
      console.error('Failed to load positions:', err);
    } finally {
      setLoading(false);
    }
  }

  const filtered = filterStatus === 'all'
    ? positions
    : positions.filter(p => (filterStatus === 'open' ? p.status === 'open' : p.status !== 'open'));

  const totalAlloc = positions.reduce((sum, p) => sum + (p.allocation_pct || 0), 0);
  const totalPnl = positions.reduce((sum, p) => sum + (p.pnl || 0), 0);
  const openCount = positions.filter(p => p.status === 'open').length;

  const getDirectionColor = (direction) => {
    if (direction === 'long') return 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30';
    if (direction === 'short') return 'bg-red-400/15 text-red-300 border-red-400/30';
    return 'bg-white/[0.08] text-white/60';
  };

  const getConvictionColor = (conviction) => {
    if (conviction === 'high') return 'bg-emerald-400/15 text-emerald-300';
    if (conviction === 'medium') return 'bg-amber-400/15 text-amber-300';
    if (conviction === 'low') return 'bg-red-400/15 text-red-300';
    return 'bg-white/[0.08] text-white/60';
  };

  const getStatusColor = (status) => {
    if (status === 'open') return 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30';
    return 'bg-white/[0.08] text-white/60';
  };

  if (loading) {
    return <div className="text-white/60 text-[13px] py-8">Loading positions...</div>;
  }

  return (
    <div className="space-y-4">
        {/* Summary */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Total Positions</div>
            <div className="text-white text-[20px] font-mono">{positions.length}</div>
            <div className="text-white/50 text-[11px] mt-2">
              {openCount} open
            </div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Total Allocation</div>
            <div className="text-white text-[20px] font-mono">{totalAlloc.toFixed(1)}%</div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Total P&L</div>
            <div className={`text-[20px] font-mono ${totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              ${totalPnl.toFixed(2)}
            </div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Avg P&L %</div>
            <div className={`text-[20px] font-mono ${
              positions.length > 0 && positions.reduce((sum, p) => sum + (p.pnl_pct || 0), 0) / positions.length >= 0
                ? 'text-emerald-400'
                : 'text-red-400'
            }`}>
              {positions.length > 0 ? ((positions.reduce((sum, p) => sum + (p.pnl_pct || 0), 0) / positions.length).toFixed(1)) + '%' : '—'}
            </div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2 mb-6">
          {['open', 'closed', 'all'].map(status => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-4 py-2 text-[13px] font-mono rounded-lg transition-colors ${
                filterStatus === status
                  ? 'bg-emerald-400/15 border border-emerald-400/30 text-emerald-300'
                  : 'bg-white/[0.08] border border-white/[0.12] text-white/60 hover:bg-white/[0.12]'
              }`}
            >
              {status === 'open' ? 'Open' : status === 'closed' ? 'Closed' : 'All'}
            </button>
          ))}
        </div>

        {/* Positions Table */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl overflow-hidden">
          <div className="bg-white/[0.03] border-b border-white/[0.06] px-6 py-3">
            <div className="grid grid-cols-12 gap-4 text-white/50 text-[12px] font-mono uppercase tracking-wider">
              <div className="col-span-2">Symbol</div>
              <div className="col-span-1">Dir</div>
              <div className="col-span-1.5 text-right">Alloc%</div>
              <div className="col-span-1.5 text-right">Entry</div>
              <div className="col-span-1.5">Conv</div>
              <div className="col-span-1.5">Status</div>
              <div className="col-span-2 text-right">P&L</div>
            </div>
          </div>

          <div>
            {filtered.map((position) => {
              const pnlPercent = position.pnl_pct || 0;
              const isPnlPositive = pnlPercent >= 0;

              return (
                <div
                  key={position.id}
                  className="border-b border-white/[0.06] hover:bg-white/[0.04] transition-colors"
                >
                  <div className="px-6 py-4 grid grid-cols-12 gap-4 items-center">
                    {/* Symbol */}
                    <div className="col-span-2">
                      <span className="text-white font-mono text-[13px] font-semibold">{position.symbol}</span>
                    </div>

                    {/* Direction */}
                    <div className="col-span-1">
                      <span
                        className={`text-[11px] font-mono px-2 py-1 rounded-full border ${getDirectionColor(position.direction)}`}
                      >
                        {position.direction === 'long' ? 'L' : 'S'}
                      </span>
                    </div>

                    {/* Allocation */}
                    <div className="col-span-1.5 text-right">
                      <span className="text-white/70 font-mono text-[12px]">{position.allocation_pct.toFixed(1)}%</span>
                    </div>

                    {/* Entry Price */}
                    <div className="col-span-1.5 text-right">
                      <span className="text-white/70 font-mono text-[12px]">
                        ${parseFloat(position.entry_price).toFixed(2)}
                      </span>
                    </div>

                    {/* Conviction */}
                    <div className="col-span-1.5">
                      <span
                        className={`text-[11px] font-mono px-2 py-1 rounded-full ${getConvictionColor(position.conviction)}`}
                      >
                        {position.conviction}
                      </span>
                    </div>

                    {/* Status */}
                    <div className="col-span-1.5">
                      <span
                        className={`text-[11px] font-mono px-2 py-1 rounded-full border ${getStatusColor(position.status)}`}
                      >
                        {position.status}
                      </span>
                    </div>

                    {/* P&L */}
                    <div className="col-span-2 text-right">
                      {position.status === 'open' ? (
                        <span className="text-white/60 text-[12px]">—</span>
                      ) : (
                        <div>
                          <div className={`font-mono text-[13px] ${isPnlPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                            {isPnlPositive ? '+' : ''}{pnlPercent.toFixed(1)}%
                          </div>
                          <div className={`font-mono text-[11px] ${isPnlPositive ? 'text-emerald-400/60' : 'text-red-400/60'}`}>
                            ${(position.pnl || 0).toFixed(2)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {filtered.length === 0 && (
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
            <p className="text-white/50 text-[13px]">
              No {filterStatus === 'open' ? 'open' : filterStatus === 'closed' ? 'closed' : ''} positions yet
            </p>
          </div>
        )}
    </div>
  );
}
