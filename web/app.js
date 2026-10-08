"use strict";
/* SupportDesk front end: plain JavaScript, talks to the JSON API under /api. */

// ----------------------------------------------------------------- icons
const P = {
  inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  chart: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  search: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  edit: '<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>',
  play: '<polygon points="5 3 19 12 5 21 5 3"/>',
  refresh: '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
  alert: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  dollar: '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  mail: '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
  lifebuoy: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="4.93" y1="4.93" x2="9.17" y2="9.17"/><line x1="14.83" y1="14.83" x2="19.07" y2="19.07"/><line x1="14.83" y1="9.17" x2="19.07" y2="4.93"/><line x1="4.93" y1="19.07" x2="9.17" y2="14.83"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  trend: '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
};
Object.assign(P, {
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  review: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><polyline points="9 14 11 16 15 12"/>',
});
const svg = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${P[name] || ""}</svg>`;
const ico = (name) => `<span class="ico">${svg(name)}</span>`;
document.querySelectorAll("[data-icon]").forEach((el) => { el.innerHTML = svg(el.dataset.icon); });
document.getElementById("brand-mark").innerHTML = ico("lifebuoy");

// --------------------------------------------------------------- helpers
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => "$" + Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function fmtTime(s) {                      // "2026-09-30 10:00" -> "Sep 30, 10:00"
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(s || "");
  return m ? `${MONTHS[+m[2] - 1]} ${+m[3]}, ${m[4]}:${m[5]}` : (s || "");
}
function fmtDate(s) {                      // "2026-09-30" -> "Sep 30, 2026"
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || "");
  return m ? `${MONTHS[+m[2] - 1]} ${+m[3]}, ${m[1]}` : (s || "-");
}
const initials = (name) => (name || "?").split(/[\s._@-]+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
const PALETTE = [["#e0e7ff", "#3730a3"], ["#dcfce7", "#166534"], ["#fde68a", "#92400e"], ["#fce7f3", "#9d174d"], ["#cffafe", "#155e75"], ["#ede9fe", "#5b21b6"], ["#fee2e2", "#991b1b"]];
function avatar(name) {
  let h = 0; for (const c of name || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const [bg, fg] = PALETTE[h % PALETTE.length];
  return `<div class="avatar" style="background:${bg};color:${fg}">${esc(initials(name))}</div>`;
}
const chip = (key, label) => `<span class="chip chip-${esc(key)}">${esc(label)}</span>`;
const reasonLabel = (r) => (r || "").replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

function toast(message, type = "ok") {
  const el = document.createElement("div");
  el.className = "toast" + (type === "error" ? " error" : "");
  el.textContent = message;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), type === "error" ? 6000 : 3200);
}

async function api(path, options = {}) {
  const res = await fetch("/api" + path, {
    method: options.method || "GET",
    headers: { "Content-Type": "application/json" },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) { /* keep status text */ }
    throw new Error(msg);
  }
  return res.json();
}

// ----------------------------------------------------------------- state
const state = { view: "inbox", tickets: [], filter: "all", search: "", selectedId: null, detail: null,
                busy: new Set(), editing: false, stats: null, queue: [], audit: [], processingNext: false };

state.review = { counts: { to_review: 0, correct: 0, incorrect: 0, unsure: 0, all: 0 }, items: [], filter: "to_review",
                 selectedId: null, detail: null, form: false, busy: false };
const FILTERS = [["all", "All"], ["new", "New"], ["auto_resolved", "Auto-resolved"], ["escalated", "Escalated"],
                 ["waiting", "Waiting for human"], ["human_resolved", "Human resolved"]];

// ------------------------------------------------------------- inbox list
function renderFilters() {
  const counts = { all: state.tickets.length };
  for (const t of state.tickets) counts[t.status_key] = (counts[t.status_key] || 0) + 1;
  $("#filters").innerHTML = FILTERS.map(([k, label]) =>
    `<button class="filter ${state.filter === k ? "active" : ""}" data-action="filter" data-key="${k}">${label}<span class="n">${counts[k] || 0}</span></button>`).join("");
}

function visibleTickets() {
  const q = state.search.trim().toLowerCase();
  return state.tickets.filter((t) =>
    (state.filter === "all" || t.status_key === state.filter) &&
    (!q || `${t.customer_name} ${t.customer_email} ${t.subject} ${t.snippet} ${t.ticket_id}`.toLowerCase().includes(q)));
}

function renderList() {
  const list = visibleTickets();
  $("#inbox-count").textContent = `(${list.length})`;
  renderFilters();
  $("#ticket-list").innerHTML = list.length ? list.map((t) => `
    <div class="item ${t.ticket_id === state.selectedId ? "active" : ""}" data-action="select" data-id="${t.ticket_id}">
      ${avatar(t.customer_name)}
      <div class="item-body">
        <div class="item-top"><span class="item-name">${esc(t.customer_name)}</span><span class="item-time">${esc(fmtTime(t.created_at))}</span></div>
        <div class="item-subject">${esc(t.snippet)}</div>
        <div class="item-foot">${chip(t.status_key, t.status_label)}${t.priority === "high" && t.processed ? '<span class="tag tag-high">HIGH</span>' : ""}<span class="muted" style="font-size:11.5px">#${t.ticket_id}</span></div>
      </div>
    </div>`).join("") : '<div class="empty-list">No tickets match.</div>';
}

// ------------------------------------------------------------ ticket page
function timelineHtml(items) {
  const dotIcon = { ok: "check", warn: "alert", stop: "x", info: "info" };
  return `<ul class="timeline">${items.map((it) => `
    <li class="tl"><span class="tl-dot ${it.kind}">${ico(dotIcon[it.kind] || "info")}</span>
      <div class="tl-title"><span>${esc(it.title)}</span><span class="tl-time">${esc(it.time)}</span></div>
      ${it.detail ? `<div class="tl-detail">${esc(it.detail)}</div>` : ""}</li>`).join("")}</ul>`;
}

function workingHtml() {
  return `<div class="card card-pad"><div class="working-title"><span class="spinner" style="border-color:rgba(79,70,229,.25);border-top-color:#4f46e5"></span>The agent is working on this ticket...</div>
    <div class="working" style="margin-top:14px"><div class="line" style="width:86%"></div><div class="line" style="width:64%"></div><div class="line" style="width:75%"></div></div>
    <p class="muted" style="margin-top:12px;font-size:12.5px">Screening, understanding the request, calling tools, checking the policy and verifying the reply. This can take 10-30 seconds.</p></div>`;
}

function replyCard(d) {
  const r = d.result, waiting = r.status === "waiting_for_human";
  const hasReply = !!(r.reply && r.reply.trim());
  const editing = waiting && (state.editing || !hasReply);
  let title = "Agent reply", sub = "Sent to the customer";
  if (waiting) { title = hasReply ? "Suggested reply" : "Reply needed"; sub = "Waiting for your approval"; }
  else if (r.status === "human_approved" || r.status === "human_rejected") { sub = "Sent after human review"; }
  else if (r.status === "asked_question") { title = "Agent question"; sub = "Sent to the customer"; }

  let body;
  if (editing) body = `<textarea id="reply-edit" class="reply-edit" placeholder="Write the reply to the customer...">${esc(r.reply || "")}</textarea>`;
  else if (hasReply) body = `<div class="bubble reply">${esc(r.reply)}</div>`;
  else body = `<div class="bubble dashed">No reply was sent for this ticket.</div>`;

  let actions = "";
  if (waiting) {
    const busy = state.busy.has(d.ticket.ticket_id);
    const approveLabel = r.pending_action ? "Approve refund &amp; send reply" : "Send reply";
    actions = `<div class="action-bar">
      <button class="btn btn-green" data-action="approve" ${busy ? "disabled" : ""}>${ico("check")}${approveLabel}</button>
      ${hasReply ? `<button class="btn btn-ghost" data-action="toggle-edit">${ico("edit")}${editing ? "Cancel edit" : "Edit reply"}</button>` : ""}
      <button class="btn btn-danger" data-action="reject" ${busy ? "disabled" : ""}>${ico("x")}Reject</button></div>`;
  }
  return `<div class="card card-pad">
    <div class="card-head"><div><div class="label">${title}</div><div class="muted" style="font-size:12.5px;margin-top:2px">${sub}</div></div><span class="tag tag-sim" title="No real email is sent">SIMULATED SEND</span></div>
    ${body}${actions}</div>`;
}

function escalationAlert(d) {
  const r = d.result;
  if (r.status === "human_approved" || r.status === "human_rejected") {
    const verb = r.status === "human_approved" ? "approved" : "rejected";
    return `<div class="alert done">${ico("shield")}<div><h3>Handled by a human</h3><p>This ticket was ${verb} by <b>${esc(r.handled_by)}</b> and the reply was sent (simulated). Everything is in the step timeline below.</p></div></div>`;
  }
  if (r.status !== "waiting_for_human") return "";
  const high = r.priority === "high";
  const pa = r.pending_action;
  const action = pa ? `<div class="action-box">${ico("dollar")}<div><div class="label">Pending action</div><div><span class="big">${money(pa.amount)}</span> refund &middot; order #${pa.order_id} &middot; ${esc(pa.item)}</div></div></div>` : "";
  return `<div class="alert ${high ? "stop" : "warn"}">${ico("alert")}<div style="flex:1">
    <h3>${pa ? "Waiting for human approval" : "Escalated to a human"} ${high ? '<span class="tag tag-high">HIGH PRIORITY</span>' : ""}<span class="reason-tag">${esc(reasonLabel(r.reason))}</span></h3>
    <p>${esc(r.summary || "")}</p>${action}</div></div>`;
}

