/* Talks to the FastAPI backend at /api/* (same origin, or set API_BASE below). */
const API_BASE = ""; // same-origin; set to "http://127.0.0.1:8000" if serving frontend separately

const el = sel => document.querySelector(sel);
const sidebarEl = el("#sidebar");
const chatScroll = el("#chatScroll");
const chatInner = el("#chatInner");
const inputEl = el("#msgInput");
const sendBtn = el("#sendBtn");
const bannerHost = el("#bannerHost");

let DOCS = [];
let currentDoc = null;
let sending = false;
const chatState = {};

const SUGGESTIONS = [
  {label:"What's the interest rate?", type:"ok"},
  {label:"Late payment penalty?", type:"ok"},
  {label:"Should I take this loan?", type:"bad"},
  {label:"Write me a poem about spring", type:"bad"},
];

async function loadDocuments(){
  const res = await fetch(`${API_BASE}/api/documents`);
  DOCS = await res.json();
  DOCS.forEach(d => chatState[d.id] = []);
  currentDoc = DOCS[0]?.id;
  renderAll();
}

function docById(id){ return DOCS.find(d=>d.id===id); }

function renderSidebar(){
  sidebarEl.innerHTML = `<div class="sidebar-label">Loan documents · vault</div>` +
    DOCS.map(d => {
      const active = d.id===currentDoc ? "active":"";
      return `<div class="doc-card ${active}" data-doc="${d.id}">
        <span class="flag">${d.flag}</span>
        <div class="bank">${d.bank}</div>
        <div class="meta">${d.country}</div>
      </div>`;
    }).join("") +
    `<div class="about-box">
      <b>Two security gates</b>
      <div class="rule"><span class="n">1</span><span>Scope guard blocks off-topic &amp; advice questions before retrieval.</span></div>
      <div class="rule"><span class="n">2</span><span>Grounding guard blocks any answer not backed by the actual contract text.</span></div>
    </div>`;
  sidebarEl.querySelectorAll(".doc-card").forEach(c => {
    c.addEventListener("click", () => {
      currentDoc = c.dataset.doc;
      sidebarEl.classList.remove("open");
      renderAll();
    });
  });
}

function renderBanner(){
  const d = docById(currentDoc);
  if(!d) return;
  bannerHost.innerHTML = `<div class="doc-banner">
    <div class="flag-big">${d.flag}</div>
    <div>
      <div class="title">${d.bank} — Personal Loan Terms</div>
      <div class="desc">scope locked to this document · retrieval-augmented, page-cited answers only</div>
    </div>
  </div>`;
}

function escapeHtml(s){
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function renderMessages(){
  const msgs = chatState[currentDoc] || [];
  chatInner.querySelectorAll(".msg-row, .pipeline, .empty-state").forEach(n=>n.remove());
  if(msgs.length===0){
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `<div class="icon">🔒</div>
      <p>Ask about <b style="color:var(--paper)">this contract only</b> — rate, fees, penalties, eligibility.
      Off-topic or advice questions are refused at the door. Every answer is cited to a page, or the agent says it isn't stated.</p>
      <div class="suggestions">${SUGGESTIONS.map(s=>`<button class="chip type-${s.type}" data-q="${s.label}">${s.label}</button>`).join("")}</div>`;
    chatInner.appendChild(empty);
    empty.querySelectorAll(".chip").forEach(c=>c.addEventListener("click", ()=>{ inputEl.value=c.dataset.q; sendMessage(); }));
    return;
  }
  msgs.forEach(m => chatInner.appendChild(renderMsgNode(m)));
}

function renderMsgNode(m){
  const row = document.createElement("div");
  if(m.role==="user"){
    row.className = "msg-row user";
    row.innerHTML = `<div class="bubble">${escapeHtml(m.text)}</div>`;
    return row;
  }
  row.className = "msg-row assistant";
  const wrap = document.createElement("div");
  wrap.className = "bubble-wrap";
  let bubbleClass = "bubble";
  let stampHtml = "";
  if(m.status==="refused"){ bubbleClass += " refused"; stampHtml = `<div class="stamp warn">⛔ out of scope</div>`; }
  if(m.status==="blocked"){ bubbleClass += " blocked"; stampHtml = `<div class="stamp warn">🛑 blocked — not grounded</div>`; }
  if(m.status==="grounded"){ bubbleClass += " grounded"; stampHtml = `<div class="stamp ok">✓ verified against contract</div>`; }

  let citesHtml = "";
  if(m.citations && m.citations.length){
    citesHtml = `<div class="cites">${[...new Set(m.citations)].map(p=>`<span class="cite-chip" data-page="${p}">p. ${p}</span>`).join("")}</div>`;
  }

  wrap.innerHTML = `<div class="${bubbleClass}">${escapeHtml(m.text).replace(/\n/g,"<br>")}</div>${stampHtml}${citesHtml}<div class="source-host"></div>`;
  row.appendChild(wrap);

  if(m.sources){
    const host = wrap.querySelector(".source-host");
    wrap.querySelectorAll(".cite-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const page = chip.dataset.page;
        const src = m.sources.find(s => String(s.page)===String(page));
        const existing = host.querySelector(".source-card");
        if(existing){ existing.remove(); if(existing.dataset.page===page) return; }
        if(!src) return;
        const card = document.createElement("div");
        card.className = "source-card";
        card.dataset.page = page;
        card.innerHTML = `<span class="pg">— page ${src.page} —</span>${escapeHtml(src.text)}`;
        host.appendChild(card);
      });
    });
  }
  return row;
}

