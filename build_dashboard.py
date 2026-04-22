"""Build a self-contained HTML dashboard with all data embedded from SQLite.

Zero hardcoding — every value comes from the database.

Usage: python build_dashboard.py
Output: dashboard_live.html (opens in any browser, no server needed)
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = str((Path(__file__).parent / "social_arb" / "db" / "social_arb.db").resolve())
OUTPUT_PATH = Path(__file__).parent / "dashboard_live.html"


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def export_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    data = {"exported_at": datetime.utcnow().isoformat()}

    data["signals"] = conn.execute(
        "SELECT id, timestamp, symbol, source, signal_type, direction, strength, confidence, data_class, raw_json FROM signals ORDER BY timestamp DESC"
    ).fetchall()
    for s in data["signals"]:
        if s.get("raw_json"):
            try: s["raw"] = json.loads(s["raw_json"])
            except: s["raw"] = {}
        else:
            s["raw"] = {}

    data["mosaics"] = conn.execute(
        "SELECT id, symbol, domain, coherence_score, divergence_strength, fragments_json, narrative, action, data_class, created_at FROM mosaics ORDER BY coherence_score DESC"
    ).fetchall()
    for m in data["mosaics"]:
        if m.get("fragments_json"):
            try: m["fragments"] = json.loads(m["fragments_json"])
            except: m["fragments"] = []
        else:
            m["fragments"] = []

    data["theses"] = conn.execute(
        "SELECT id, mosaic_id, symbol, domain, roi_bear, roi_base, roi_bull, kelly_fraction, lifecycle_stage, status, created_at FROM theses ORDER BY created_at DESC"
    ).fetchall()

    data["decisions"] = conn.execute(
        "SELECT id, thesis_id, gate, symbol, decision, confidence, rationale, trust_level, created_at FROM decisions ORDER BY created_at DESC"
    ).fetchall()

    # Compute summary from data
    source_counts = {}
    symbol_counts = {}
    for s in data["signals"]:
        source_counts[s["source"]] = source_counts.get(s["source"], 0) + 1
        symbol_counts[s["symbol"]] = symbol_counts.get(s["symbol"], 0) + 1

    domain_counts = {}
    data_class_counts = {}
    for m in data["mosaics"]:
        domain_counts[m["domain"]] = domain_counts.get(m["domain"], 0) + 1
        dc = m.get("data_class") or "public"
        data_class_counts[dc] = data_class_counts.get(dc, 0) + 1

    thesis_statuses = {}
    for t in data["theses"]:
        st = t.get("status", "unknown")
        thesis_statuses[st] = thesis_statuses.get(st, 0) + 1

    data["summary"] = {
        "total_signals": len(data["signals"]),
        "total_mosaics": len(data["mosaics"]),
        "total_theses": len(data["theses"]),
        "total_decisions": len(data["decisions"]),
        "source_counts": source_counts,
        "symbol_counts": symbol_counts,
        "domain_counts": domain_counts,
        "data_class_counts": data_class_counts,
        "thesis_statuses": thesis_statuses,
    }

    conn.close()
    return data


def build():
    data = export_data()
    js_data = json.dumps(data, default=str)

    # Read the template dashboard and inject data
    template = (Path(__file__).parent / "dashboard.html").read_text()

    # Replace the API fetch pattern with embedded data
    injection = f"""
<script>
// ALL DATA FROM SQLITE — ZERO HARDCODED VALUES
window.__SOCIAL_ARB_DATA__ = {js_data};
</script>
"""

    # Insert data script before the React babel script
    html = template.replace(
        '<div id="root"></div>',
        f'<div id="root"></div>\n{injection}'
    )

    # Replace the useFetch hook to use embedded data
    html = html.replace(
        """const API = "http://localhost:8787/api";

function useFetch(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    setLoading(true);
    fetch(url)
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [url]);
  return { data, loading, error };
}""",
        """const DB = window.__SOCIAL_ARB_DATA__ || {};

function resolveEndpoint(url) {
  // Map API URLs to embedded data
  if (url.includes("/api/summary")) return DB.summary;
  if (url.includes("/api/mosaics")) {
    const m = url.match(/symbol=(\\w+)/);
    return m ? DB.mosaics.filter(x => x.symbol === m[1]) : DB.mosaics;
  }
  if (url.includes("/api/theses")) {
    const m = url.match(/status=(\\w+)/);
    return m ? DB.theses.filter(x => x.status === m[1]) : DB.theses;
  }
  if (url.includes("/api/signals")) {
    let results = DB.signals || [];
    const symMatch = url.match(/symbol=(\\w+)/);
    const srcMatch = url.match(/source=(\\w+)/);
    if (symMatch) results = results.filter(x => x.symbol === symMatch[1]);
    if (srcMatch) results = results.filter(x => x.source === srcMatch[1]);
    return results.slice(0, 500);
  }
  if (url.includes("/api/symbol")) {
    const m = url.match(/s=(\\w+)/);
    if (m) {
      const sym = m[1];
      return {
        symbol: sym,
        signals: (DB.signals || []).filter(x => x.symbol === sym),
        mosaics: (DB.mosaics || []).filter(x => x.symbol === sym),
        theses: (DB.theses || []).filter(x => x.symbol === sym),
        decisions: (DB.decisions || []).filter(x => x.symbol === sym),
      };
    }
  }
  if (url.includes("/api/scans")) return DB.scans || [];
  if (url.includes("/api/decisions")) return DB.decisions || [];
  return null;
}

function useFetch(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    setLoading(true);
    try {
      const resolved = resolveEndpoint(url);
      setData(resolved);
      setLoading(false);
    } catch(e) {
      setError(e.message);
      setLoading(false);
    }
  }, [url]);
  return { data, loading, error };
}

const API = "embedded";"""
    )

    OUTPUT_PATH.write_text(html)
    print(f"Built {OUTPUT_PATH}")
    print(f"  {data['summary']['total_signals']} signals from {list(data['summary']['source_counts'].keys())}")
    print(f"  {data['summary']['total_mosaics']} mosaics across {list(data['summary']['domain_counts'].keys())}")
    print(f"  {data['summary']['total_theses']} theses ({data['summary']['thesis_statuses']})")
    return str(OUTPUT_PATH)


if __name__ == "__main__":
    build()