function renderDetail() {
  const root = $("#detail");
  if (!state.selectedId) {
    root.innerHTML = `<div class="empty-state"><div class="art">${ico("mail")}</div><h3>Select a ticket</h3><p>Pick a ticket on the left to see the customer message,<br>the agent's reply and every step the agent took.</p></div>`;
    return;
  }
  const d = state.detail;
  if (!d || d.ticket.ticket_id !== state.selectedId) { root.innerHTML = `<div class="detail">${workingHtml()}</div>`; return; }
  const t = d.ticket, busy = state.busy.has(t.ticket_id), processed = !!d.result;

  const processBtn = `<button class="btn ${processed ? "btn-ghost" : "btn-primary"}" data-action="process" ${busy ? "disabled" : ""}>
      ${busy ? '<span class="spinner"></span>Working...' : ico(processed ? "refresh" : "play") + (processed ? "Run again" : "Process with agent")}</button>`;

  let html = `<div class="detail">
    <div class="detail-head">
      <div><h2>${esc(t.subject)}</h2>
        <div class="detail-meta"><span>From <b>${esc(t.customer_name)}</b> &lt;${esc(t.customer_email)}&gt;</span><span>${esc(fmtTime(t.created_at))}</span><span>Ticket #${t.ticket_id}</span></div></div>
      <div class="detail-actions">${chip(d.status_key, d.status_label)}${processBtn}</div>
    </div>
    <div class="card card-pad"><div class="label">Customer message</div><div class="bubble">${esc(t.body)}</div></div>`;

  if (busy) html += workingHtml();
  else if (processed) {
    html += escalationAlert(d) + replyCard(d);
    html += `<div class="card card-pad"><div class="card-head"><div class="label">What the agent did</div><span class="muted" style="font-size:12.5px">${d.timeline.length} steps${d.result.duration_ms ? " &middot; " + (d.result.duration_ms / 1000).toFixed(1) + "s" : ""}</span></div>${timelineHtml(d.timeline)}</div>`;
  } else {
    html += `<div class="card card-pad" style="text-align:center;padding:34px 20px"><div class="art" style="width:56px;height:56px;margin:0 auto 12px;border-radius:16px;background:var(--primary-soft);color:var(--primary);display:grid;place-items:center">${ico("zap")}</div>
      <h3>This ticket has not been processed yet</h3><p class="muted" style="margin:6px 0 16px">The agent will screen it, work out what the customer wants, use the store tools and check the policy.</p>
      <button class="btn btn-primary" data-action="process">${ico("play")}Process with agent</button></div>`;
  }
  root.innerHTML = html + "</div>";
}

