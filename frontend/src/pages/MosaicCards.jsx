import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

export default function MosaicCards() {
  const [mosaics, setMosaics] = useState([]);
  const [expanded, setExpanded] = useState(new Set());
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      setLoading(true);
      const data = await api.getMosaics();
      setMosaics(data || []);
    } catch (err) {
      setMsg({ type: 'error', text: `Failed to load: ${err.message}` });
    } finally {
      setLoading(false);
    }
  }

  async function handleRunAnalysis() {
    setMsg(null);
    try {
      await api.createTask({ task_type: 'analyze' });
      setMsg({ type: 'success', text: 'Analysis started — mosaics will update when complete' });
      setTimeout(() => setMsg(null), 5000);
    } catch (err) {
      setMsg({ type: 'error', text: `Failed: ${err.message}` });
      setTimeout(() => setMsg(null), 5000);
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

  const getActionColor = (action) => {
    if (action === 'build_thesis') return 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30';
    if (action === 'investigate') return 'bg-amber-400/15 text-amber-300 border-amber-400/30';
    return 'bg-white/[0.08] text-white/60 border-white/[0.06]';
  };

  const getDomainColor = (domain) => {
    if (domain === 'public') return 'bg-blue-400/15 text-blue-300';
    if (domain === 'private') return 'bg-purple-400/15 text-purple-300';
    if (domain === 'crypto') return 'bg-orange-400/15 text-orange-300';
    return 'bg-white/[0.08] text-white/70';
  };

  if (loading) {
    return <div className="text-white/60 text-[13px] py-8">Loading mosaics...</div>;
  }

  return (
    <div className="space-y-4">
        {/* Controls */}
        <div className="flex gap-3">
          <button
            onClick={load}
            className="px-4 py-2 bg-white/[0.08] border border-white/[0.12] text-white/80 text-[13px] font-mono rounded-lg hover:bg-white/[0.12] transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={handleRunAnalysis}
            className="px-4 py-2 bg-amber-400/15 border border-amber-400/30 text-amber-300 text-[13px] font-mono rounded-lg hover:bg-amber-400/20 transition-colors"
          >
            Run Analysis
          </button>
          <div className="ml-auto text-white/50 text-[13px] font-mono self-center">
            {mosaics.length} mosaics
          </div>
        </div>

        {/* Messages */}
        {msg && (
          <div
            className={`mb-6 px-4 py-3 rounded-lg text-[13px] font-mono ${
              msg.type === 'success'
                ? 'bg-emerald-400/15 border border-emerald-400/30 text-emerald-300'
                : 'bg-red-400/15 border border-red-400/30 text-red-300'
            }`}
          >
            {msg.text}
          </div>
        )}

        {/* Mosaic Grid */}
        <div className="grid grid-cols-1 gap-4">
          {mosaics.map((mosaic) => {
            const isExpanded = expanded.has(mosaic.id);
            return (
              <div
                key={mosaic.id}
                className="bg-[#111827]/80 border border-white/[0.06] rounded-xl overflow-hidden hover:border-white/[0.12] transition-colors"
              >
                {/* Header */}
                <div
                  className="px-6 py-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
                  onClick={() => toggleExpand(mosaic.id)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4 flex-1">
                      {/* Expand Icon */}
                      <div className={isExpanded ? 'text-emerald-400' : 'text-white/40'}>
                        {isExpanded ? <span className="text-xs">▲</span> : <span className="text-xs">▼</span>}
                      </div>

                      {/* Symbol and Basic Info */}
                      <div className="flex items-center gap-3">
                        <span className="text-[16px] font-mono font-bold text-white">{mosaic.symbol}</span>
                      </div>

                      {/* Coherence Score Bar */}
                      {mosaic.coherence_score != null && (
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-2 bg-white/[0.05] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-400 transition-all"
                              style={{ width: `${Math.min(mosaic.coherence_score * 100, 100)}%` }}
                            />
                          </div>
                          <span className="text-[12px] font-mono text-white/70">
                            {(mosaic.coherence_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Right Side */}
                    <div className="flex items-center gap-3">
                      {/* Action Badge */}
                      {mosaic.action && (
                        <span
                          className={`text-[11px] font-mono px-3 py-1.5 rounded-full border transition-colors ${getActionColor(
                            mosaic.action
                          )}`}
                        >
                          {mosaic.action}
                        </span>
                      )}

                      {/* Domain Badge */}
                      {mosaic.domain && (
                        <span
                          className={`text-[11px] font-mono px-3 py-1.5 rounded-full ${getDomainColor(mosaic.domain)}`}
                        >
                          {mosaic.domain}
                        </span>
                      )}

                      {/* Divergence */}
                      {mosaic.divergence_strength != null && (
                        <span className="text-[12px] font-mono text-white/60">
                          div: {(mosaic.divergence_strength * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="bg-white/[0.02] border-t border-white/[0.06] px-6 py-4 space-y-4">
                    {/* Narrative */}
                    {mosaic.narrative && (
                      <div>
                        <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">Narrative</div>
                        <p className="text-[13px] text-white/80 leading-relaxed">{mosaic.narrative}</p>
                      </div>
                    )}

                    {/* Fragments */}
                    {mosaic.fragments_json && (
                      <div>
                        <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">Fragments</div>
                        <pre className="bg-[#0a0f1a] border border-white/[0.06] rounded-lg p-3 text-[11px] font-mono text-white/70 overflow-x-auto max-h-48 overflow-y-auto">
                          {typeof mosaic.fragments_json === 'string'
                            ? mosaic.fragments_json
                            : JSON.stringify(mosaic.fragments_json, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2 pt-2">
                      <Link
                        to={`/gate/review?gate=L2_validation&symbol=${mosaic.symbol}&entity_id=${mosaic.id}&entity_type=mosaic`}
                        className="px-3 py-2 text-[13px] font-mono rounded-lg bg-emerald-400/15 border border-emerald-400/30 text-emerald-300 hover:bg-emerald-400/20 transition-colors no-underline"
                      >
                        Review → Gate
                      </Link>
                      <Link
                        to={`/mosaic/${mosaic.symbol}`}
                        className="px-3 py-2 text-[13px] font-mono rounded-lg bg-white/[0.08] border border-white/[0.12] text-white/80 hover:bg-white/[0.12] transition-colors no-underline"
                      >
                        Workbench
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {mosaics.length === 0 && (
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
            <p className="text-white/50 text-[13px]">No mosaics yet. Run analysis to assemble signal clusters.</p>
          </div>
        )}
    </div>
  );
}
