import { useState } from "react";

const THEMES = [
  { id: 'health_energy_shift', name: 'Health-Conscious Energy', sector: 'consumer_health',
    keywords: ['energy drink','celsius','clean energy','zero sugar','healthy','gym','pre workout'],
    tickers: { up: ['CELH','PEP'], down: ['MNST','GIS'], hidden: ['LULU','PLNT'] },
    desc: 'Gen Z shifting from sugar-loaded to health-positioned energy brands' },
  { id: 'ozempic_economy', name: 'GLP-1 / Ozempic Economy', sector: 'pharma_consumer',
    keywords: ['ozempic','wegovy','glp-1','weight loss','semaglutide','mounjaro','obesity'],
    tickers: { up: ['NVO','LLY','HIMS'], down: ['WW','DXCM','MCD'], hidden: ['LULU','HSY'] },
    desc: 'GLP-1 drugs reshaping food, fitness, fashion, and healthcare spending' },
  { id: 'ai_infrastructure', name: 'AI Infrastructure Build-Out', sector: 'tech_infra',
    keywords: ['gpu','nvidia','data center','ai training','chips','compute','llm'],
    tickers: { up: ['NVDA','TSM','AVGO'], down: ['CHGG'], hidden: ['VRT','CEG','CCJ'] },
    desc: 'Massive capex cycle for AI compute infrastructure' },
  { id: 'ai_application_layer', name: 'AI Application Winners', sector: 'tech_software',
    keywords: ['chatgpt','copilot','ai agent','generative ai','ai coding'],
    tickers: { up: ['MSFT','PLTR','CRM'], down: ['UPWK','CHGG'], hidden: ['CRWD'] },
    desc: 'Companies monetizing AI at the application layer' },
  { id: 'nuclear_energy_revival', name: 'Nuclear Energy Revival', sector: 'energy',
    keywords: ['nuclear','uranium','smr','baseload','nuclear power'],
    tickers: { up: ['CCJ','LEU','CEG'], down: [], hidden: ['NNE','BWXT','GEV'] },
    desc: 'Nuclear energy as the answer to AI massive energy demand' },
  { id: 'defi_renaissance', name: 'DeFi Renaissance', sector: 'crypto_defi',
    keywords: ['defi','yield','tvl','dex','restaking','eigenlayer','lending'],
    tickers: { up: ['AAVE','UNI','ETH'], down: [], hidden: ['LINK','SOL','COIN'] },
    desc: 'DeFi protocols seeing renewed usage and TVL growth' },
  { id: 'real_world_assets', name: 'RWA Tokenization', sector: 'crypto_rwa',
    keywords: ['rwa','tokenization','real world asset','ondo','treasury token'],
    tickers: { up: ['ONDO','MKR','LINK'], down: [], hidden: ['AVAX','ETH'] },
    desc: 'Tokenization of real-world assets' },
  { id: 'tiktok_commerce', name: 'TikTok-Driven Commerce', sector: 'ecommerce',
    keywords: ['tiktok shop','viral product','haul','unboxing','social commerce'],
    tickers: { up: ['SHOP','AMZN'], down: [], hidden: ['CPNG','SNAP'] },
    desc: 'Social commerce driven by TikTok discovery' },
  { id: 'nearshoring_renaissance', name: 'Manufacturing Nearshoring', sector: 'industrials',
    keywords: ['nearshoring','reshoring','made in usa','tariff','supply chain'],
    tickers: { up: ['CAT','ETN','ROK'], down: [], hidden: ['PCAR','XPO'] },
    desc: 'Manufacturing shifting from China to US/Mexico' },
  { id: 'experience_economy', name: 'Experience Over Things', sector: 'travel_leisure',
    keywords: ['travel','concert','live event','festival','experience'],
    tickers: { up: ['BKNG','ABNB','LYV'], down: [], hidden: ['UBER','RCL'] },
    desc: 'Post-COVID shift to experiences over material goods' },
  { id: 'retail_trading_surge', name: 'Retail Trading Resurgence', sector: 'fintech',
    keywords: ['meme stock','yolo','wallstreetbets','0dte','robinhood'],
    tickers: { up: ['HOOD','COIN'], down: [], hidden: ['CBOE','IBKR'] },
    desc: 'Retail trader activity surging' },
  { id: 'ai_crypto_convergence', name: 'AI x Crypto Convergence', sector: 'crypto_ai',
    keywords: ['ai agent','depin','compute token','decentralized ai','render','bittensor'],
    tickers: { up: ['RNDR','FET','TAO'], down: [], hidden: ['AKT','LINK'] },
    desc: 'Intersection of AI compute and decentralized infrastructure' },
];