function renderSide() {
  const root = $("#side"), d = state.detail;
  if (!state.selectedId || !d || d.ticket.ticket_id !== state.selectedId) { root.innerHTML = ""; return; }
  const c = d.customer, o = d.order, s = d.shipment;
  let html = `<div class="side-card"><div class="label" style="margin-bottom:12px">Customer</div>
    <div class="person">${avatar(c.name)}<div style="min-width:0"><div class="person-name">${esc(c.name)}</div><div class="person-mail">${esc(c.email).replace("@", "@<wbr>")}</div></div></div>
    <div class="rows">
      <div class="row"><span>Account</span><span>${c.known ? "Known customer" : "Unknown sender"}</span></div>
      ${c.known ? `<div class="row"><span>Orders</span><span>${c.orders.length}</span></div><div class="row"><span>Address</span><span>${esc(c.address)}</span></div>` : ""}
    </div></div>`;

  if (o) {
    html += `<div class="side-card"><div class="label">Order #${o.order_id}</div>
      <div class="order-top"><div><div class="order-amount">${money(o.amount)}</div><div class="muted">${esc(o.item)}${o.quantity > 1 ? " &times; " + o.quantity : ""}</div></div>
      <span class="status-pill sp-${esc(o.status)}">${esc(o.status)}</span></div>
      <div class="rows">
        <div class="row"><span>Ordered</span><span>${fmtDate(o.order_date)}</span></div>
        <div class="row"><span>Shipped</span><span>${fmtDate(o.shipped_date)}</span></div>
        <div class="row"><span>Delivered</span><span>${fmtDate(o.delivered_date)}</span></div>
        <div class="row"><span>Ship to</span><span>${esc(o.shipping_address)}</span></div>
        <div class="row"><span>Refunded</span><span>${o.refunded ? '<span style="color:var(--green)">Yes (simulated)</span>' : "No"}</span></div>
      </div></div>`;
    if (s && s.shipped) {
      html += `<div class="side-card"><div class="label" style="display:flex;gap:8px;align-items:center">${ico("box")}Shipment</div>
        <div class="rows"><div class="row"><span>Carrier</span><span>${esc(s.carrier)}</span></div>
        <div class="row"><span>Status</span><span style="text-transform:capitalize">${esc((s.status || "").replace(/_/g, " "))}</span></div>
        <div class="row"><span>Tracking</span><span>${esc(s.tracking_number)}</span></div>
        <div class="row"><span>${s.status === "delivered" ? "Delivered" : "Expected"}</span><span>${fmtDate(s.status === "delivered" ? s.delivered_date : s.expected_date)}</span></div></div></div>`;
    }
  } else if (d.order_note) {
    html += `<div class="note">${esc(d.order_note)} No order details are shown.</div>`;
  }
  if (c.known && c.orders.length > 1) {
    html += `<div class="side-card"><div class="label">All orders (${c.orders.length})</div><div class="mini-orders">` +
      c.orders.map((x) => `<div class="mini-order"><span>#${x.order_id} ${esc(x.item)}</span><b>${money(x.amount)}</b></div>`).join("") + `</div></div>`;
  }
  root.innerHTML = html;
}