function scrollToBottom(){ chatScroll.scrollTop = chatScroll.scrollHeight; }

function renderPipeline(stepIndex, blockedAt=null){
  const steps = ["Scope guard","Retrieve clauses","Draft answer","Grounding guard"];
  const existing = chatInner.querySelector(".pipeline");
  if(existing) existing.remove();
  const wrap = document.createElement("div");
  wrap.className = "pipeline";
  wrap.innerHTML = steps.map((s,i)=>{
    let cls = "pstep";
    if(blockedAt!==null && i===blockedAt) cls += " blocked";
    else if(i<stepIndex || (blockedAt!==null && i<blockedAt)) cls += " done";
    else if(i===stepIndex && blockedAt===null) cls += " active";
    return `<div class="${cls}"><span class="dot"></span>${s}</div>` + (i<3?`<div class="pline"></div>`:"");
  }).join("");
  chatInner.appendChild(wrap);
  scrollToBottom();
}

async function sendMessage(){
  const text = inputEl.value.trim();
  if(!text || sending || !currentDoc) return;
  sending = true;
  sendBtn.disabled = true;
  inputEl.value = "";
  inputEl.style.height = "auto";

  chatState[currentDoc].push({role:"user", text});
  renderMessages();
  scrollToBottom();
  renderPipeline(1); // we can't see the backend's internal steps live over a single POST,
                      // so show a generic "working" sweep while we await the response.

  try{
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: text, doc_id: currentDoc}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({detail:"request failed"}));
      throw new Error(err.detail || "request failed");
    }
    const data = await res.json();

    if(data.status === "refused"){
      renderPipeline(0, 0);
      await sleep(200);
    } else if(data.status === "blocked"){
      renderPipeline(3, 3);
      await sleep(200);
    } else {
      renderPipeline(4);
      await sleep(150);
    }

    chatState[currentDoc].push({
      role: "assistant",
      status: data.status,
      text: data.text,
      citations: data.citations,
      sources: data.sources,
    });
    renderMessages();
    scrollToBottom();
  } catch(err){
    chatState[currentDoc].push({role:"assistant", status:"blocked", text:`Error: ${err.message}`});
    renderMessages();
  } finally {
    const p = chatInner.querySelector(".pipeline");
    if(p) p.remove();
    sending = false;
    sendBtn.disabled = false;
  }
}

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

function renderAll(){
  renderSidebar();
  renderBanner();
  renderMessages();
  scrollToBottom();
}

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
});
inputEl.addEventListener("keydown", e => {
  if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); sendMessage(); }
});
sendBtn.addEventListener("click", sendMessage);
el("#menuBtn").addEventListener("click", () => sidebarEl.classList.toggle("open"));

loadDocuments();
