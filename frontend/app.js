
const $ = (id) => document.getElementById(id);
let companies = [];

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}
function toast(msg) {
  $("toast").textContent = msg; $("toast").classList.add("show");
  setTimeout(() => $("toast").classList.remove("show"), 3000);
}
function renderRows() {
  const q = $("search").value.toLowerCase();
  $("companyRows").innerHTML = companies.filter(c => (c.name||"").toLowerCase().includes(q) || (c.code||"").toLowerCase().includes(q))
    .map(c => `<tr onclick="showCompany('${esc(c.code)}')">
      <td>${esc(c.rank ?? "—")}</td><td><b>${esc(c.name)}</b><br><small>${esc(c.code)}</small></td>
      <td>${fmt(c.environmental)}</td><td>${fmt(c.social)}</td><td>${fmt(c.governance)}</td>
      <td class="score">${fmt(c.score)}</td><td><span class="pill">${esc(c.risk)}</span></td>
      <td>${fmt(c.quality)}</td><td>${c.contradictions ?? 0}/${c.review_flags ?? 0}</td>
    </tr>`).join("") || `<tr><td colspan="9">No companies found.</td></tr>`;
}
function fmt(v){ return v == null ? "—" : Number(v).toFixed(2); }

async function load() {
  const data = await api("/api/summary");
  companies = data.companies || [];
  $("count").textContent = data.count ?? "—";
  $("avg").textContent = data.average_score == null ? "—" : `${data.average_score}/10`;
  $("top").textContent = data.best_company?.name || "—";
  renderRows();
  loadDownloads();
}
async function showCompany(code) {
  const d = await api(`/api/company/${encodeURIComponent(code)}`);
  const s = d.summary;
  $("detail").innerHTML = `<div class="detail">
    <h3>${esc(s.name)} <span class="pill">${esc(s.risk)}</span></h3>
    <p>Master ESG score <b>${fmt(s.score)}/10</b> • data quality ${fmt(s.quality)}/10</p>
    ${metric("Environmental",s.environmental)}${metric("Social",s.social)}${metric("Governance",s.governance)}
    <h3>Strengths</h3><p>${esc(s.strengths || "Not available")}</p>
    <h3>Weaknesses</h3><p>${esc(s.weaknesses || "Not available")}</p>
    <h3>Recommendations</h3><p>${esc(s.recommendations || "Not available")}</p>
    <p><b>Contradictions:</b> ${s.contradictions} &nbsp; <b>Review flags:</b> ${s.review_flags}</p>
    <p><a href="/api/outputs/esg_master_scores.csv">Master scores CSV</a> · <a href="/api/outputs/greenwashing_detection.csv">Greenwashing CSV</a> · <a href="/api/outputs/multi_agent_explanations.csv">Explainability CSV</a></p>
  </div>`;
}
function metric(name,val){return `<div><b>${name}</b> <span>${fmt(val)}/10</span><div class="bar"><i style="width:${Math.max(0,Math.min(100,(val||0)*10))}%"></i></div></div>`}
async function loadDownloads(){
  try {
    const d = await api("/api/download-status");
    $("downloads").innerHTML = `<p><b>${d.valid}</b> latest valid/skipped records • <b>${d.pending}</b> pending</p>` +
      (d.rows?.length ? `<div class="table-wrap"><table><thead><tr><th>Company</th><th>Status</th><th>Reason</th></tr></thead><tbody>${d.rows.map(r=>`<tr><td>${esc(r.company_code)}</td><td>${esc(r.status)}</td><td>${esc(r.reason)}</td></tr>`).join("")}</tbody></table></div>` : `<p>No downloader log yet.</p>`);
  } catch(e){ $("downloads").textContent = "Downloader status unavailable."; }
}
async function poll(){
  try{
    const s=await api("/api/run-status"); $("status").textContent=s.status;
    if(s.status==="running"){setTimeout(poll,1500)}
    else if(s.status==="completed"){toast("Pipeline completed."); await load();}
    else if(s.status==="failed"){toast(s.message); }
  }catch(e){}
}
$("refreshBtn").onclick=load;
$("search").oninput=renderRows;
$("runBtn").onclick=async()=>{
  $("runBtn").disabled=true; $("status").textContent="starting";
  try{await api("/api/run?download=true",{method:"POST"}); toast("Pipeline started."); poll();}
  catch(e){toast("Could not start pipeline.");}
  finally{setTimeout(()=>{$("runBtn").disabled=false},2500)}
};
load().catch(e=>toast("Could not load outputs. Run the pipeline first."));