// ------------------------------------------------------------ queue page
function renderQueue() {
  const root = $("#view-queue");
  const q = state.queue;
  const cards = q.map((t) => {
    const hasReply = !!t.suggested_reply;
    return `<div class="card q-card">
      <div class="q-top">${avatar(t.customer_name)}<div class="grow"><b>${esc(t.customer_name)}</b> <span class="muted">&middot; #${t.ticket_id} &middot; ${esc(fmtTime(t.created_at))}</span><div style="margin-top:5px;display:flex;gap:8px;align-items:center">${chip(t.status_key, t.status_label)}${t.priority === "high" ? '<span class="tag tag-high">HIGH</span>' : ""}<span class="muted" style="font-size:12.5px">${esc(reasonLabel(t.reason))}</span></div></div>
        <button class="btn btn-ghost btn-sm" data-action="open" data-id="${t.ticket_id}">Open ticket</button></div>
      <div class="q-summary">${esc(t.summary || "")}</div>
      ${hasReply ? `<div class="q-reply"><div class="label" style="margin-bottom:6px">Suggested reply</div><div class="bubble reply" style="margin-top:0">${esc(t.suggested_reply)}</div></div>` : ""}
      <div class="action-bar">
        ${hasReply ? `<button class="btn btn-green" data-action="q-approve" data-id="${t.ticket_id}">${ico("check")}Approve${t.summary && /refund/i.test(t.summary) && t.status_key === "waiting" ? " refund" : ""} &amp; send</button>` : `<button class="btn btn-primary" data-action="open" data-id="${t.ticket_id}">${ico("edit")}Write a reply</button>`}
        <button class="btn btn-danger" data-action="q-reject" data-id="${t.ticket_id}">${ico("x")}Reject</button>
      </div></div>`;
  }).join("");
  root.innerHTML = `<div class="page-inner"><h1 class="page-title">Human queue</h1>
    <p class="page-sub">Tickets the agent could not (or should not) handle alone. High priority first. Refunds happen only after you approve.</p>
    ${q.length ? `<div class="queue-list">${cards}</div>` : `<div class="card empty-card"><div class="art" style="width:64px;height:64px;margin:0 auto 12px;border-radius:18px;background:var(--green-soft);color:var(--green);display:grid;place-items:center">${ico("check")}</div><h3 style="color:var(--text)">The queue is empty</h3><p>Nothing is waiting for a human right now.</p></div>`}</div>`;
}

// -------------------------------------------------------- dashboard page
function donut(s) {
  const parts = [[s.auto_resolved, "#16a34a", "Auto-resolved"], [s.asked_question, "#2563eb", "Asked a question"], [s.escalated, "#d97706", "Escalated to a human"]];
  const total = s.processed, R = 54, C = 2 * Math.PI * R;
  let offset = 0, arcs = "";
  if (total) for (const [n, color] of parts) {
    if (!n) continue;
    const len = (n / total) * C;
    arcs += `<circle cx="70" cy="70" r="${R}" fill="none" stroke="${color}" stroke-width="16" stroke-dasharray="${len} ${C - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 70 70)"/>`;
    offset += len;
  }
  const svgHtml = `<svg class="donut" viewBox="0 0 140 140"><circle cx="70" cy="70" r="${R}" fill="none" stroke="#eef1f6" stroke-width="16"/>${arcs}
    <text x="70" y="70" text-anchor="middle" font-size="21" font-weight="800" fill="#0f172a">${s.auto_resolved_pct}%</text>
    <text x="70" y="87" text-anchor="middle" font-size="9.5" font-weight="600" fill="#64748b">auto-resolved</text></svg>`;
  const legend = parts.map(([n, color, label]) => `<div><i style="background:${color}"></i>${label}<b>${n}</b></div>`).join("");
  return `<div class="donut-wrap">${svgHtml}<div class="legend">${legend}</div></div>`;
}

function reviewPanel(s) {
  const v = s.review;
  if (!v || !v.ai_resolved) return "";
  const pct = (n) => (v.ai_resolved ? (100 * n) / v.ai_resolved : 0);
  const reasons = v.reasons.length ? `<p class="hint" style="margin-top:12px">Incorrect because: ${v.reasons.map((r) => esc(r.text) + " (" + r.count + ")").join(", ")}</p>` : "";
  return `<div class="card val-card"><div class="card-head"><div><h3 style="font-size:15px">Human validation of AI-resolved tickets</h3>
      <span class="muted" style="font-size:12.5px">A person checked the tickets that the AI resolved</span></div><a class="btn btn-soft btn-sm" data-action="goto-review">Open Review AI</a></div>
    <div class="val-row"><div class="val-num"><b>${v.reviewed} of ${v.ai_resolved}</b><span>reviewed</span></div>
      <div class="val-num"><b style="color:var(--green)">${v.agreement_pct}%</b><span>reviewer agrees (correct &divide; correct + incorrect)</span></div>
      <div class="val-num"><b style="color:var(--red)">${v.incorrect}</b><span>marked incorrect</span></div>
      <div class="val-num"><b style="color:var(--amber)">${v.unsure}</b><span>not sure</span></div>
      <div class="val-bar"><div class="bar"><i style="width:${pct(v.correct)}%;background:var(--green)"></i><i style="width:${pct(v.incorrect)}%;background:var(--red)"></i><i style="width:${pct(v.unsure)}%;background:var(--amber)"></i></div>
        <p class="hint">Green: correct. Red: incorrect. Amber: not sure. Grey: not reviewed yet (${v.unreviewed}).</p></div></div>${reasons}</div>`;
}

