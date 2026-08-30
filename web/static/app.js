// ============================================================================
// SHOW ITS WORK — frontend interactions
// ============================================================================
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = (p, o) => fetch(p, o).then(r => r.json());
let STATE = { scenarios: [], activeScn: null, last: null };

// ---- live clock + status ----
function tick() {
  const d = new Date();
  const t = d.toTimeString().slice(0, 8);
  const off = -d.getTimezoneOffset() / 60;
  $('#clock').textContent = t; $('#clock2').textContent = t;
  $('#tz').textContent = 'UTC' + (off >= 0 ? '+' : '') + off;
}
setInterval(tick, 1000); tick();

// ---- boot ----
(async function boot() {
  const b = await api('/api/bootstrap');
  STATE.scenarios = b.scenarios;
  const sel = $('#persona');
  sel.innerHTML = b.personas.map(p => `<option value="${p.key}">${p.label}</option>`).join('');
  sel.value = 'revenue_analyst';
  const chips = $('#chips');
  b.scenarios.forEach(s => {
    const c = document.createElement('button');
    c.className = 'chip'; c.dataset.id = s.id;
    c.innerHTML = `<span class="c">${s.code}</span> ${s.label}`;
    c.onclick = () => loadScenario(s.id);
    chips.appendChild(c);
  });
})();

function loadScenario(id) {
  const s = STATE.scenarios.find(x => x.id === id); if (!s) return;
  $('#q').value = s.question; $('#persona').value = s.persona;
  STATE.activeScn = s;
  $$('.chip').forEach(c => c.classList.toggle('active', c.dataset.id === id));
  $('#scntag').textContent = '//' + s.code;
  runInvestigation(s.window);
}
function scrollTo2(sel) { $(sel).scrollIntoView({ behavior: 'smooth' }); }

// ---- pipeline runner animation ----
const STAGES = [
  ['01', 'GATE'], ['02', 'FACTPACK'], ['03', 'PROPOSE'],
  ['04', 'SKEPTIC'], ['05', 'JUDGE'], ['06', 'WRITE'], ['07', 'VERIFY']];