function detectClusters(text) {
  const t = text.toLowerCase();
  const results = [];
  for (const th of THEMES) {
    const matches = th.keywords.filter(kw => t.includes(kw));
    if (matches.length > 0) {
      const coverage = matches.length / th.keywords.length;
      const strength = Math.min(10, coverage * 8 + matches.length * 0.5);
      results.push({ ...th, matches, coverage, strength,
        lifecycle: coverage > 0.5 ? 'confirmed' : coverage > 0.2 ? 'validating' : 'emerging' });
    }
  }
  results.sort((a, b) => b.strength - a.strength);
  return results;
}

function Chip({ ticker, type }) {
  const colors = {
    up: { bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.3)', text: '#22c55e' },
    down: { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)', text: '#ef4444' },
    hidden: { bg: 'rgba(168,85,247,0.12)', border: 'rgba(168,85,247,0.3)', text: '#a855f7' },
  };
  const c = colors[type];
  return (
    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
      fontFamily: 'monospace', background: c.bg, color: c.text, border: `1px solid ${c.border}` }}>
      {ticker}
    </span>
  );
}

function ClusterCard({ cluster, isActive, onClick }) {
  const strColor = cluster.strength >= 6 ? '#22c55e' : cluster.strength >= 3 ? '#eab308' : '#6b7280';
  return (
    <div onClick={onClick} style={{
      background: '#0d1117', border: `1px solid ${isActive ? '#3b82f6' : '#1e293b'}`,
      borderRadius: 8, padding: 12, marginBottom: 10, cursor: 'pointer',
      boxShadow: isActive ? '0 0 12px rgba(59,130,246,0.15)' : 'none',
      transition: 'border-color 0.15s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{cluster.name}</span>
        <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 10, fontWeight: 600,
          background: `${strColor}22`, color: strColor }}>{cluster.strength.toFixed(1)}</span>
      </div>
      <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
        {cluster.sector} · {cluster.lifecycle} · {cluster.matches.length} keywords · {(cluster.coverage*100).toFixed(0)}% coverage
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
        {cluster.tickers.up.map(t => <Chip key={t} ticker={t} type="up" />)}
        {cluster.tickers.down.map(t => <Chip key={t} ticker={t} type="down" />)}
        {cluster.tickers.hidden.map(t => <Chip key={t} ticker={t} type="hidden" />)}
      </div>
      {isActive && (
        <div style={{ marginTop: 12 }}>
          {cluster.tickers.up.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', marginBottom: 4 }}>Upstream (Beneficiaries)</div>
              {cluster.tickers.up.map(t => (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px', fontSize: 12 }}>
                  <span style={{ color: '#22c55e' }}>+</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#22c55e' }}>{t}</span>
                  <span style={{ color: '#6b7280' }}>Direct beneficiary</span>
                </div>
              ))}
            </div>
          )}
          {cluster.tickers.down.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', marginBottom: 4 }}>Downstream (Disrupted)</div>
              {cluster.tickers.down.map(t => (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px', fontSize: 12 }}>
                  <span style={{ color: '#ef4444' }}>-</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#ef4444' }}>{t}</span>
                  <span style={{ color: '#6b7280' }}>Short candidate</span>
                </div>
              ))}
            </div>
          )}
          {cluster.tickers.hidden.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', marginBottom: 4 }}>Hidden Alpha (2nd/3rd Order)</div>
              {cluster.tickers.hidden.map(t => (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px', fontSize: 12 }}>
                  <span style={{ color: '#a855f7' }}>★</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#a855f7' }}>{t}</span>
                  <span style={{ color: '#6b7280' }}>Information edge</span>
                  <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 8, background: 'rgba(168,85,247,0.15)', color: '#a855f7' }}>ALPHA</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <p style={{ fontSize: 11, color: '#6b7280', marginTop: 6 }}>{cluster.desc}</p>
    </div>
  );
}

export default function App() {
  const [obs, setObs] = useState('');
  const [keywords, setKeywords] = useState('');
  const [clusters, setClusters] = useState([]);
  const [selected, setSelected] = useState(-1);
  const [conviction, setConviction] = useState(50);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('Ready — Enter a trend observation below');

  function log(msg) {
    setEvents(prev => [{ time: new Date().toLocaleTimeString(), msg }, ...prev].slice(0, 30));
  }

  function analyze() {
    if (!obs.trim()) return;
    setStatus('Analyzing...');
    log('Started trend analysis');
    const c = detectClusters(obs + ' ' + keywords);
    setClusters(c);
    setSelected(-1);
    setStatus(`Found ${c.length} trend cluster${c.length !== 1 ? 's' : ''}`);
    log(`Detected ${c.length} trend clusters`);
  }

  const sel = selected >= 0 ? clusters[selected] : null;
  const score = sel ? Math.min(100, sel.strength * 10) : 0;
  const verdict = score >= 75 ? 'STRONG BUY' : score >= 55 ? 'BUY' : score >= 35 ? 'WATCH' : score >= 15 ? 'PASS' : 'AVOID';
  const vColor = score >= 75 ? '#22c55e' : score >= 55 ? '#3b82f6' : score >= 35 ? '#eab308' : score >= 15 ? '#f97316' : '#ef4444';

  const hubs = {};
  clusters.forEach(c => [...c.tickers.up, ...c.tickers.hidden].forEach(t => { hubs[t] = (hubs[t]||0)+1; }));
  const hubList = Object.entries(hubs).sort((a,b)=>b[1]-a[1]).slice(0,8);

  const hiddenAll = clusters.flatMap(c => c.tickers.hidden.map(t => ({ ticker: t, theme: c.name })));
  const shortsAll = clusters.flatMap(c => c.tickers.down.map(t => ({ ticker: t, theme: c.name })));

  const inputStyle = {
    width: '100%', background: '#0d1117', border: '1px solid #1e293b', color: '#c9d1d9',
    padding: '8px 10px', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', outline: 'none',
  };

  return (
    <div style={{ background: '#0f172a', color: '#c9d1d9', minHeight: '100vh',
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      {/* Header */}
      <div style={{ background: '#1e293b', borderBottom: '1px solid #334155', padding: '12px 20px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 18, fontWeight: 700, color: '#3b82f6' }}>Social Arb — Trend Lattice</span>
        <span style={{ fontSize: 12, color: '#6b7280' }}>{status}</span>
      </div>

      {/* 3-Panel Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 300px', gap: 1, background: '#334155', minHeight: 'calc(100vh - 50px)' }}>
        {/* LEFT: Input */}
        <div style={{ background: '#1e293b', padding: 16, overflowY: 'auto' }}>
          <div style={{ fontSize: 12, color: '#3b82f6', textTransform: 'uppercase', fontWeight: 600, marginBottom: 10 }}>Your Observation</div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: '#6b7280', display: 'block', marginBottom: 3 }}>What did you see on the ground?</label>
            <textarea value={obs} onChange={e => setObs(e.target.value)} placeholder="e.g., Every nurse at the hospital is drinking Celsius. The vending machine at my gym sold out."
              style={{ ...inputStyle, height: 100, resize: 'vertical' }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: '#6b7280', display: 'block', marginBottom: 3 }}>Keywords</label>
            <input value={keywords} onChange={e => setKeywords(e.target.value)} placeholder="celsius, energy drink, gen z"
              style={inputStyle} />
          </div>
          <button onClick={analyze} style={{
            width: '100%', padding: '10px', background: '#3b82f6', color: '#fff', border: 'none',
            borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
            Analyze Trend
          </button>

          {hubList.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 12, color: '#3b82f6', textTransform: 'uppercase', fontWeight: 600, marginBottom: 8 }}>Hub Tickers</div>
              {hubList.map(([t, n]) => (
                <div key={t} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #334155', fontSize: 12 }}>
                  <span>{t}</span><span style={{ color: '#3b82f6', fontFamily: 'monospace' }}>{n} themes</span>
                </div>
              ))}
            </div>
          )}

          {events.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 12, color: '#3b82f6', textTransform: 'uppercase', fontWeight: 600, marginBottom: 8 }}>Event Log</div>
              <div style={{ maxHeight: 150, overflowY: 'auto', fontSize: 11, fontFamily: 'monospace' }}>
                {events.map((e, i) => (
                  <div key={i} style={{ padding: '2px 0', color: '#6b7280', borderBottom: '1px solid rgba(51,65,85,0.5)' }}>
                    <span style={{ color: '#3b82f6' }}>{e.time}</span> {e.msg}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* CENTER: Clusters */}
        <div style={{ background: '#1e293b', padding: 16, overflowY: 'auto' }}>
          <div style={{ fontSize: 12, color: '#3b82f6', textTransform: 'uppercase', fontWeight: 600, marginBottom: 10 }}>Trend Clusters & Beneficiary Map</div>
          {clusters.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <p style={{ fontSize: 15, marginBottom: 8 }}>Enter your ground-level observation</p>
              <p style={{ fontSize: 12 }}>The system will cluster signals, map beneficiaries, and show you the upstream/downstream supply chain.</p>
            </div>
          ) : (
            clusters.map((c, i) => (
              <ClusterCard key={c.id} cluster={c} isActive={selected === i}
                onClick={() => { setSelected(i); log(`Selected: ${c.name}`); }} />
            ))
          )}
        </div>

        {/* RIGHT: Assessment */}
        <div style={{ background: '#1e293b', padding: 16, overflowY: 'auto' }}>
          <div style={{ fontSize: 12, color: '#3b82f6', textTransform: 'uppercase', fontWeight: 600, marginBottom: 10 }}>Your Assessment</div>

          {sel && (
            <div style={{ background: '#0d1117', border: '1px solid #1e293b', borderRadius: 8, padding: 12, marginBottom: 12 }}>
              <div style={{ fontSize: 13, color: '#3b82f6', fontWeight: 600, marginBottom: 8 }}>Thesis Verdict</div>
              <span style={{ display: 'inline-block', padding: '4px 12px', borderRadius: 6, fontWeight: 700, fontSize: 13,
                background: `${vColor}22`, color: vColor }}>{verdict}</span>
              <span style={{ marginLeft: 8, fontSize: 13 }}>{score.toFixed(0)}% conviction</span>
              <div style={{ height: 6, background: '#334155', borderRadius: 3, margin: '8px 0', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${score}%`, background: vColor, borderRadius: 3 }} />
              </div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>
                {sel.matches.length} keywords · {sel.tickers.up.length} longs · {sel.tickers.down.length} shorts · {sel.tickers.hidden.length} hidden
              </div>
            </div>
          )}

          <div style={{ background: '#0d1117', border: '1px solid #1e293b', borderRadius: 8, padding: 12, marginBottom: 12 }}>
            <div style={{ fontSize: 13, color: '#3b82f6', fontWeight: 600, marginBottom: 6 }}>Human Override</div>
            <p style={{ fontSize: 11, color: '#6b7280', marginBottom: 8 }}>You are the final decision maker. The system gives you data, YOU make the call.</p>
            <label style={{ fontSize: 11, color: '#6b7280' }}>Conviction Level: {conviction}%</label>
            <input type="range" min={0} max={100} value={conviction} onChange={e => setConviction(+e.target.value)}
              style={{ width: '100%', accentColor: '#3b82f6', margin: '6px 0' }} />
          </div>

          <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
            <button disabled={!sel} onClick={() => { log(`APPROVED @ ${conviction}%`); alert(`Trade queued! Conviction: ${conviction}%`); }}
              style={{ padding: '6px 14px', borderRadius: 6, border: 'none', fontSize: 11, fontWeight: 600, cursor: sel?'pointer':'default',
                background: sel ? '#22c55e' : '#334155', color: sel ? '#fff' : '#6b7280' }}>Approve Trade</button>
            <button disabled={!sel} onClick={() => { log('Added to watchlist'); }}
              style={{ padding: '6px 14px', borderRadius: 6, border: 'none', fontSize: 11, fontWeight: 600, cursor: sel?'pointer':'default',
                background: sel ? '#eab308' : '#334155', color: sel ? '#000' : '#6b7280' }}>Watchlist</button>
            <button disabled={!sel} onClick={() => { log('REJECTED'); }}
              style={{ padding: '6px 14px', borderRadius: 6, border: 'none', fontSize: 11, fontWeight: 600, cursor: sel?'pointer':'default',
                background: sel ? '#ef4444' : '#334155', color: sel ? '#fff' : '#6b7280' }}>Reject</button>
          </div>

          {hiddenAll.length > 0 && (
            <div style={{ background: '#0d1117', border: '1px solid #1e293b', borderRadius: 8, padding: 12, marginBottom: 12 }}>
              <div style={{ fontSize: 13, color: '#a855f7', fontWeight: 600, marginBottom: 6 }}>Hidden Alpha</div>
              {hiddenAll.map((h, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '3px 0' }}>
                  <span style={{ color: '#a855f7', fontFamily: 'monospace', fontWeight: 600 }}>{h.ticker}</span>
                  <span style={{ color: '#6b7280', fontSize: 11 }}>{h.theme}</span>
                </div>
              ))}
            </div>
          )}

          {shortsAll.length > 0 && (
            <div style={{ background: '#0d1117', border: '1px solid #1e293b', borderRadius: 8, padding: 12 }}>
              <div style={{ fontSize: 13, color: '#ef4444', fontWeight: 600, marginBottom: 6 }}>Short Candidates</div>
              {shortsAll.map((s, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '3px 0' }}>
                  <span style={{ color: '#ef4444', fontFamily: 'monospace', fontWeight: 600 }}>{s.ticker}</span>
                  <span style={{ color: '#6b7280', fontSize: 11 }}>{s.theme}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