function renderDashboard() {
  const root = $("#view-dashboard"), s = state.stats;
  if (!s) { root.innerHTML = ""; return; }
  const metric = (icon, bg, fg, value, label, note = "") => `<div class="card metric"><div class="m-ico" style="background:${bg};color:${fg}">${ico(icon)}</div>
      <div class="m-value">${value}</div><div class="m-label">${label}</div>${note ? `<div class="m-note">${note}</div>` : ""}</div>`;
  if (!s.processed) {
    root.innerHTML = `<div class="page-inner"><h1 class="page-title">Dashboard</h1><p class="page-sub">Live numbers from the database.</p>
      <div class="card empty-card"><h3 style="color:var(--text)">No tickets processed yet</h3><p>Open the inbox and run the agent on a few tickets. The numbers appear here.</p></div></div>`;
    return;
  }
  const max = Math.max(1, ...s.escalation_reasons.map((r) => r.count));
  const bars = s.escalation_reasons.length ? s.escalation_reasons.map((r) => `<div class="bar-row"><div class="bar-name" title="${esc(reasonLabel(r.reason))}">${esc(reasonLabel(r.reason))}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(r.count / max) * 100}%"></div></div><div class="bar-num">${r.count}</div></div>`).join("") : '<p class="muted" style="margin-top:14px">No escalations yet.</p>';
  const rows = state.audit.map((a) => `<tr><td style="white-space:nowrap;color:var(--muted)">${esc((a.created_at || "").slice(11))}</td>
      <td><a class="link" data-action="open" data-id="${a.ticket_id}">#${a.ticket_id}</a></td>
      <td><span class="dot ${a.kind}"></span><b style="font-weight:600">${esc(a.title)}</b>${a.detail ? `<div class="muted" style="font-size:12.5px;margin-left:16px">${esc(a.detail)}</div>` : ""}</td></tr>`).join("");
  root.innerHTML = `<div class="page-inner"><h1 class="page-title">Dashboard</h1>
    <p class="page-sub">Live numbers from the database &middot; ${s.processed} of ${s.total_tickets} tickets processed so far</p>
    <div class="metrics">
      ${metric("trend", "var(--green-soft)", "var(--green)", s.auto_resolved_pct + "%", "Auto-resolved", `${s.auto_resolved} of ${s.processed} processed`)}
      ${metric("users", "var(--amber-soft)", "var(--amber)", s.escalated, "Escalations", `${s.waiting_for_human} waiting &middot; ${s.high_priority_waiting} high priority`)}
      ${metric("mail", "var(--blue-soft)", "var(--blue)", s.processed, "Tickets processed", `${s.new} still New`)}
      ${metric("clock", "var(--primary-soft)", "var(--primary)", s.avg_handling_seconds + "s", "Avg handling time", "agent processing time per ticket")}
      ${metric("dollar", "var(--green-soft)", "var(--green)", money(s.refund_total), "Refunds (simulated)", `${s.refund_count} refund${s.refund_count === 1 ? "" : "s"} issued`)}
      ${metric("zap", "var(--slate-soft)", "var(--slate)", s.estimated_minutes_saved + " min", "Est. agent time saved", `estimate: ${s.minutes_per_ticket_assumption} min per auto-resolved ticket`)}
    </div>
    <div class="charts">
      <div class="card chart-card"><h3>Outcomes</h3><span class="muted" style="font-size:12.5px">What happened to the ${s.processed} processed tickets</span>${donut(s)}</div>
      <div class="card chart-card"><h3>Escalations by reason</h3><span class="muted" style="font-size:12.5px">Why tickets were handed to a human</span><div class="bars">${bars}</div></div>
    </div>
    ${reviewPanel(s)}
    <div class="card table-card"><h3>Audit trail <span class="muted" style="font-size:12.5px;font-weight:500">&middot; latest ${state.audit.length} events</span></h3>
      <table><thead><tr><th style="width:110px">Time</th><th style="width:90px">Ticket</th><th>Event</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="footnote"><b>Auto-resolved %</b> = tickets the agent fully handled &divide; tickets processed. A ticket where the agent only asked a question is not counted as resolved.
      The time-saved figure is an estimate that assumes a human needs ${s.minutes_per_ticket_assumption} minutes per ticket (the brief says 5-10). Refunds and emails are simulated.</p></div>`;
}

// ---------------------------------------------------------------- actions
async function loadTickets() { state.tickets = await api("/tickets"); }
async function loadQueue() {
  state.queue = await api("/queue");
  const n = state.queue.length, b = $("#queue-badge");
  b.textContent = n; b.hidden = n === 0;
}
async function loadDetail(id) { state.detail = await api("/tickets/" + id); }

async function refreshAll() {
  await Promise.all([loadTickets(), loadQueue()]);
  if (state.selectedId) await loadDetail(state.selectedId);
  if (state.view === "dashboard") await loadDashboard();
  await loadReviewQueue();
  renderAll();
}
async function loadDashboard() { [state.stats, state.audit] = await Promise.all([api("/stats"), api("/audit?limit=25")]); }

function renderAll() { renderList(); renderDetail(); renderSide(); if (state.view === "review") renderReview(); if (state.view === "queue") renderQueue(); if (state.view === "dashboard") renderDashboard(); }

async function selectTicket(id) {
  state.selectedId = id; state.editing = false; state.detail = null;
  history.replaceState(null, "", "#t" + id);
  renderList(); renderDetail(); renderSide();
  try { await loadDetail(id); } catch (e) { toast(e.message, "error"); }
  renderDetail(); renderSide();
}

function showView(view) {
  state.view = view;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
  for (const v of ["inbox", "review", "queue", "dashboard"]) $("#view-" + v).hidden = v !== view;
  if (view === "review") openReview();
  if (view === "queue") loadQueue().then(renderQueue);
  if (view === "dashboard") loadDashboard().then(renderDashboard).catch((e) => toast(e.message, "error"));
}

async function runWithBusy(id, fn, okMessage) {
  state.busy.add(id); renderDetail();
  try { await fn(); if (okMessage) toast(okMessage); }
  catch (e) { toast(e.message, "error"); }
  finally { state.busy.delete(id); state.editing = false; await refreshAll(); }
}

const processTicket = (id) => runWithBusy(id, async () => { state.detail = await api(`/tickets/${id}/process`, { method: "POST" }); }, `Ticket #${id} processed`);