function buildStages() {
  $('#stages').innerHTML = STAGES.map(([n, t]) =>
    `<div class="stg" data-t="${t}"><div class="n">${n}</div><div class="t">${t}</div><div class="tick"></div></div>`).join('');
}
async function animateStages() {
  const els = $$('#stages .stg');
  for (let i = 0; i < els.length; i++) {
    els[i].classList.add('active'); els[i].querySelector('.tick').textContent = '▹';
    $('#run-title').textContent = '> ' + els[i].dataset.t;
    await sleep(150 + Math.random() * 110);
    els[i].classList.remove('active'); els[i].classList.add('done');
    els[i].querySelector('.tick').textContent = '✓';
  }
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---- run ----
async function runInvestigation(window) {
  const btn = $('#run'); btn.disabled = true;
  $('#access').textContent = '> RUNNING ANALYSIS_';
  buildStages(); $('#runner').classList.add('on');
  $('#results').classList.remove('on');
  const t0 = performance.now();
  const [data] = await Promise.all([
    api('/api/investigate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: $('#q').value, persona: $('#persona').value,
        window: window || (STATE.activeScn && STATE.activeScn.window) || null
      })
    }),
    animateStages()
  ]);
  STATE.last = data;
  await sleep(120);
  $('#runner').classList.remove('on');
  render(data);
  btn.disabled = false;
  const ms = Math.round(performance.now() - t0);
  $('#lat').textContent = 'LATENCY ' + ms + 'MS';
  $('#access').textContent = data.verdict.level === 'INSUFFICIENT'
    ? '> ABSTAINED — INSUFFICIENT EVIDENCE_' : '> ACCESS GRANTED_';
  $('#scn').textContent = 'SCN ' + String(Math.floor(Math.random() * 9000) + 1000);
  $('#results').classList.add('on');
  $('#results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ---- markdown-ish memo ----
function cites(s) {
  return s.replace(/\[([FD]\d{3})\]/g, (m, id) =>
    `<span class="cite ${id[0]}" data-id="${id}" onclick="jumpCite('${id}')">[${id}]</span>`);
}
function bold(s) { return s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'); }
function renderMemo(md) {
  const blocks = md.split('\n\n').map(b => b.trim()).filter(Boolean);
  let html = '';
  for (const b of blocks) {
    if (b.startsWith('**For ') || b.startsWith('> ')) continue;         // rendered elsewhere
    const m = b.match(/^\*\*(.+?)\*\*\s*([\s\S]*)$/);
    if (m && m[2]) html += `<h4>${m[1].replace(/\.$/,'')}</h4><p>${cites(bold(m[2]))}</p>`;
    else html += `<p>${cites(bold(b))}</p>`;
  }
  return html;
}
function jumpCite(id) {
  scrollTo2('#receipts');
  setTimeout(() => {
    $$('.tbl tr').forEach(r => r.classList.remove('hl'));
    const row = $(`tr[data-fid="${id}"]`); if (row) { row.classList.add('hl'); }
  }, 400);
}

// ---- render everything ----
function render(d) {
  $('#answer-desc').textContent = d.analysis_kpi.toUpperCase().replace(/_/g, ' ') + ' · ' + d.persona.replace(/_/g,' ');
  // verdict
  const v = d.verdict;
  $('#verdict').innerHTML = `<span class="badge ${v.level}"><span class="led"></span>${v.level} CONFIDENCE</span>`;
  // redactions
  $('#redactions').innerHTML = (d.redactions || []).map(r =>
    `<div class="redact"><span class="lk">[LOCK]</span><span>${r}</span></div>`).join('');
  // memo
  $('#memo').innerHTML = renderMemo(d.memo);
  staggerIn('#memo > *');
  // actions
  $('#actions').innerHTML = (d.actions.length ? d.actions : []).map(a => `
    <div class="hyp" style="margin:10px 0"><div class="h" style="cursor:default">
      <span class="stamp survived" style="font-size:10px">${a.confidence}</span>
      <span class="claim"><b>${a.driver}</b> → <span style="color:var(--violet)">${a.lever}</span><br>
      <span style="color:var(--ink-2);font-size:11px">${a.action}</span><br>
      <span style="color:var(--ink-3);font-size:10.5px">Impact: ${a.expected_impact} · Owner: ${a.owner}</span></span>
    </div></div>`).join('') || '<p class="mono-label" style="margin-top:8px">No actions — engine abstained.</p>';

  // skeptic
  $('#hyps').innerHTML = d.hypotheses.map((h, i) => {
    const stamp = h.status === 'killed' ? 'REJECTED' : h.status === 'survived' ? 'SURVIVED' : 'OPEN';
    const atk = h.attacks.map(a =>
      `<div class="atk ${a.passed ? 'ok' : 'no'}"><span class="mk">${a.passed ? '✓' : '✗'}</span>
       <span class="tn">${a.test}</span><span>${a.detail}</span></div>`).join('');
    const open = h.status === 'killed' ? 'open' : '';
    return `<div class="hyp ${h.status} ${open}" onclick="this.classList.toggle('open')">
      <div class="h"><span class="stamp">${stamp}</span>
        <span class="claim">${h.claim}</span>
        <span class="exp">${h.explained_share ? Math.round(h.explained_share*100)+'%' : ''}</span></div>
      <div class="body"><div class="mech">${h.mechanism}</div>${atk}</div></div>`;
  }).join('');

  // charts
  $('#waterfall').innerHTML = waterfall(d.drivers, d.analysis_kpi);
  $('#line').innerHTML = lineChart(d.series);

  // receipts
  $('#facts').innerHTML = `<tr><th>ID</th><th>Statement</th><th>Producer</th></tr>` +
    d.facts.map(f => `<tr data-fid="${f.id}"><td><b>${f.id}</b></td><td>${f.statement}</td>
      <td><span class="pill ${f.producer}">${f.producer}</span></td></tr>`).join('');
  $('#evidence').innerHTML = `<tr><th>ID</th><th>Src</th><th>Text</th></tr>` +
    d.evidence.map(e => `<tr data-fid="${e.id}"><td><b>${e.id}</b></td>
      <td><span class="pill retrieval">${e.source}</span></td><td>${e.text}</td></tr>`).join('');
  const fr = d.freshness || {};
  $('#prov').innerHTML = fr.source ? `<div class="mono-label" style="line-height:1.9">
    SOURCE <b style="color:var(--ink)">${fr.source}</b> · GRAIN ${fr.grain} · REFRESH ${fr.refresh} ·
    SLA ${fr.freshness_sla_hours}H · ${fr.governance}<br>LINEAGE ${(d.lineage||[]).join(' → ')}</div>` : '';
  const ver = d.verification;
  $('#verif').innerHTML = `<div class="redact" style="border-color:${ver.clean?'var(--ok)':'var(--danger)'};
    background:${ver.clean?'var(--lime-wash)':'var(--danger-wash)'};color:var(--ink)">
    <span class="lk">[CHECK]</span><span>Citations ${ver.citations_valid}/${ver.citations_found} resolve ·
    clean=${ver.clean}</span></div>`;

  // telemetry
  const t = d.telemetry;
  const numbers = 0;
  $('#metrics').innerHTML = `
    ${metric('LATENCY', t.total_latency_ms, 'MS', 0)}
    ${metric('LLM CALLS', t.llm_calls, '', 0)}
    ${metric('TOKENS', t.input_tokens + t.output_tokens, '', 0)}
    ${metric('EST. COST', t.estimated_cost_usd, '', 5, '$')}`;
  $$('#metrics .v').forEach(el => countUp(el));
  $('#statement').innerHTML = t.llm_calls === 0
    ? `The LLM computed <b>0 numbers</b>. It wasn't called — the deterministic core produced every figure across <b>${t.non_llm_calls}</b> tool steps.`
    : `The LLM computed <b>0 numbers</b>. It only phrased the memo (${t.llm_calls} call${t.llm_calls>1?'s':''}); <b>${t.non_llm_calls}</b> deterministic steps produced every figure.`;
  const by = t.work_by_producer; const total = Object.values(by).reduce((a, b) => a + b, 0);
  const colors = { deterministic:'#1b5fd9', statistical:'#4d7a00', retrieval:'#b5197a', rule:'#946200', llm:'#7c4dff' };
  $('#prodbar').innerHTML = Object.entries(by).map(([k, n]) =>
    `<div class="seg" style="flex:0;background:${colors[k]||'#666'}" data-flex="${n}">${k} ${n}</div>`).join('');
  requestAnimationFrame(() => $$('#prodbar .seg').forEach(s => s.style.flex = s.dataset.flex));
  $('#ledger').innerHTML = `<tr><th>Step</th><th>Producer</th><th>ms</th><th>Model</th><th>Tokens</th><th>Cost</th></tr>` +
    (d.telemetry_events || []).map(e => `<tr><td>${e.step}</td>
      <td><span class="pill ${e.kind}">${e.kind}</span></td><td>${e.latency_ms}</td>
      <td>${e.model || '—'}</td><td>${e.input_tokens + e.output_tokens || '—'}</td>
      <td>${e.cost_usd ? '$'+e.cost_usd.toFixed(5) : '—'}</td></tr>`).join('');

  // console coord readout
  const sig = d.facts[0];
  $('#coord').innerHTML = `Δ_KPI ${(d.series && signPct(d)) || '__'}<br>` +
    `ZSCORE ${zFrom(sig)}<br>CONF ${d.verdict.level.slice(0,4)}`;
  $('#renderpct').textContent = d.verdict.level === 'INSUFFICIENT' ? 'ABSTAIN' : 'RESOLVED';
}
function signPct(d){ const m=(d.facts[0]?.statement||'').match(/([+-]?\d+\.?\d*)%/); return m?m[1]+'%':'__'; }
function zFrom(f){ const m=(f?.statement||'').match(/z=(-?\d+\.?\d*)/); return m?m[1]:'__'; }

function metric(k, val, unit, dp, pre='') {
  return `<div class="metric"><div class="k">${k}</div>
    <div class="v" data-t="${val}" data-dp="${dp}" data-pre="${pre}" data-unit="${unit}">0</div></div>`;
}
function countUp(el) {
  const target = parseFloat(el.dataset.t) || 0, dp = +el.dataset.dp, pre = el.dataset.pre, unit = el.dataset.unit;
  const dur = 650, t0 = performance.now();
  (function f(now) {
    const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    const val = target * e;
    el.innerHTML = pre + (dp ? val.toFixed(dp) : Math.round(val).toLocaleString()) + (unit ? ` <small>${unit}</small>` : '');
    if (p < 1) requestAnimationFrame(f);
  })(t0);
}
function staggerIn(sel) {
  $$(sel).forEach((el, i) => {
    el.style.opacity = 0; el.style.transform = 'translateY(8px)';
    setTimeout(() => { el.style.transition = 'all .35s'; el.style.opacity = 1; el.style.transform = 'none'; }, 60 * i);
  });
}

// ---- SVG charts (hand-drawn, brutalist) ----
function waterfall(drivers, kpi) {
  if (!drivers || !drivers.length) return '<div class="chart"><div class="ct"><span>DRIVER ATTRIBUTION</span></div><svg viewBox="0 0 460 220"></svg></div>';
  const W = 460, H = 40 + drivers.length * 28, max = Math.max(...drivers.map(d => Math.abs(d.contribution))) || 1;
  const rows = drivers.map((d, i) => {
    const y = 20 + i * 28, w = Math.abs(d.contribution) / max * 250, neg = d.contribution < 0;
    const x = 150, col = neg ? '#7c4dff' : '#c8f135';
    return `<text x="8" y="${y + 12}" font-family="var(--mono)" font-size="10" fill="#0b0b0c">${d.group}</text>
      <rect x="${x}" y="${y}" width="${w}" height="18" fill="${col}" stroke="#0b0b0c" stroke-width="1"/>
      <text x="${x + w + 6}" y="${y + 13}" font-family="var(--mono)" font-size="9.5" fill="#5a5a5e">${fmt(d.contribution)} · ${Math.round(d.share*100)}%</text>`;
  }).join('');
  return `<div class="chart"><div class="ct"><span>DRIVER ATTRIBUTION</span><span>${kpi}</span></div>
    <svg viewBox="0 0 ${W} ${H}"><line x1="150" y1="10" x2="150" y2="${H - 10}" stroke="#0b0b0c" stroke-width="1"/>${rows}</svg></div>`;
}
function lineChart(s) {
  if (!s || !s.values.length) return '';
  const W = 460, H = 180, pad = 24, vals = s.values, n = vals.length;
  const mn = Math.min(...vals), mx = Math.max(...vals), rng = mx - mn || 1;
  const X = i => pad + i / (n - 1) * (W - pad * 2), Y = v => pad + (1 - (v - mn) / rng) * (H - pad * 2);
  const pts = vals.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const wi0 = s.dates.indexOf(s.window[0]), wi1 = s.dates.indexOf(s.window[1]);
  const wx0 = wi0 >= 0 ? X(wi0) : 0, wx1 = wi1 >= 0 ? X(wi1) : 0;
  return `<div class="chart"><div class="ct"><span>${s.kpi} — WINDOW SHADED</span><span>${s.window[0]} → ${s.window[1]}</span></div>
    <svg viewBox="0 0 ${W} ${H}">
      <rect x="${wx0}" y="${pad}" width="${Math.max(2,wx1-wx0)}" height="${H-pad*2}" fill="#ec1c4b" opacity="0.10"/>
      <polyline points="${pts}" fill="none" stroke="#7c4dff" stroke-width="1.6"/>
      <line x1="${pad}" y1="${H-pad}" x2="${W-pad}" y2="${H-pad}" stroke="#0b0b0c" stroke-width="1"/>
    </svg></div>`;
}
function fmt(n) { const a = Math.abs(n); return (n<0?'-':'') + (a >= 1000 ? (a/1000).toFixed(1)+'k' : a.toFixed(a<10?2:0)); }

// ---- console voxel canvas (rotating isometric cluster) ----
(function viz() {
  const cv = $('#viz'), ctx = cv.getContext('2d');
  let vox = [];
  for (let x = -2; x <= 2; x++) for (let z = -2; z <= 2; z++) {
    const h = Math.round(1 + Math.abs(Math.sin(x * 1.3) + Math.cos(z * 1.7)) * 3);
    for (let y = 0; y < h; y++) if (Math.random() > .12) vox.push([x, y, z]);
  }
  const accents = new Set(vox.filter(() => Math.random() < .12).map(v => v.join(',')));
  function resize() { const r = cv.parentElement.getBoundingClientRect(); cv.width = r.width * 2; cv.height = r.height * 2; }
  resize(); window.addEventListener('resize', resize);
  let a = 0, last = 0;
  function iso(x, y, z, ang) {
    const c = Math.cos(ang), s = Math.sin(ang), rx = x * c - z * s, rz = x * s + z * c;
    return [(rx - rz) * 26, (rx + rz) * 15 - y * 30];
  }
  function draw(now) {
    requestAnimationFrame(draw);
    if (now - last < 33) return; last = now;          // ~30fps
    a += 0.012; const w = cv.width, h = cv.height;
    ctx.clearRect(0, 0, w, h); ctx.save(); ctx.translate(w / 2, h / 2 + 60); ctx.scale(2, 2);
    const order = [...vox].sort((p, q) => (p[0]+p[2] - q[0]-q[2]) + (p[1]-q[1]) * .01);
    for (const [x, y, z] of order) {
      const [px, py] = iso(x, y, z, a); const S = 26, T = 15;
      const acc = accents.has([x, y, z].join(','));
      const top = acc ? (Math.random()<.5?'#c8f135':'#7c4dff') : '#d9d9d6';
      drawCube(ctx, px, py, S, T, top, acc);
    }
    ctx.restore();
  }
  function drawCube(ctx, px, py, S, T, top, acc) {
    // top rhombus
    ctx.beginPath(); ctx.moveTo(px, py - 30); ctx.lineTo(px + S, py - 30 + T);
    ctx.lineTo(px, py - 30 + 2*T); ctx.lineTo(px - S, py - 30 + T); ctx.closePath();
    ctx.fillStyle = top; ctx.fill(); ctx.strokeStyle = '#0b0b0c'; ctx.lineWidth = .5; ctx.stroke();
    // left face
    ctx.beginPath(); ctx.moveTo(px - S, py - 30 + T); ctx.lineTo(px, py - 30 + 2*T);
    ctx.lineTo(px, py + T); ctx.lineTo(px - S, py); ctx.closePath();
    ctx.fillStyle = acc ? shade(top,-30) : '#8c8c90'; ctx.fill(); ctx.stroke();
    // right face
    ctx.beginPath(); ctx.moveTo(px + S, py - 30 + T); ctx.lineTo(px, py - 30 + 2*T);
    ctx.lineTo(px, py + T); ctx.lineTo(px + S, py); ctx.closePath();
    ctx.fillStyle = acc ? shade(top,-55) : '#6a6a6e'; ctx.fill(); ctx.stroke();
  }
  function shade(hex, d) {
    const n = parseInt(hex.slice(1), 16); let r=(n>>16)+d, g=((n>>8)&255)+d, b=(n&255)+d;
    r=Math.max(0,Math.min(255,r)); g=Math.max(0,Math.min(255,g)); b=Math.max(0,Math.min(255,b));
    return `rgb(${r},${g},${b})`;
  }
  requestAnimationFrame(draw);
})();

// ---- console cursor coordinate readout (idle) ----
$('.render')?.addEventListener('mousemove', e => {
  if (STATE.last) return;
  const r = e.currentTarget.getBoundingClientRect();
  const x = ((e.clientX - r.left) / r.width * 180 - 90).toFixed(4);
  const y = ((e.clientY - r.top) / r.height * 180 - 90).toFixed(4);
  $('#coord').innerHTML = `X_${x}<br>Y_${y}<br>SCAN_ACTIVE`;
});
