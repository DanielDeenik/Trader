import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

export default function Decisions() {
  const [reviews, setReviews] = useState([]);
  const [expanded, setExpanded] = useState(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      setLoading(true);
      const data = await api.getReviews();
      const decided = (data || []).filter(r => r.decision && r.decision !== 'pending');
      setReviews(decided);
    } catch (err) {
      console.error('Failed to load reviews:', err);
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

  const getDecisionColor = (decision) => {
    if (decision === 'promote' || decision === 'execute') return 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30';
    if (decision === 'watch') return 'bg-amber-400/15 text-amber-300 border-amber-400/30';
    if (decision === 'discard') return 'bg-red-400/15 text-red-300 border-red-400/30';
    return 'bg-white/[0.08] text-white/60';
  };

  if (loading) {
    return <div className="text-white/60 text-[13px] py-8">Loading decisions...</div>;
  }

  return (
    <div className="space-y-4">
        {/* Summary */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Decided</div>
            <div className="text-white text-[20px] font-mono">{reviews.length}</div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Promoted</div>
            <div className="text-emerald-400 text-[20px] font-mono">
              {reviews.filter(r => r.decision === 'promote' || r.decision === 'execute').length}
            </div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Watch</div>
            <div className="text-amber-400 text-[20px] font-mono">
              {reviews.filter(r => r.decision === 'watch').length}
            </div>
          </div>
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
            <div className="text-white/50 text-[11px] uppercase tracking-wide mb-1">Discarded</div>
            <div className="text-red-400 text-[20px] font-mono">
              {reviews.filter(r => r.decision === 'discard').length}
            </div>
          </div>
        </div>

        {/* Decisions Table */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl overflow-hidden">
          <div className="bg-white/[0.03] border-b border-white/[0.06] px-6 py-3">
            <div className="grid grid-cols-12 gap-4 text-white/50 text-[12px] font-mono uppercase tracking-wider">
              <div className="col-span-2">Symbol</div>
              <div className="col-span-1">Gate</div>
              <div className="col-span-2">Decision</div>
              <div className="col-span-2">Score</div>
              <div className="col-span-2">Created</div>
              <div className="col-span-3 text-right">Action</div>
            </div>
          </div>

          <div>
            {reviews.map((review) => {
              const isExpanded = expanded.has(review.id);
              const scorePercent = review.threshold > 0 ? (review.total_score / review.threshold) * 100 : 0;

              return (
                <div key={review.id}>
                  {/* Main Row */}
                  <div
                    className="border-b border-white/[0.06] hover:bg-white/[0.04] cursor-pointer transition-colors"
                    onClick={() => toggleExpand(review.id)}
                  >
                    <div className="px-6 py-4 grid grid-cols-12 gap-4 items-center">
                      {/* Symbol */}
                      <div className="col-span-2">
                        <span className="text-white font-mono text-[13px] font-semibold">{review.symbol}</span>
                      </div>

                      {/* Gate */}
                      <div className="col-span-1">
                        <span className="text-white/60 text-[12px] font-mono">{review.gate}</span>
                      </div>

                      {/* Decision Badge */}
                      <div className="col-span-2">
                        <span
                          className={`text-[11px] font-mono px-3 py-1.5 rounded-full border transition-colors ${getDecisionColor(review.decision)}`}
                        >
                          {review.decision}
                        </span>
                      </div>

                      {/* Score Bar */}
                      <div className="col-span-2">
                        <div className="flex gap-2 items-center">
                          <div className="flex-1 h-2 bg-white/[0.05] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-400 transition-all"
                              style={{ width: `${Math.min(scorePercent, 100)}%` }}
                            />
                          </div>
                          <span className="text-white/60 font-mono text-[11px] w-16 text-right">
                            {review.total_score}/{review.threshold}
                          </span>
                        </div>
                      </div>

                      {/* Created */}
                      <div className="col-span-2">
                        <span className="text-white/60 text-[12px]">
                          {review.created_at ? new Date(review.created_at).toLocaleDateString() : '—'}
                        </span>
                      </div>

                      {/* Actions */}
                      <div className="col-span-3 flex justify-end">
                        <div className={isExpanded ? 'text-emerald-400' : 'text-white/40'}>
                          {isExpanded ? <span className="text-xs">▲</span> : <span className="text-xs">▼</span>}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="bg-white/[0.02] border-b border-white/[0.06]">
                      <div className="px-6 py-4 space-y-4">
                        {/* Dominant Narrative */}
                        {review.dominant_narrative && (
                          <div>
                            <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">Narrative</div>
                            <p className="text-[13px] text-white/80 leading-relaxed">{review.dominant_narrative}</p>
                          </div>
                        )}

                        {/* Market Pricing */}
                        {review.market_pricing && (
                          <div>
                            <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">Market Pricing</div>
                            <p className="text-[13px] text-white/80">{review.market_pricing}</p>
                          </div>
                        )}

                        {/* Invalidation */}
                        {review.invalidation && (
                          <div>
                            <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">Invalidation</div>
                            <p className="text-[13px] text-white/80">{review.invalidation}</p>
                          </div>
                        )}

                        {/* Scores JSON */}
                        {review.scores_json && (
                          <div>
                            <div className="text-white/50 text-[11px] uppercase tracking-wider font-mono mb-2">Scores</div>
                            <pre className="bg-[#0a0f1a] border border-white/[0.06] rounded-lg p-3 text-[11px] font-mono text-white/70 overflow-x-auto max-h-48 overflow-y-auto">
                              {typeof review.scores_json === 'string'
                                ? review.scores_json
                                : JSON.stringify(review.scores_json, null, 2)}
                            </pre>
                          </div>
                        )}

                        {/* Risk Note */}
                        {review.risk_note && (
                          <div className="bg-amber-400/10 border border-amber-400/20 rounded-lg p-3">
                            <div className="text-amber-300 text-[12px]">{review.risk_note}</div>
                          </div>
                        )}

                        {/* Action Button */}
                        {(review.decision === 'promote' || review.decision === 'execute') && (
                          <Link
                            to={`/positions?create=${review.symbol}`}
                            className="inline-block px-4 py-2 text-[13px] font-mono rounded-lg bg-emerald-400/15 border border-emerald-400/30 text-emerald-300 hover:bg-emerald-400/20 transition-colors no-underline"
                          >
                            Create Position →
                          </Link>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {reviews.length === 0 && (
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
            <p className="text-white/50 text-[13px]">No decisions yet. Promote signals through HITL gates.</p>
          </div>
        )}
    </div>
  );
}