function approveTicket(id) {
  const ta = $("#reply-edit");
  const reply = ta ? ta.value.trim() : null;
  if (ta && !reply) { toast("Please write a reply first.", "error"); return; }
  return runWithBusy(id, async () => { state.detail = await api(`/tickets/${id}/approve`, { method: "POST", body: { reply, by: "human_agent" } }); },
                     "Approved. Refund and reply done (simulated).");
}
const rejectTicket = (id) => runWithBusy(id, async () => { state.detail = await api(`/tickets/${id}/reject`, { method: "POST", body: { by: "human_agent" } }); }, "Ticket rejected. Reply sent (simulated).");

async function processNext() {
  if (state.processingNext) return;
  state.processingNext = true;
  const btn = $("#btn-process-next"); const html = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>Working...';
  try { const out = await api("/process_next?n=5", { method: "POST" }); toast(out.processed.length ? `Processed ${out.processed.length} tickets` : "No new tickets left"); }
  catch (e) { toast(e.message, "error"); }
  finally { btn.disabled = false; btn.innerHTML = html; state.processingNext = false; await refreshAll(); }
}


// ------------------------------------------------------------- Review AI
const REVIEW_FILTERS = [["to_review", "To review"], ["correct", "Correct"], ["incorrect", "Incorrect"], ["unsure", "Not sure"], ["all", "All"]];
const REVIEW_CHIP = { to_review: ["new", "To review"], correct: ["auto_resolved", "Correct"], incorrect: ["escalated", "Incorrect"], unsure: ["waiting", "Not sure"] };

async function loadReviewQueue() {
  const r = state.review;
  const q = await api("/review/queue?filter=" + r.filter);
  r.counts = q.counts; r.items = q.items;
  const b = $("#review-badge");
  b.textContent = q.counts.to_review; b.hidden = q.counts.to_review === 0;
}

async function openReview() {
  const r = state.review;
  try { await loadReviewQueue(); } catch (e) { toast(e.message, "error"); }
  if (!r.items.some((i) => i.ticket_id === r.selectedId)) r.selectedId = r.items.length ? r.items[0].ticket_id : null;
  r.detail = null; r.form = false;
  renderReview();
  if (r.selectedId) await selectReview(r.selectedId);
}

async function selectReview(id) {
  const r = state.review;
  r.selectedId = id; r.form = false; r.detail = null;
  renderReview();
  try { r.detail = await api("/review/" + id); } catch (e) { toast(e.message, "error"); }
  renderReview();
  const el = $(`#view-review .item[data-id="${id}"]`);
  if (el) el.scrollIntoView({ block: "nearest" });
}

function reviewListHtml() {
  const r = state.review, c = r.counts;
  const done = c.correct + c.incorrect + c.unsure, pct = c.all ? Math.round((100 * done) / c.all) : 0;
  const filters = REVIEW_FILTERS.map(([k, label]) => `<button class="filter ${r.filter === k ? "active" : ""}" data-action="review-filter" data-key="${k}">${label}<span class="n">${c[k] ?? 0}</span></button>`).join("");
  const items = r.items.length ? r.items.map((t) => {
    const [ck, cl] = REVIEW_CHIP[t.state];
    return `<div class="item ${t.ticket_id === r.selectedId ? "active" : ""}" data-action="review-select" data-id="${t.ticket_id}">
      ${avatar(t.customer_name)}<div class="item-body">
      <div class="item-top"><span class="item-name">${esc(t.customer_name)}</span><span class="item-time">#${t.ticket_id}</span></div>
      <div class="item-subject">${esc(t.snippet)}</div>
      <div class="item-foot">${chip(ck, cl)}${t.outdated ? '<span class="tag tag-sim">OUTDATED</span>' : ""}${t.kind === "question" ? '<span class="muted" style="font-size:11.5px">asked a question</span>' : ""}</div></div></div>`;
  }).join("") : `<div class="empty-list">${c.all ? "Nothing in this list." : "No AI-resolved tickets yet.<br>Process some tickets in the Inbox first."}</div>`;
  return `<div class="col-head"><div class="col-title">AI-resolved tickets</div>
      <button class="btn btn-soft btn-sm" data-action="review-process" title="Run the agent on the next 5 New tickets">${ico("zap")}Process 5 more</button></div>
    <div class="rv-progress"><p><b>${done}</b> of <b>${c.all}</b> reviewed</p><div class="bar"><i style="width:${pct}%"></i></div></div>
    <div class="filters">${filters}</div><div class="list">${items}</div>`;
}

