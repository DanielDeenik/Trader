import { useState, useEffect } from 'react';
import { api } from '../api';
import { Link } from 'react-router-dom';

export default function ThesisForge() {
  const [theses, setTheses] = useState([]);
  const [expanded, setExpanded] = useState(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      setLoading(true);
      const data = await api.getTheses();
      setTheses(data || []);
    } catch (err) {
      console.error('Failed to load theses:', err);
    } finally {
      setLoading(false);
    }
  }

  function toggleExpand(id) {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpanded(newExpanded);
  }

  const getLifecycleColor = (stage) => {
    if (stage === 'emerging') return 'bg-blue-400/15 text-blue-300 border-blue-400/30';
    if (stage === 'validating') return 'bg-amber-400/15 text-amber-300 border-amber-400/30';
    if (stage === 'confirmed') return 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30';
    if (stage === 'saturated') return 'bg-red-400/15 text-red-300 border-red-400/30';
    return 'bg-white/[0.08] text-white/60';
  };

  const getStatusColor = (status) => {
    if (status === 'active') return 'bg-emerald-400/15 text-emerald-300';
    return 'bg-white/[0.08] text-white/60';
  };

  const getDomainColor = (domain) => {
    if (domain === 'public') return 'text-blue-300 font-mono text-[12px]';
    if (domain === 'private') return 'text-purple-300 font-mono text-[12px]';
    if (domain === 'crypto') return 'text-orange-300 font-mono text-[12px]';
    return 'text-white/60 font-mono text-[12px]';
  };

  if (loading) {
    return <div className="text-white/60 text-[13px] py-8">Loading theses...</div>;
  }

  return (
    <div className="space-y-4">
        {/* Summary */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Total Theses</div>
            <div className="text-white text-[20px] font-mono">{theses.length}</div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Active</div>
            <div className="text-emerald-400 text-[20px] font-mono">
              {theses.filter(t => t.status === 'active').length}
            </div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Avg Kelly</div>
            <div className="text-white text-[20px] font-mono">
              {theses.length > 0
                ? ((theses.reduce((sum, t) => sum + (t.kelly_fraction || 0), 0) / theses.length) * 100).toFixed(1) + '%'
                : '—'}
            </div>
          </div>
        </div>

        {/* Theses Grid */}
        <div className="space-y-4">
          {theses.map((thesis) => {
            const isExpanded = expanded.has(thesis.id);
            return (
              <div
                key={thesis.id}
                className="bg-[#111827]/80 border border-white/[0.06] rounded-xl overflow-hidden hover:border-white/[0.12] transition-colors"
              >
                {/* Header */}
                <div
                  className="px-6 py-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
                  onClick={() => toggleExpand(thesis.id)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      {/* Expand Icon */}
                      <div className={isExpanded ? 'text-emerald-400' : 'text-white/40'}>
                        {isExpanded ? <span className="text-xs">▲</span> : <span className="text-xs">▼</span>}
                      </div>

                      {/* Symbol */}
                      <span className="text-[16px] font-mono font-bold text-white">{thesis.symbol}</span>

                      {/* Lifecycle Stage */}
                      {thesis.lifecycle_stage && (
                        <span
                          className={`text-[11px] font-mono px-3 py-1.5 rounded-full border transition-colors ${getLifecycleColor(thesis.lifecycle_stage)}`}
                        >
                          {thesis.lifecycle_stage}
                        </span>
                      )}

                      {/* Status */}
                      {thesis.status && (
                        <span className={`text-[11px] font-mono px-3 py-1.5 rounded-full ${getStatusColor(thesis.status)}`}>
                          {thesis.status}
                        </span>
                      )}
                    </div>

                    {/* Right Side - ROI Range */}
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-white/50 text-[11px] uppercase tracking-wider mb-1">ROI Range</div>
                        <div className="flex gap-2 items-center">
                          <span className="text-red-400 font-mono text-[13px]">
                            {thesis.roi_bear != null ? `${(thesis.roi_bear * 100).toFixed(0)}%` : '—'}
                          </span>
                          <span className="text-white/40">/</span>
                          <span className="text-white/80 font-mono text-[13px]">
                            {thesis.roi_base != null ? `${(thesis.roi_base * 100).toFixed(0)}%` : '—'}
                          </span>
                          <span className="text-white/40">/</span>
                          <span className="text-emerald-400 font-mono text-[13px]">
                            {thesis.roi_bull != null ? `${(thesis.roi_bull * 100).toFixed(0)}%` : '—'}
                          </span>
                        </div>
                      </div>

                      {/* Kelly Fraction */}
                      {thesis.kelly_fraction != null && (
                        <div className="text-right">
                          <div className="text-white/50 text-[11px] uppercase tracking-wider mb-1">Kelly</div>
                          <div className="text-emerald-400 font-mono text-[13px]">
                            {(thesis.kelly_fraction * 100).toFixed(1)}%
                          </div>
                        </div>
                      )}

                      {/* Domain */}
                      <div className={getDomainColor(thesis.domain)}>{thesis.domain}</div>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="bg-white/[0.02] border-t border-white/[0.06] px-6 py-4 space-y-4">
                    {/* ROI Breakdown */}
                    <div>
                      <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-3">
                        Scenario Analysis
                      </div>
                      <div className="grid grid-cols-3 gap-3">
                        <div className="bg-red-400/10 border border-red-400/20 rounded-lg p-3">
                          <div className="text-white/60 text-[11px] mb-1">Bear Case</div>
                          <div className="text-red-400 font-mono text-[14px] font-bold">
                            {thesis.roi_bear != null ? `${(thesis.roi_bear * 100).toFixed(1)}%` : '—'}
                          </div>
                        </div>
                        <div className="bg-white/[0.08] border border-white/[0.12] rounded-lg p-3">
                          <div className="text-white/60 text-[11px] mb-1">Base Case</div>
                          <div className="text-white font-mono text-[14px] font-bold">
                            {thesis.roi_base != null ? `${(thesis.roi_base * 100).toFixed(1)}%` : '—'}
                          </div>
                        </div>
                        <div className="bg-emerald-400/10 border border-emerald-400/20 rounded-lg p-3">
                          <div className="text-white/60 text-[11px] mb-1">Bull Case</div>
                          <div className="text-emerald-400 font-mono text-[14px] font-bold">
                            {thesis.roi_bull != null ? `${(thesis.roi_bull * 100).toFixed(1)}%` : '—'}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Risk Assessment */}
                    {thesis.risk_assessment && (
                      <div>
                        <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">
                          Risk Assessment
                        </div>
                        <p className="text-[13px] text-white/70 leading-relaxed">{thesis.risk_assessment}</p>
                      </div>
                    )}

                    {/* Vulnerability JSON */}
                    {thesis.vulnerability_json && (
                      <div>
                        <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">
                          Vulnerabilities
                        </div>
                        <pre className="bg-[#0a0f1a] border border-white/[0.06] rounded-lg p-3 text-[11px] font-mono text-white/70 overflow-x-auto max-h-48 overflow-y-auto">
                          {typeof thesis.vulnerability_json === 'string'
                            ? thesis.vulnerability_json
                            : JSON.stringify(thesis.vulnerability_json, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Simulation JSON */}
                    {thesis.simulation_json && (
                      <div>
                        <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">
                          Simulation Data
                        </div>
                        <pre className="bg-[#0a0f1a] border border-white/[0.06] rounded-lg p-3 text-[11px] font-mono text-white/70 overflow-x-auto max-h-48 overflow-y-auto">
                          {typeof thesis.simulation_json === 'string'
                            ? thesis.simulation_json
                            : JSON.stringify(thesis.simulation_json, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Action */}
                    <div className="flex gap-2 pt-2">
                      <Link
                        to={`/gate/review?gate=L3_conviction&symbol=${thesis.symbol}&entity_id=${thesis.id}&entity_type=thesis`}
                        className="px-3 py-2 text-[13px] font-mono rounded-lg bg-emerald-400/15 border border-emerald-400/30 text-emerald-300 hover:bg-emerald-400/20 transition-colors no-underline"
                      >
                        Review → Gate
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {theses.length === 0 && (
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
            <p className="text-white/50 text-[13px]">No theses yet. Run analysis to forge theses from mosaics.</p>
          </div>
        )}
    </div>
  );
}
