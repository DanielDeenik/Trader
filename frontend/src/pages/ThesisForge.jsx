import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function ThesisForge() {
  const { data: theses, refetch } = useApi(() => api.getTheses())
  const [expanded, setExpanded] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ symbol: '', domain: 'public', thesis_type: '', lifecycle_stage: 'emerging', roi_bear: '', roi_base: '', roi_bull: '', risk_assessment: '' })
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createThesis({
        ...form,
        roi_bear: parseFloat(form.roi_bear) / 100,
        roi_base: parseFloat(form.roi_base) / 100,
        roi_bull: parseFloat(form.roi_bull) / 100,
      })
      setForm({ symbol: '', domain: 'public', thesis_type: '', lifecycle_stage: 'emerging', roi_bear: '', roi_base: '', roi_bull: '', risk_assessment: '' })
      setShowForm(false)
      refetch()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">+ Create Thesis</button>
        )}
        <button onClick={refetch} className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded">Refresh</button>
        <span className="text-xs text-gray-400 self-center">{(theses || []).length} theses</span>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-gray-800 border border-gray-700 rounded p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs text-gray-400 block mb-1">Symbol</label><input value={form.symbol} onChange={e => setForm({...form, symbol: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Domain</label><select value={form.domain} onChange={e => setForm({...form, domain: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs"><option value="public">Public</option><option value="private">Private</option><option value="crypto">Crypto</option></select></div>
            <div><label className="text-xs text-gray-400 block mb-1">Thesis Type</label><input value={form.thesis_type} onChange={e => setForm({...form, thesis_type: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Lifecycle Stage</label><select value={form.lifecycle_stage} onChange={e => setForm({...form, lifecycle_stage: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs"><option value="emerging">Emerging</option><option value="validating">Validating</option><option value="confirmed">Confirmed</option><option value="saturated">Saturated</option></select></div>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div><label className="text-xs text-gray-400 block mb-1">ROI Bear %</label><input type="number" step="0.1" value={form.roi_bear} onChange={e => setForm({...form, roi_bear: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">ROI Base %</label><input type="number" step="0.1" value={form.roi_base} onChange={e => setForm({...form, roi_base: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">ROI Bull %</label><input type="number" step="0.1" value={form.roi_bull} onChange={e => setForm({...form, roi_bull: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
          </div>
          <div><label className="text-xs text-gray-400 block mb-1">Risk Assessment</label><textarea value={form.risk_assessment} onChange={e => setForm({...form, risk_assessment: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" rows="3" /></div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">{saving ? 'Creating...' : 'Create'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1 bg-gray-700 text-gray-300 border border-gray-600 text-xs rounded">Cancel</button>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
        </form>
      )}

      {(theses || []).map(t => (
        <div key={t.id} className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="flex justify-between items-center cursor-pointer" onClick={() => setExpanded(expanded === t.id ? null : t.id)}>
            <div className="flex items-center gap-3">
              <SymbolLink symbol={t.symbol} />
              {t.lifecycle_stage && <span className="text-xs text-yellow-400">{t.lifecycle_stage}</span>}
              {t.status && <span className={`text-xs px-1 rounded ${t.status === 'active' ? 'bg-emerald-900 text-emerald-400' : 'bg-gray-700 text-gray-400'}`}>{t.status}</span>}
            </div>
            <span className="text-xs text-gray-500">{t.domain}</span>
          </div>

          {expanded === t.id && (
            <div className="mt-2 border-t border-gray-700 pt-2 text-xs space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-red-900/30 p-2 rounded"><span className="text-gray-400">Bear:</span> <span className="text-red-400">{t.roi_bear != null ? `${(t.roi_bear * 100).toFixed(0)}%` : '—'}</span></div>
                <div className="bg-gray-900 p-2 rounded"><span className="text-gray-400">Base:</span> <span className="text-gray-200">{t.roi_base != null ? `${(t.roi_base * 100).toFixed(0)}%` : '—'}</span></div>
                <div className="bg-emerald-900/30 p-2 rounded"><span className="text-gray-400">Bull:</span> <span className="text-emerald-400">{t.roi_bull != null ? `${(t.roi_bull * 100).toFixed(0)}%` : '—'}</span></div>
              </div>
              {t.kelly_fraction != null && <div className="text-gray-400">Kelly: {(t.kelly_fraction * 100).toFixed(1)}%</div>}
              {t.vulnerability_json && <pre className="bg-gray-900 p-2 rounded text-gray-400 overflow-x-auto max-h-24 overflow-y-auto">{typeof t.vulnerability_json === 'string' ? t.vulnerability_json : JSON.stringify(t.vulnerability_json, null, 2)}</pre>}
              <a href={`/gate/review?gate=L3_conviction&symbol=${t.symbol}&entity_id=${t.id}&entity_type=thesis`} className="block text-emerald-400 hover:text-emerald-300 no-underline">→ Review at L3 Gate</a>
            </div>
          )}
        </div>
      ))}

      {(!theses || theses.length === 0) && <div className="text-gray-500 text-xs">No theses yet. Run analysis to forge theses from mosaics.</div>}
    </div>
  )
}