function reviewMainHtml() {
  const r = state.review, d = r.detail;
  if (!r.selectedId) return `<div class="empty-state"><div class="art">${ico("review")}</div><h3>Nothing to review</h3><p>Tickets that the AI resolved appear here, so you can check them yourself.</p></div>`;
  if (!d || d.ticket.ticket_id !== r.selectedId) return `<div class="rv-scroll"><div class="rv-grid"><div class="card card-pad" style="grid-column:1/-1">${workingHtml()}</div></div></div>`;
  const t = d.ticket, ev = d.evidence, res = d.result;

  const facts = ev.facts.length ? `<table class="facts"><thead><tr><th>Fact in the reply</th><th>Value</th><th>Found in</th></tr></thead><tbody>` +
      ev.facts.map((f) => `<tr><td>${esc(f.kind)}</td><td><b>${esc(f.value)}</b></td><td class="${f.ok ? "fact-ok" : "fact-bad"}">${f.ok ? "&#10003; " + esc(f.where) : "&#10007; not found anywhere"}</td></tr>`).join("") + "</tbody></table>"
      : '<p class="hint" style="margin-top:10px">The reply does not mention any order number, amount or date.</p>';

  const decisions = ev.decisions.length ? ev.decisions.map((x) => `<div class="decision">${ico(x.ok ? "check" : x.kind === "lookup" ? "info" : "x")}<div><b>${esc(x.title)}</b><span class="why">${esc(x.why || "")}</span></div></div>`).join("")
      : '<p class="hint">The AI used no tools for this ticket.</p>';

  let now = '<p class="hint">No order is linked to this ticket.</p>';
  const o = ev.order_now;
  if (o && o.found === false) now = `<div class="note">Order #${o.order_id} is not on this customer's account, so its details are not shown.</div>`;
  else if (o) now = `<div class="rows"><div class="row"><span>Order</span><span>#${o.order_id} &middot; ${esc(o.item)}</span></div>
      <div class="row"><span>Amount</span><span>${money(o.amount)}</span></div><div class="row"><span>Status</span><span style="text-transform:capitalize">${esc(o.status)}</span></div>
      <div class="row"><span>Refunded</span><span>${o.refunded ? '<span style="color:var(--green)">Yes (simulated)</span>' : "No"}</span></div>
      ${o.refund_records.map((x) => `<div class="row"><span>Refund record</span><span>${money(x.amount)} &middot; ${esc(x.approved_by)}</span></div>`).join("")}
      <div class="row"><span>Ship to</span><span>${esc(o.shipping_address)}</span></div></div>`;

  const rv = d.review && !d.review.stale ? d.review : null;
  const stale = d.review && d.review.stale ? '<span class="tag tag-sim">YOUR OLD REVIEW IS OUTDATED: THE REPLY CHANGED</span>' : "";
  const stateLine = rv ? `<div class="rv-state">${chip(...REVIEW_CHIP[rv.verdict])}<span>${esc(rv.reviewer)} &middot; ${esc(fmtTime(rv.reviewed_at))}${rv.reason_text ? " &middot; " + esc(rv.reason_text) : ""}${rv.note ? " &middot; &ldquo;" + esc(rv.note) + "&rdquo;" : ""}</span>
      <a class="link" data-action="review-clear">Clear my review</a></div>` : stale;
  const reasons = Object.entries(d.reasons).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
  const form = r.form ? `<div class="rv-form"><b style="color:#991b1b">What is wrong?</b><select id="rv-reason"><option value="">Choose a reason...</option>${reasons}</select>
      <button class="btn btn-danger" data-action="review-save-incorrect">${ico("x")}Save as incorrect</button><a class="link" data-action="review-cancel">Cancel</a></div>` : "";
  const disabled = r.busy ? "disabled" : "";

  return `<div class="rv-scroll"><div class="rv-head"><div><h2>${esc(t.subject)}</h2>
        <div class="detail-meta"><span>${esc(t.customer_name)} &lt;${esc(t.customer_email)}&gt;</span><span>${esc(fmtTime(t.created_at))}</span><span>Ticket #${t.ticket_id}</span></div></div>
      <div class="detail-actions">${chip(...REVIEW_CHIP[rv ? rv.verdict : "to_review"])}<a class="btn btn-ghost btn-sm" data-action="review-open" data-id="${t.ticket_id}">Open in Inbox</a></div></div>
    <div class="rv-grid"><div class="rv-col">
      <div class="card card-pad"><div class="label">1. What the customer wrote</div><div class="bubble">${esc(t.body)}</div></div>
      <div class="card card-pad"><div class="card-head"><div class="label">2. What the AI replied</div><span class="tag tag-sim">SIMULATED SEND</span></div><div class="bubble reply">${esc(res.reply)}</div></div>
      <div class="card card-pad"><div class="label">3. Are the facts in the reply real?</div><p class="hint">Each order number, amount and date in the reply, checked against what the system returned.</p>${facts}</div>
    </div><div class="rv-col">
      <div class="card card-pad"><div class="label">4. What the AI did, and why the rules allowed it</div><div style="margin-top:8px">${decisions}</div>
        <p class="hint">${ev.llm_used ? "The LLM was used to understand the request and to write the reply." : "No LLM was used for this ticket."} ${ev.tools_used} tool call(s).</p></div>
      <div class="card card-pad"><div class="label">5. The data right now</div><div style="margin-top:8px">${now}</div></div>
      <div class="card card-pad"><div class="card-head"><div class="label">Step by step</div><span class="muted" style="font-size:12.5px">${d.timeline.length} steps</span></div>${timelineHtml(d.timeline)}</div>
    </div></div></div>
    <div class="rv-bar"><div class="rv-bar-inner">${form}${stateLine ? stateLine : ""}
      <div class="rv-buttons"><button class="btn btn-green" data-action="review-verdict" data-v="correct" ${disabled}>${ico("check")}Correct<kbd>1</kbd></button>
        <button class="btn btn-danger" data-action="review-verdict" data-v="incorrect" ${disabled}>${ico("x")}Incorrect<kbd>2</kbd></button>
        <button class="btn btn-amber" data-action="review-verdict" data-v="unsure" ${disabled}>${ico("help")}Not sure<kbd>3</kbd></button>
        <input id="rv-note" class="rv-note" type="text" maxlength="300" placeholder="Optional note" value="${rv && rv.note ? esc(rv.note) : ""}">
        <span class="hint" style="margin:0">J / K: next / previous ticket</span></div></div></div>`;
}

function renderReview() {
  const root = $("#view-review");
  root.innerHTML = `<section class="rv-list">${reviewListHtml()}</section><section class="rv-main">${reviewMainHtml()}</section>`;
}

async function submitReview(verdict, reason) {
  const r = state.review; if (r.busy || !r.selectedId) return;
  const note = ($("#rv-note") || {}).value || "";
  r.busy = true; renderReview();
  try {
    const id = r.selectedId;
    r.detail = await api("/review/" + id, { method: "POST", body: { verdict, reason: reason || null, note, reviewer: "reviewer" } });
    toast(verdict === "correct" ? "Marked correct" : verdict === "incorrect" ? "Marked incorrect" : "Marked not sure");
    r.form = false; r.busy = false;
    const before = r.items.findIndex((i) => i.ticket_id === id);
    await loadReviewQueue();
    if (r.filter === "to_review") {                                 // the ticket left this list: go to the next one
      const next = r.items[Math.min(before, r.items.length - 1)];
      r.selectedId = next ? next.ticket_id : null; r.detail = null;
      renderReview();
      if (next) await selectReview(next.ticket_id);
      return;
    }
  } catch (e) { toast(e.message, "error"); }
  r.busy = false; renderReview();
}

async function stepReview(delta) {
  const r = state.review, i = r.items.findIndex((x) => x.ticket_id === r.selectedId), n = r.items[i + delta];
  if (n) await selectReview(n.ticket_id);
}

// ----------------------------------------------------------------- events
document.addEventListener("click", async (ev) => {
  const el = ev.target.closest("[data-action], .tab");
  if (!el) return;
  if (el.classList.contains("tab")) { showView(el.dataset.view); return; }
  const id = el.dataset.id ? Number(el.dataset.id) : state.selectedId;
  switch (el.dataset.action) {
    case "select": selectTicket(id); break;
    case "filter": state.filter = el.dataset.key; renderList(); break;
    case "process": processTicket(id); break;
    case "approve": approveTicket(id); break;
    case "reject": rejectTicket(id); break;
    case "toggle-edit": state.editing = !state.editing; renderDetail(); break;
    case "open": showView("inbox"); state.filter = "all"; state.search = ""; $("#search").value = ""; await selectTicket(id); renderList(); break;
    case "review-select": selectReview(id); break;
    case "review-filter": state.review.filter = el.dataset.key; state.review.selectedId = null; openReview(); break;
    case "review-verdict": {
      const v = el.dataset.v;
      if (v === "incorrect") { state.review.form = true; renderReview(); } else submitReview(v);
      break;
    }
    case "review-save-incorrect": {
      const reason = ($("#rv-reason") || {}).value;
      if (!reason) { toast("Please choose what is wrong.", "error"); break; }
      submitReview("incorrect", reason); break;
    }
    case "review-cancel": state.review.form = false; renderReview(); break;
    case "review-clear":
      try { state.review.detail = await api("/review/" + state.review.selectedId, { method: "DELETE" }); await loadReviewQueue(); renderReview(); toast("Review cleared"); }
      catch (e) { toast(e.message, "error"); }
      break;
    case "review-open": showView("inbox"); state.filter = "all"; state.search = ""; $("#search").value = ""; await selectTicket(id); renderList(); break;
    case "review-process": {
      el.disabled = true;
      try { const out = await api("/process_next?n=5", { method: "POST" }); toast(out.processed.length ? `Processed ${out.processed.length} tickets` : "No new tickets left"); await refreshAll(); }
      catch (e) { toast(e.message, "error"); }
      break;
    }
    case "goto-review": showView("review"); break;
    case "q-approve": await runWithBusy(id, async () => { await api(`/tickets/${id}/approve`, { method: "POST", body: { by: "human_agent" } }); }, "Approved. Refund and reply done (simulated)."); renderQueue(); break;
    case "q-reject": await runWithBusy(id, async () => { await api(`/tickets/${id}/reject`, { method: "POST", body: { by: "human_agent" } }); }, "Ticket rejected. Reply sent (simulated)."); renderQueue(); break;
  }
});
window.addEventListener("hashchange", () => {
  const m = /^#t(\d+)$/.exec(location.hash);
  if (m && Number(m[1]) !== state.selectedId) { showView("inbox"); selectTicket(Number(m[1])); }
});
document.addEventListener("keydown", (e) => {
  if (state.view !== "review" || e.ctrlKey || e.metaKey || e.altKey) return;
  if (/^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || ""))) return;
  const k = e.key.toLowerCase();
  if (k === "1") submitReview("correct");
  else if (k === "2") { state.review.form = true; renderReview(); }
  else if (k === "3") submitReview("unsure");
  else if (k === "j" || k === "arrowdown") { e.preventDefault(); stepReview(1); }
  else if (k === "k" || k === "arrowup") { e.preventDefault(); stepReview(-1); }
});
$("#search").addEventListener("input", (e) => { state.search = e.target.value; renderList(); });
$("#btn-process-next").addEventListener("click", processNext);

// ------------------------------------------------------------------ start
(async function init() {
  try {
    await Promise.all([loadTickets(), loadQueue(), loadReviewQueue()]);
    const fromHash = /^#t(\d+)$/.exec(location.hash);
    const first = fromHash ? Number(fromHash[1]) : (state.tickets.find((t) => t.status_key === "waiting") || state.tickets[0] || {}).ticket_id;
    renderList();
    if (first) await selectTicket(first); else renderDetail();
  } catch (e) {
    toast("Could not load tickets: " + e.message, "error");
  }
})();
