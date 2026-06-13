const API = "http://localhost:4000";

// Track applied jobs so buttons show correct state across re-renders
const appliedJobs = new Set();
let currentAgent     = "booking";   // booking | crew | hr
let lastCandidateId  = "";
let chatHistories    = { crew: [], booking: [], hr: [] };
let isLoading        = false;
let msgCount         = { crew: 0, booking: 0, hr: 0 }; // track AI responses per agent

// ── Markdown renderer ─────────────────────────────────────────────────────────
function md(text) {
  if (!text || typeof text !== "string") return "";

  // Strip everything from ---QUESTIONS--- onwards
  if (text.includes("---QUESTIONS---")) text = text.split("---QUESTIONS---")[0].trim();

  // Strip any leaked raw JSON arrays at end of text
  text = text.replace(/\[\s*\{[\s\S]*?\}\s*\]/g, "").trim();
  text = text.replace(/\[\s*"[^"]*"[\s\S]*?\]/g, "").trim();

  // Strip trailing dashes/separators
  text = text.replace(/^[-—]{3,}\s*$/gm, "").trim();

  return text
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/^### (.+)$/gm,"<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm,  "<h1>$1</h1>")
    .replace(/\*\*\*(.+?)\*\*\*/g,"<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g,    "<strong>$1</strong>")
    .replace(/(^[*+\-] .+$\n?)+/gm, match => {
      const items = match.trim().split("\n")
        .map(l => `<li>${l.replace(/^[*+\-] /,"")}</li>`).join("");
      return `<ul>${items}</ul>`;
    })
    .replace(/\*(.+?)\*/g,"<em>$1</em>")
    .replace(/\n{2,}/g,"</p><p>")
    .replace(/\n/g,"<br>");
}

// ── Utility ───────────────────────────────────────────────────────────────────
function statusClass(s) {
  if (!s) return "";
  s = s.toLowerCase();
  if (s.includes("fully")) return "status-booked";
  if (s.includes("partial")) return "status-partial";
  return "status-available";
}
function statusLabel(s) {
  if (!s) return "🟢 Available";
  s = s.toLowerCase();
  if (s.includes("fully")) return "🔴 Fully Booked";
  if (s.includes("partial")) return "🟡 Partially Booked";
  return "🟢 Available";
}
function shortId(id) { return id ? id.toString().slice(0,8) + "…" : ""; }

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}

function scrollToBottom() {
  const m = document.getElementById("messages");
  m.scrollTop = m.scrollHeight;
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function toggleSidebar() {
  const sb = document.getElementById("sidebar");
  if (window.innerWidth <= 680) {
    sb.classList.toggle("mobile-open");
  } else {
    sb.classList.toggle("collapsed");
  }
}

// ── Agent switching ───────────────────────────────────────────────────────────
function switchAgent(agent, btn) {
  if (agent === currentAgent) return; // already on this agent, do nothing
  currentAgent = agent;
  resetBookingContext();

  // Clear chat messages for the new agent
  const msgs = document.getElementById("messages");
  msgs.querySelectorAll(".msg-row").forEach(el => el.remove());
  lastCandidateId = "";
  msgCount[agent] = 0;
  document.getElementById("user-input").value = "";
  document.getElementById("user-input").style.height = "auto";
  // Clear attached file
  const cFile = document.getElementById("c-file");
  if (cFile) cFile.value = "";
  const attachBtn2 = document.getElementById("attach-btn");
  if (attachBtn2) attachBtn2.classList.remove("has-file");
  // Show welcome screen
  document.getElementById("welcome").style.display = "flex";

  // Update active button
  document.querySelectorAll(".agent-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");

  // Update header title
  const titles = { crew: "Crew Career Agent", booking: "Boat Booking Agent", hr: "HR Agent" };
  document.getElementById("chat-title").textContent = titles[agent];
  updateHeaderDot(agent);

  // Toggle attach button visibility
  const attachBtn = document.getElementById("attach-btn");
  if (attachBtn) attachBtn.classList.toggle("hidden", agent !== "crew");
  document.getElementById("hr-header-controls").classList.toggle("hidden", agent !== "hr");

  // Toggle input extra fields
  document.getElementById("booking-fields").classList.toggle("hidden", agent !== "booking");
  if (agent === "hr") {
    document.getElementById("hr-fields").classList.remove("hidden");
    buildHrFields();
  } else {
    document.getElementById("hr-fields").classList.add("hidden");
  }

  // Update placeholder
  const placeholders = {
    crew:    "Ask about jobs, skill gaps, certifications, career advice...",
    booking: "Search for boats, check availability, book a vessel...",
    hr:      "Generate a JD, rank candidates, See candidate application...",
  };
  document.getElementById("user-input").placeholder = placeholders[agent];

  // Update welcome chips
  const chips = {
    crew:    ["Which jobs am I eligible for?","Analyze my skill gaps","What certifications do I need?","Give me a career plan"],
    booking: ["Show luxury boats in Goa","Find boats under ₹20k in Kerala","Any ferries in Mumbai?","Best rated boats in Kochi"],
    hr:      [],
  };
  document.getElementById("welcome-chips").innerHTML = chips[agent]
    .map(c => `<span class="w-chip" onclick="useChip(this)">${c}</span>`).join("");

  // Keep welcome if no messages for this agent
  showWelcomeIfEmpty();
}

// Show agent dot color in header
function updateHeaderDot(agent) {
  const dot = document.getElementById("header-dot");
  if (!dot) return;
  dot.className = "header-agent-dot";
  dot.classList.add(agent === "crew" ? "crew-dot" : agent === "booking" ? "booking-dot" : "hr-dot");
}

function showWelcomeIfEmpty() {
  const msgs = document.getElementById("messages");
  const real = msgs.querySelectorAll(".msg-row");
  document.getElementById("welcome").style.display = real.length === 0 ? "flex" : "none";
}

// ── HR fields builder ─────────────────────────────────────────────────────────
function buildHrFields() {
  const modeEl = document.getElementById("hr-mode");
  if (!modeEl) return;
  const mode = modeEl.value;
  const grid = document.getElementById("hr-fields-grid");
  const selectStyle = `style="background:#0a1828;border:1px solid rgba(59,158,218,.25);border-radius:8px;padding:.4rem .7rem;font-size:.83rem;color:#ccdcf0;font-family:inherit;outline:none;width:100%"`;
  const templates = {
    generate_jd: `
      <div class="field-group"><label>Role</label><input id="hr-role" placeholder="e.g. Captain" oninput="hrFillJdInput()"/></div>
      <div class="field-group"><label>Location</label><input id="hr-location" placeholder="e.g. Mumbai" oninput="hrFillJdInput()"/></div>
      <div class="field-group"><label>Min Experience (yrs)</label><input id="hr-exp" type="number" value="3" min="0" placeholder="e.g. 3"/></div>
      <div class="field-group"><label>Specify Requirements</label><input id="hr-context" placeholder="e.g. Bulk carrier, VLCC ops"/></div>`,
    rank_candidates: `
      <div class="field-group" style="min-width:280px">
        <label>Rank applicants for job</label>
        <select id="hr-rank-jobid" onchange="hrFillInput()" ${selectStyle}><option value="">Loading jobs…</option></select>
      </div>`,
    list_jobs: `
      <div class="field-group">
        <label>Filter by status</label>
        <select id="hr-jobs-filter" onchange="hrFillInput()" ${selectStyle}>
          <option value="">All</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="closed">Closed</option>
        </select>
      </div>`,
    notifications: ``,
  };
  grid.innerHTML = templates[mode] || "";

  // Auto-populate job dropdown — HR published jobs + jobs with applications (no duplicates)
  if (mode === "rank_candidates") {
    Promise.all([
      fetch(`${API}/hr/jobs?status=published`).then(r => r.json()).catch(() => ({ jobs: [] })),
      fetch(`${API}/hr/notifications`).then(r => r.json()).catch(() => ({ notifications: [] }))
    ]).then(([hrData, notifData]) => {
      const sel = document.getElementById("hr-rank-jobid");
      if (!sel) return;

      const seen  = new Set();
      const options = [];

      // 1. HR published jobs first
      for (const j of (hrData.jobs || [])) {
        const key = (j.title || "").toLowerCase().trim();
        if (!seen.has(key) && j._id && j.title) {
          seen.add(key);
          options.push({ id: j._id, title: j.title });
        }
      }

      // 2. Jobs from notifications (crew applied — seeded or HR jobs)
      for (const n of (notifData.notifications || [])) {
        const key = (n.job_title || "").toLowerCase().trim();
        if (!seen.has(key) && n.job_id && n.job_title) {
          seen.add(key);
          options.push({ id: n.job_id, title: n.job_title });
        }
      }

      if (!options.length) {
        sel.innerHTML = `<option value="">No jobs found</option>`;
        return;
      }
      sel.innerHTML = `<option value="">— Select a job to rank applicants —</option>` +
        options.map(j => `<option value="${j.id}">${j.title}</option>`).join("");
    });
  }
}

function onHrModeChange() {
  buildHrFields();
  const mode = document.getElementById("hr-mode")?.value;

  // Auto-trigger for modes that need no extra input
  if (mode === "notifications") {
    setTimeout(() => hrAutoTrigger(mode), 100);
  }
  // list_jobs & rank_candidates: selection fills input box, user presses Enter
  // generate_jd: user fills role/location, presses Enter
}

function hrFillJdInput() {
  const role = document.getElementById("hr-role")?.value.trim();
  const loc  = document.getElementById("hr-location")?.value.trim();
  const input = document.getElementById("user-input");
  if (!input) return;
  if (role || loc) {
    input.value = `Generate JD for ${role || "role"}${loc ? " in " + loc : ""}`;
    autoResize(input);
  }
}

function hrFillInput() {
  const mode = document.getElementById("hr-mode")?.value;
  const input = document.getElementById("user-input");
  if (!input) return;

  if (mode === "list_jobs") {
    const sel = document.getElementById("hr-jobs-filter");
    const label = sel?.options[sel.selectedIndex]?.text || "All";
    input.value = label === "All" ? "Show all jobs" : `Show ${label.toLowerCase()} jobs`;
    autoResize(input);
    input.focus();
  } else if (mode === "rank_candidates") {
    const sel = document.getElementById("hr-rank-jobid");
    const val = sel?.value;
    const label = sel?.options[sel.selectedIndex]?.text || "";
    if (val && label && label !== "— Select a job to rank applicants —") {
      // Auto-trigger immediately when a real job is selected
      if (isLoading) return;
      appendMessage("user", `Rank applicants for: ${label}`);
      setTyping(true);
      handleHR("").catch(e => { setTyping(false); appendMessage("ai","❌ "+e.message); });
    }
  }
}

function onJobSelected() {
  hrFillInput();
}

async function hrAutoTrigger(mode) {
  if (isLoading) return;
  const statusEl = document.getElementById("hr-jobs-filter");
  const status = statusEl?.value || "";
  const statusLabel = statusEl?.options[statusEl.selectedIndex]?.text || "All";
  const modeLabels = {
    notifications: "Show new applications",
    list_jobs: `Show ${status ? statusLabel.toLowerCase() : "all"} jobs`,
    rank_candidates: "Shortlist candidates",
  };
  appendMessage("user", modeLabels[mode] || mode);
  setTyping(true);
  try {
    await handleHR("");
  } catch(e) {
    setTyping(false);
    appendMessage("ai", "❌ " + e.message);
  }
}

// ── File selection ────────────────────────────────────────────────────────────
function onFileSelected(input) {
  const attachBtn2 = document.getElementById("attach-btn");
  if (input.files && input.files[0]) {
    if (attachBtn2) attachBtn2.classList.add("has-file");
    // Just visually mark attached — DO NOT send chat bubble yet
    // File will go with the next query the user types
  } else {
    if (attachBtn2) attachBtn2.classList.remove("has-file");
  }
}

// ── New chat ──────────────────────────────────────────────────────────────────
function newChat() {
  const msgs = document.getElementById("messages");
  msgs.querySelectorAll(".msg-row").forEach(el => el.remove());
  lastCandidateId = "";
  resetBookingContext();
  msgCount[currentAgent] = 0;
  appliedJobs.clear();
  document.getElementById("welcome").style.display = "flex";
  document.getElementById("user-input").value = "";
  document.getElementById("user-input").style.height = "auto";
  // Clear file
  const cFile2 = document.getElementById("c-file");
  if (cFile2) cFile2.value = "";
  const attachBtn2 = document.getElementById("attach-btn");
  if (attachBtn2) attachBtn2.classList.remove("has-file");
}

// ── Use welcome chip ──────────────────────────────────────────────────────────
function useChip(el) {
  document.getElementById("user-input").value = el.textContent;
  document.getElementById("user-input").focus();
}

// ── Key handler ───────────────────────────────────────────────────────────────
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// ── Append message bubble ─────────────────────────────────────────────────────
function appendMessage(role, content, isHTML = false) {
  const msgs = document.getElementById("messages");
  document.getElementById("welcome").style.display = "none";

  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  if (isHTML) {
    bubble.innerHTML = content;
  } else {
    bubble.innerHTML = `<p>${md(content)}</p>`;
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  msgs.appendChild(row);
  scrollToBottom();
  return bubble;
}

function setTyping(show) {
  document.getElementById("typing").classList.toggle("hidden", !show);
  document.getElementById("send-btn").disabled = show;
  isLoading = show;
  if (show) scrollToBottom();
}

// ── SEND MESSAGE ──────────────────────────────────────────────────────────────
async function sendMessage() {
  if (isLoading) return;
  const input = document.getElementById("user-input");
  const query = input.value.trim();
  const file  = document.getElementById("c-file")?.files[0];

  // For HR: allow send with no text (mode+job selection is enough)
  // For crew: allow send with just file and no text
  // For booking: require query
  if (!query && !file && currentAgent === "booking") { input.focus(); return; }
  if (!query && !file && currentAgent === "crew")    { input.focus(); return; }

  // Append user message — include filename if file attached
  if (query || file) {
    const displayMsg = file
      ? `${query || ""}${query ? " &nbsp;" : ""}📎 <em style="color:rgba(255,255,255,.55);font-size:.83rem">${file.name}</em>`
      : query;
    appendMessage("user", displayMsg, true);
  } else if (currentAgent === "hr") {
    // HR triggered by dropdown — show auto message
    const modeEl = document.getElementById("hr-mode");
    const modeLabels = { generate_jd:"Generate JD", list_jobs:"Show all jobs", notifications:"Show applications", rank_candidates:"Shortlist candidates" };
    const label = modeLabels[modeEl?.value] || "HR action";
    appendMessage("user", label);
  }
  input.value = "";
  input.style.height = "auto";
  setTyping(true);

  try {
    if (currentAgent === "crew")    await handleCrew(query);
    else if (currentAgent === "booking") await handleBooking(query);
    else if (currentAgent === "hr") await handleHR(query);
  } catch (e) {
    setTyping(false);
    const errMsg = e.message === "Failed to fetch"
      ? "❌ Cannot reach server. Make sure the backend is running on port 4000."
      : "❌ Server error: " + e.message;
    appendMessage("ai", errMsg);
  }
}

// ── CREW AGENT ────────────────────────────────────────────────────────────────
async function handleCrew(query) {
  const file   = document.getElementById("c-file").files[0];
  const thought = false;

  let data;

  if (file) {
    const form = new FormData();
    form.append("query", query);
    form.append("file", file);
    form.append("save_candidate", true);
    form.append("include_thought_process", thought);
    const res = await fetch(`${API}/agent/run-with-resume`, { method: "POST", body: form });
    data = await res.json();

    if (!data.error) {
      // Clear the file after successful parse — all follow-ups use candidate_id
      const cFile = document.getElementById("c-file");
      if (cFile) cFile.value = "";
      const attachBtn = document.getElementById("attach-btn");
      if (attachBtn) attachBtn.classList.remove("has-file");
    }
  } else if (lastCandidateId) {
    const res = await fetch(`${API}/agent/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, candidate_id: lastCandidateId, include_thought_process: thought }),
    });
    data = await res.json();
  } else {
    setTyping(false);
    appendMessage("ai", "📎 Please attach your resume using the **Attach Resume** button above, then ask your question.");
    return;
  }

  setTyping(false);

  if (data.error) { appendMessage("ai", "❌ " + data.error); return; }

  lastCandidateId = data.candidate_id || data.data?.candidate_id || lastCandidateId;
  const isFirstCrew = msgCount["crew"] === 0;
  msgCount["crew"]++;
  appendMessage("ai", buildCrewHTML(data, isFirstCrew), true);
}

function buildCrewHTML(data, isFirst = false) {
  const meta = isFirst ? `<div class="meta-row">
    <span class="badge">🤖 ${data.agent||"Crew Agent"}</span>
    <span class="badge green">👤 ${data.candidate_name||"—"}</span>
    <span class="badge amber">🎯 ${String(data.intent||"").replace(/_/g," ")}</span>
    <span class="badge">💼 ${data.data?.eligible_jobs??0} / ${data.data?.total_jobs??0} eligible</span>
  </div>` : "";

  const response = `<div>${md(data.response||"")}</div>`;

  const matches = data.data?.best_matches || data.data?.skill_gap_report || [];
  // Sort best to least by gap_score
  const sorted = [...matches].sort((a, b) => (b.gap_score ?? 0) - (a.gap_score ?? 0));
  const jobCards = sorted.length ? `
    <div class="jobs-grid" style="margin-top:.8rem">
      ${sorted.map(j => {
        const score = j.gap_score ?? j.skill_match_pct ?? 0;
        const eligible = j.is_eligible && score >= 50;   // score<50 = cannot apply
        const canApply = eligible && score >= 50;
        const borderColor = score >= 70 ? "#4ade80" : score >= 50 ? "#fbbf24" : "#f87171";
        const scoreColor  = score >= 70 ? "#4ade80" : score >= 50 ? "#fbbf24" : "#f87171";
        const jobId = j.job_id || j._id || "";
        return `<div class="job-card" style="border-top-color:${borderColor}">
          <h4>${j.title || j.job_title || "—"}</h4>
          <div class="score-bar">
            <span class="score-num" style="color:${scoreColor}">${score}/100</span>
            <div class="score-track"><div class="score-fill" style="width:${score}%;background:${scoreColor}"></div></div>
          </div>
          <div class="job-meta">
            ${eligible !== undefined ? (eligible
              ? '<span class="tag-eligible">✅ Eligible</span>'
              : '<span class="tag-ineligible">❌ Not Eligible</span>') : ""}
            ${j.eligibility_label ? `<span class="tag-label">${j.eligibility_label}</span>` : ""}
            ${j.skill_match_pct != null ? `<br>🎯 Skills: <strong>${j.skill_match_pct}%</strong>` : ""}
            ${j.experience_years != null ? `<br>⏱ Experience: <strong>${j.experience_years} yrs</strong> ${j.minimum_experience != null ? `(needs ${j.minimum_experience}+)` : ""}` : ""}
            ${j.location  ? `<br>� ${j.location}` : ""}
            ${j.salary    ? `<br>💰 ${j.salary}` : ""}
            ${(j.missing_certs?.length) ? `<br><span style="color:#f59e0b">📜 Missing certs: ${j.missing_certs.join(", ")}</span>` : ""}
            ${j.missing_mandatory?.length ? `<br><span style="color:#f87171">⚠ Missing skills: ${j.missing_mandatory.join(", ")}</span>` : ""}
            ${j.present_skills?.length ? `<br><span style="color:#6ee7b7">✔ Has: ${j.present_skills.slice(0,4).join(", ")}</span>` : ""}
          </div>
          ${canApply && jobId
            ? appliedJobs.has(jobId)
              ? `<button class="apply-btn" disabled style="background:rgba(255,255,255,.1);color:rgba(255,255,255,.4);cursor:default;border:1px solid rgba(255,255,255,.12)">✅ Applied</button>`
              : `<button class="apply-btn" id="apply-btn-${jobId}" onclick="crewApply('${jobId}','${(j.title||j.job_title||"").replace(/'/g,"")}')">📝 Apply Now</button>`
            : score < 50
              ? `<div style="font-size:.74rem;color:#f87171;margin-top:.5rem;padding:.28rem .6rem;background:rgba(248,113,113,.1);border-radius:6px;display:inline-block">Score too low to apply (min 50)</div>`
              : ""
          }
        </div>`;
      }).join("")}
    </div>` : "";

  const qs = buildSuggestions(data.suggested_questions, true);
  return meta + response + jobCards + qs;
}

// ── BOOKING AGENT ─────────────────────────────────────────────────────────────
// State for pending booking confirmation
let pendingBooking = null; // { boatName, boatId, price }

async function handleBooking(query) {
  const name    = document.getElementById("b-name")?.value.trim() || "Guest";
  const payment = document.getElementById("b-payment")?.value || "online";
  const confirm = document.getElementById("b-confirm")?.value === "true";

  // Detect booking intent — user said yes/book after seeing boats
  const isConfirmIntent = /^(yes|book|confirm|book it|yes please|ok book|proceed)$/i.test(query.trim());
  if (isConfirmIntent && pendingBooking) {
    // Show inline booking details form instead of re-querying
    setTyping(false);
    showBookingForm(pendingBooking, name);
    return;
  }

  // Build enriched query: merge current query with stored context
  const hint = buildContextHint();
  let enrichedQuery = query;
  if (hint) {
    // Only inject context if the query itself doesn't already have full location/filter info
    const hasLocation = /kerala|goa|mumbai|kochi|alleppey|chennai|goa|kolkata|vizag|mangalore|andaman|lakshadweep/i.test(query);
    const hasBudget   = /₹|\d+k|\d{4,}/i.test(query);
    if (!hasLocation && !hasBudget) {
      // Follow-up query — inject previous context
      enrichedQuery = `${query} (previous context: ${hint})`;
    } else if (!hasLocation && hint.includes("location")) {
      // Has budget/other filter but no location — carry location forward
      enrichedQuery = `${query} in ${bookingContext.location}`;
    }
  }

  const params = new URLSearchParams({
    query: enrichedQuery,
    user_name: name,
    confirm_booking: confirm,
    payment_method: payment,
    include_thought_process: false,
  });
  const res  = await fetch(`${API}/booking/run?${params}`, { method: "POST" });
  const data = await res.json();
  setTyping(false);

  if (data.error && !data.response) { appendMessage("ai", "❌ " + data.error); return; }

  // Store the context extracted from this response for next turn
  if (data.data?._req) updateBookingContext(data.data._req);
  // Fallback: parse context from the enriched query we sent
  _parseAndStoreContext(enrichedQuery, data);

  // Store top boat for pending booking confirmation
  const topBoats = data.data?.top_recommendations || [];
  if (topBoats.length > 0) {
    pendingBooking = {
      name: topBoats[0].name,
      boatId: topBoats[0].boat_id || topBoats[0]._id,
      price: topBoats[0].price_per_day,
      location: topBoats[0].location,
    };
  }

  const isFirst = msgCount["booking"] === 0;
  msgCount["booking"]++;
  appendMessage("ai", buildBookingHTML(data, isFirst), true);
}

function showBookingForm(boat, userName) {
  const now = new Date();
  const months = [];
  for (let i = 1; i <= 8; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const val = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    const label = d.toLocaleString("en-IN", { month: "long", year: "numeric" });
    months.push(`<option value="${val}">${label}</option>`);
  }

  const html = `
    <div style="line-height:1.8">
      <p style="margin-bottom:.8rem">Great choice! To confirm booking for <strong>${boat.name}</strong> (₹${(boat.price||0).toLocaleString()}/day), I need a few details:</p>
      <div style="display:flex;flex-direction:column;gap:.6rem">
        <div class="field-group">
          <label>Travel Month</label>
          <select id="bk-month" style="background:#0a1828;border:1px solid rgba(59,158,218,.3);border-radius:8px;padding:.4rem .7rem;font-size:.83rem;color:#ccdcf0;font-family:inherit;outline:none">
            ${months.join("")}
          </select>
        </div>
        <div class="field-group">
          <label>Payment Method</label>
          <select id="bk-payment" style="background:#0a1828;border:1px solid rgba(59,158,218,.3);border-radius:8px;padding:.4rem .7rem;font-size:.83rem;color:#ccdcf0;font-family:inherit;outline:none">
            <option value="online">Online</option>
            <option value="upi">UPI</option>
            <option value="card">Card</option>
            <option value="cash">Cash</option>
          </select>
        </div>
        <button onclick="confirmBookingNow('${boat.name}','${userName}')"
          style="background:linear-gradient(135deg,#1e6fa8,#0d4a7a);color:#fff;border:none;padding:.5rem 1.2rem;border-radius:10px;font-size:.88rem;font-weight:700;cursor:pointer;font-family:inherit;margin-top:.3rem;align-self:flex-start">
          ✅ Confirm Booking
        </button>
      </div>
    </div>`;
  appendMessage("ai", html, true);
}

async function confirmBookingNow(boatName, userName) {
  const month   = document.getElementById("bk-month")?.value;
  const payment = document.getElementById("bk-payment")?.value || "online";
  if (!month) { alert("Please select a travel month."); return; }

  const query = `Book ${boatName} for ${month}, payment: ${payment}, confirm booking`;
  appendMessage("user", `✅ Confirm ${boatName} — ${new Date(month+"-01").toLocaleString("en-IN",{month:"long",year:"numeric"})} · ${payment}`);
  setTyping(true);

  const params = new URLSearchParams({
    query,
    user_name: userName || "Guest",
    confirm_booking: true,
    payment_method: payment,
    include_thought_process: false,
  });
  try {
    const res  = await fetch(`${API}/booking/run?${params}`, { method: "POST" });
    const data = await res.json();
    setTyping(false);
    pendingBooking = null;
    const isFirstB = msgCount["booking"] === 0;
    msgCount["booking"]++;
    appendMessage("ai", buildBookingHTML(data, isFirstB), true);
  } catch(e) {
    setTyping(false);
    appendMessage("ai", "❌ Booking failed: " + e.message);
  }
}

function _parseAndStoreContext(query, data) {
  // Extract location from response boats if available
  const boats = data.data?.top_recommendations || [];
  if (boats.length > 0 && boats[0].location) {
    if (!bookingContext.location) bookingContext.location = boats[0].location;
  }
  // Parse budget from query string
  const budgetMatch = query.match(/under\s*[₹rs]?\s*(\d+)k?/i);
  if (budgetMatch) {
    let val = parseInt(budgetMatch[1]);
    if (query.toLowerCase().includes("k")) val *= 1000;
    if (!bookingContext.budget_max) bookingContext.budget_max = val;
  }
  // Parse location keywords from query
  const locationMap = {
    kerala: "Kerala", kochi: "Kochi", alleppey: "Alleppey", goa: "Goa",
    mumbai: "Mumbai", chennai: "Chennai", kolkata: "Kolkata",
    vizag: "Visakhapatnam", visakhapatnam: "Visakhapatnam",
    mangalore: "Mangalore", andaman: "Port Blair", lakshadweep: "Lakshadweep",
  };
  for (const [key, val] of Object.entries(locationMap)) {
    if (query.toLowerCase().includes(key)) {
      bookingContext.location = val;
      break;
    }
  }
}

function buildContextPill() {
  const parts = [];
  if (bookingContext.location)     parts.push(`📍 ${bookingContext.location}`);
  if (bookingContext.budget_max)   parts.push(`💰 ≤₹${Number(bookingContext.budget_max).toLocaleString()}`);
  if (bookingContext.passengers)   parts.push(`👥 ${bookingContext.passengers}`);
  if (bookingContext.travel_month) parts.push(`📅 ${bookingContext.travel_month}`);
  if (bookingContext.boat_type)    parts.push(`🚢 ${bookingContext.boat_type}`);
  if (!parts.length) return "";
  return `<span class="badge" style="background:#e0f2fe;color:#0369a1;border-color:#bae6fd;font-size:.72rem" title="Active filters carried from conversation">
    🔁 ${parts.join(" · ")}
  </span>`;
}

function buildBookingHTML(data, isFirst = false) {
  const meta = isFirst
    ? `<div class="meta-row">
    <span class="badge">🤖 ${data.agent||"Booking Agent"}</span>
    <span class="badge green">👤 ${data.user_name||"—"}</span>
    <span class="badge amber">🎯 ${String(data.intent||"").replace(/_/g," ")}</span>
    <span class="badge">🚢 ${data.data?.total_boats_found??0} boats found</span>
    ${buildContextPill()}
  </div>`
    : (buildContextPill() ? `<div class="meta-row">${buildContextPill()}</div>` : "");

  const response = `<div>${md(data.response||"")}</div>`;

  const boats = data.data?.top_recommendations || [];
  const boatCards = boats.length ? `
    <div class="boats-grid" style="margin-top:.8rem">
      ${boats.map(b => `
        <div class="boat-card">
          <h4>${b.name}</h4>
          <div class="price">₹${(b.price_per_day||0).toLocaleString()}/day</div>
          <div class="boat-meta">
            <span class="${statusClass(b.booking_status)}">${statusLabel(b.booking_status)}</span><br>
            📍 ${b.location||"—"} · 👥 ${b.capacity} people<br>
            ⭐ ${b.rating} · ${b.type}<br>
            👨‍✈️ ${(b.crew||[]).slice(0,2).join(", ")||"—"}<br>
            🎯 ${(b.activities||[]).slice(0,3).join(", ")||"—"}
          </div>
        </div>`).join("")}
    </div>` : "";

  const booking = data.data?.booking;
  const bookingHtml = booking ? `
    <div class="confirm-card" style="margin-top:.8rem">
      <h3>✅ Booking Confirmed!</h3>
      <div class="meta-row">
        <span class="badge green">🆔 ${booking.booking_id}</span>
        <span class="badge green">🚢 ${booking.boat_name}</span>
        <span class="badge green">📅 ${booking.travel_date}</span>
        <span class="badge green">💳 ${booking.transaction_id?.slice(0,12)}...</span>
      </div>
    </div>` : "";

  const qs = buildSuggestions(data.suggested_questions, false);
  return meta + response + boatCards + bookingHtml + qs;
}

// ── HR AGENT ──────────────────────────────────────────────────────────────────
async function handleHR(query) {
  const modeEl = document.getElementById("hr-mode");
  if (!modeEl) { setTyping(false); return; }

  // If user typed something, try to detect intent from their query
  let mode = modeEl.value;
  if (query) {
    const q = query.toLowerCase();
    if (q.match(/publish|published|active|open job|all job|list job|show job/))  { mode = "list_jobs"; modeEl.value = "list_jobs"; buildHrFields(); }
    else if (q.match(/draft/))                                                     { mode = "list_jobs"; modeEl.value = "list_jobs"; buildHrFields(); }
    else if (q.match(/application|applicant|who applied|candidate.*apply/))        { mode = "notifications"; modeEl.value = "notifications"; buildHrFields(); }
    else if (q.match(/rank|shortlist|score.*candidate|best candidate/))            { mode = "rank_candidates"; modeEl.value = "rank_candidates"; buildHrFields(); }
    else if (q.match(/generate.*jd|create.*jd|new job|post.*job|jd for/))         { mode = "generate_jd"; modeEl.value = "generate_jd"; buildHrFields(); }
  }

  let endpoint, body;

  if (mode === "generate_jd") {
    let role = document.getElementById("hr-role")?.value.trim();
    let loc  = document.getElementById("hr-location")?.value.trim();

    // If fields empty but user typed query, parse role/location from query
    if ((!role || !loc) && query) {
      const q = query.toLowerCase();
      // "generate jd for Captain in Mumbai" → role=Captain, loc=Mumbai
      const forMatch = query.match(/for\s+([A-Za-z\s]+?)\s+in\s+([A-Za-z\s]+?)(?:\s*$)/i);
      if (forMatch) {
        if (!role) role = forMatch[1].trim();
        if (!loc)  loc  = forMatch[2].trim();
      }
    }

    if (!role || !loc) {
      setTyping(false);
      appendMessage("ai", "⚠️ Please fill in the **Role** and **Location** fields, or type: *Generate JD for [Role] in [Location]*");
      return;
    }
    endpoint = "/hr/generate-jd";
    body = {
      role,
      location:         loc,
      experience_years: parseInt(document.getElementById("hr-exp")?.value) || 3,
      extra_context:    document.getElementById("hr-context")?.value.trim() || query || "",
    };
  } else if (mode === "rank_candidates") {
    const job_id = document.getElementById("hr-rank-jobid")?.value.trim();
    if (!job_id) { setTyping(false); appendMessage("ai","⚠️ Please select a job from the dropdown above."); return; }
    endpoint = "/hr/rank-candidates";
    body = { job_id };
  } else if (mode === "list_jobs") {
    let status = document.getElementById("hr-jobs-filter")?.value || "";
    // If user typed "published", override filter
    if (query && query.toLowerCase().includes("publish")) status = "published";
    else if (query && query.toLowerCase().includes("draft")) status = "draft";
    else if (query && query.toLowerCase().includes("closed")) status = "closed";
    endpoint = `/hr/jobs${status ? "?status=" + status : ""}`;
    body = null;
  } else if (mode === "notifications") {
    endpoint = "/hr/notifications";
    body = null;
  }

  const res  = await fetch(`${API}${endpoint}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  setTyping(false);

  if (data.error) { appendMessage("ai","❌ " + data.error); return; }

  // list_jobs returns {jobs, count} without intent field — normalise
  if (mode === "list_jobs") {
    const isFirstHR = msgCount["hr"] === 0; msgCount["hr"]++;
    appendMessage("ai", buildHRHTML({ intent: "list_jobs", response: `Found **${data.count||0}** jobs.`, data: { jobs: data.jobs||[] } }, isFirstHR), true);
    return;
  }

  if (mode === "notifications") {
    const isFirstHR = msgCount["hr"] === 0; msgCount["hr"]++;
    const notifs = data.notifications || [];
    appendMessage("ai", buildNotificationsHTML(notifs, isFirstHR), true);
    return;
  }

  const isFirstHR = msgCount["hr"] === 0;
  msgCount["hr"]++;
  appendMessage("ai", buildHRHTML(data, isFirstHR), true);
}

function buildNotificationsHTML(notifs, isFirst = false) {
  const header = isFirst ? `<div class="meta-row"><span class="badge">🤖 HR Agent</span><span class="badge amber">🔔 New Applications</span></div>` : "";
  if (!notifs.length) return header + `<p style="color:rgba(255,255,255,.45);font-size:.88rem">No applications received yet.</p>`;
  return header + `
    <p style="color:rgba(255,255,255,.6);font-size:.85rem;margin-bottom:.7rem"><strong>${notifs.length}</strong> application(s) received</p>
    ${notifs.map(n => {
      const sc = n.gap_score || 0;
      const scColor = sc >= 70 ? "#4ade80" : sc >= 50 ? "#fbbf24" : "#f87171";
      const time = n.created_at ? new Date(n.created_at).toLocaleString("en-IN", {
        day:"numeric", month:"short",
        hour:"2-digit", minute:"2-digit",
        hour12: true,
        timeZone: "Asia/Kolkata"
      }) : "";
      return `<div style="background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.09);border-left:3px solid ${scColor};border-radius:10px;padding:.75rem 1rem;margin-bottom:.5rem;font-size:.82rem;line-height:1.75">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.5rem">
          <strong style="color:#e8f2ff">${n.candidate_name || "—"}</strong>
          <span style="color:rgba(255,255,255,.35);font-size:.72rem;white-space:nowrap">${time}</span>
        </div>
        Applied for <span style="color:#7ec8f0;font-weight:600">${n.job_title || "—"}</span><br>
        Score: <strong style="color:${scColor}">${sc}/100</strong> &nbsp;·&nbsp;
        Skills: <strong>${n.skill_match_pct || 0}%</strong> &nbsp;·&nbsp;
        ${n.is_eligible ? '<span style="color:#4ade80">✅ Eligible</span>' : '<span style="color:#f87171">❌ Not eligible</span>'}
        ${!n.read ? '<span style="background:rgba(59,158,218,.2);color:#7dd3fc;border-radius:10px;padding:.05rem .45rem;font-size:.7rem;margin-left:.4rem">NEW</span>' : ""}
        <div style="margin-top:.55rem">
          <button onclick="hrViewResume('${n.candidate_id}','${(n.candidate_name||"").replace(/'/g,"")}')"
            style="background:rgba(59,158,218,.15);color:#7dd3fc;border:1px solid rgba(59,158,218,.25);padding:.28rem .75rem;border-radius:7px;font-size:.75rem;font-weight:600;cursor:pointer;font-family:inherit">
            📄 View Resume
          </button>
        </div>
      </div>`;
    }).join("")}`;
}

function buildHRHTML(data, isFirst = false) {
  const intent = data.intent || "";
  let html = isFirst ? `<div class="meta-row">
    <span class="badge">🤖 ${data.agent||"HR Agent"}</span>
    <span class="badge amber">🎯 ${intent.replace(/_/g," ")}</span>
  </div>
  <div>${md(data.response||"")}</div>` : `<div>${md(data.response||"")}</div>`;

  const d = data.data || {};

  // JD card
  if (intent === "generate_jd" && d.jd) {
    const jd = d.jd;
    const jobId = d.job_id || "";
    html += `<div style="background:rgba(124,58,237,.1);border:1px solid rgba(124,58,237,.2);border-left:3px solid #a78bfa;border-radius:12px;padding:.95rem 1.1rem;margin-top:.8rem;font-size:.82rem;line-height:1.8">
      <div class="meta-row" style="margin-bottom:.5rem">
        <span class="badge" style="background:rgba(124,58,237,.15);color:#c4b5fd;border-color:rgba(124,58,237,.25)">📄 JD Draft</span>
        <span class="badge green">💼 ${jd.title||""}</span>
        <span class="badge">📍 ${jd.location||""}</span>
        <span class="badge amber">💰 ${jd.salary||""}</span>
        <span class="badge">🕒 ${jd.minimum_experience||0}+ yrs</span>
      </div>
      <p style="margin:.4rem 0 .3rem;color:#ccdcf0"><strong>Summary:</strong> ${jd.summary||""}</p>
      <div style="margin:.5rem 0">
        <strong style="color:#e8f2ff">Required Skills:</strong><br>
        <div style="margin-top:.3rem">${(jd.mandatory_skills||[]).map(s=>`<span class="skill-tag">${s}</span>`).join("")}</div>
      </div>
      <div style="margin:.5rem 0">
        <strong style="color:#e8f2ff">Required Certifications:</strong><br>
        <div style="margin-top:.3rem">${(jd.required_certifications||[]).map(c=>`<span class="cert-tag">${c}</span>`).join("")}</div>
      </div>
      <div style="margin-top:.7rem;padding:.5rem .7rem;background:rgba(124,58,237,.08);border-radius:8px;font-size:.78rem">
        <strong style="color:#c4b5fd">Job ID:</strong> <code style="color:#a78bfa;font-size:.76rem">${jobId}</code>
      </div>
      <div style="margin-top:.6rem;display:flex;gap:.5rem;flex-wrap:wrap">
        <button onclick="copyText('${jobId}')" style="background:rgba(124,58,237,.2);color:#c4b5fd;border:1px solid rgba(124,58,237,.3);padding:.3rem .8rem;border-radius:7px;font-size:.78rem;font-weight:700;cursor:pointer;font-family:inherit">📋 Copy ID</button>
        <button onclick="hrPublishJob('${jobId}')" style="background:rgba(74,222,128,.15);color:#4ade80;border:1px solid rgba(74,222,128,.25);padding:.3rem .8rem;border-radius:7px;font-size:.78rem;font-weight:700;cursor:pointer;font-family:inherit">🌐 Publish</button>
        <button onclick="hrEditJD('${jobId}')" style="background:rgba(59,158,218,.15);color:#7dd3fc;border:1px solid rgba(59,158,218,.25);padding:.3rem .8rem;border-radius:7px;font-size:.78rem;font-weight:700;cursor:pointer;font-family:inherit">✏️ Edit JD</button>
      </div>
    </div>`;
  }

  // Rank candidates
  if (intent === "rank_candidates" && d.shortlist) {
    html += `<div style="margin-top:.8rem;font-size:.85rem;font-weight:700;color:rgba(255,255,255,.75)">
      🏆 Top ${d.shortlist.length} of ${d.total_ranked||"?"} candidates &nbsp;·&nbsp; <strong style="color:#4ade80">${d.eligible||0}</strong> eligible
    </div>
    <div class="jobs-grid" style="margin-top:.5rem">
      ${d.shortlist.map(c => {
        const sc = c.gap_score || 0;
        const scColor = sc >= 70 ? "#4ade80" : sc >= 50 ? "#fbbf24" : "#f87171";
        return `<div class="job-card" style="border-top-color:${c.is_eligible?'#4ade80':'#f87171'}">
          <h4>#${c.rank} ${c.name}</h4>
          <div class="score-bar">
            <span class="score-num" style="color:${scColor}">${sc}/100</span>
            <div class="score-track"><div class="score-fill" style="width:${sc}%;background:${scColor}"></div></div>
          </div>
          <div class="job-meta">
            ${c.is_eligible ? '<span class="tag-eligible">✅ Eligible</span>' : '<span class="tag-ineligible">❌ Not Eligible</span>'}
            <span class="tag-label">${c.eligibility_label||""}</span><br>
            🎯 Skills: <strong>${c.skill_match_pct}%</strong> &nbsp;·&nbsp; ⏱ <strong>${c.experience_years||0} yrs</strong>
            ${c.current_role ? `<br>🏷️ ${c.current_role}` : ""}
            ${c.missing_mandatory?.length
              ? `<br><span style="color:#f87171">⚠ Missing: ${c.missing_mandatory.join(", ")}</span>`
              : '<br><span style="color:#4ade80">✅ All skills present</span>'}
          </div>
          <div style="margin-top:.4rem;font-size:.72rem;color:rgba(255,255,255,.3)">
            ID: <code style="color:#7dd3fc">${shortId(c.candidate_id)}</code>
            <button onclick="copyText('${c.candidate_id}')" style="margin-left:.3rem;font-size:.7rem;padding:.12rem .4rem;background:rgba(255,255,255,.07);color:rgba(255,255,255,.5);border:1px solid rgba(255,255,255,.1);border-radius:5px;cursor:pointer;font-family:inherit">Copy</button>
          </div>
        </div>`;
      }).join("")}
    </div>`;
  }

  // List jobs
  if (intent === "list_jobs" && Array.isArray(d.jobs)) {
    html += `<div style="margin-top:.8rem;display:flex;flex-direction:column;gap:.5rem">
      ${d.jobs.length === 0
        ? '<p style="color:rgba(255,255,255,.45);font-size:.88rem">No jobs found.</p>'
        : d.jobs.map(j => {
            const statusColor = j.status === "published" ? "#4ade80" : j.status === "closed" ? "#f87171" : "#fbbf24";
            const rawSalary = j.salary || "";
            const salary = rawSalary
              ? rawSalary.replace(/(\d+)/g, n => "₹" + Number(n).toLocaleString("en-IN")).replace(/₹(\d)/g, "₹$1")
              : "—";
            return `
            <div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.09);border-left:3px solid ${statusColor};border-radius:10px;padding:.8rem 1rem;font-size:.82rem;line-height:1.85">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.5rem;margin-bottom:.3rem">
                <strong style="color:#e8f2ff;font-size:.88rem">${j.title||"—"}</strong>
                <span style="background:${statusColor}22;color:${statusColor};border:1px solid ${statusColor}44;border-radius:20px;padding:.1rem .6rem;font-size:.7rem;font-weight:700;white-space:nowrap">${j.status||"draft"}</span>
              </div>
              <div style="color:rgba(255,255,255,.55)">
                📍 ${j.location||"—"} &nbsp;·&nbsp; 💰 ${salary} &nbsp;·&nbsp; 🕒 ${j.minimum_experience||0}+ yrs
              </div>
              <div style="margin-top:.5rem;display:flex;gap:.4rem;flex-wrap:wrap;align-items:center">
                <span style="color:rgba(255,255,255,.3);font-size:.72rem">ID: <code style="background:rgba(255,255,255,.08);padding:.05rem .35rem;border-radius:4px;color:#7dd3fc">${shortId(String(j._id||""))}</code></span>
                <button onclick="copyText('${j._id||""}')" style="font-size:.7rem;padding:.18rem .55rem;background:rgba(255,255,255,.08);color:rgba(255,255,255,.6);border:1px solid rgba(255,255,255,.12);border-radius:6px;cursor:pointer;font-family:inherit">Copy ID</button>
                ${j.status !== "published"
                  ? `<button onclick="hrPublishJob('${j._id||""}')" style="font-size:.7rem;padding:.18rem .6rem;background:rgba(74,222,128,.15);color:#4ade80;border:1px solid rgba(74,222,128,.25);border-radius:6px;cursor:pointer;font-family:inherit">Publish</button>`
                  : `<button onclick="hrCloseJob('${j._id||""}')" style="font-size:.7rem;padding:.18rem .6rem;background:rgba(248,113,113,.15);color:#f87171;border:1px solid rgba(248,113,113,.25);border-radius:6px;cursor:pointer;font-family:inherit">Close</button>`}
              </div>
            </div>`;
          }).join("")}
    </div>`;
  }

  return html;
}

// ── Suggested questions ───────────────────────────────────────────────────────
function buildSuggestions(questions, isCrewContext) {
  if (!questions || !Array.isArray(questions) || !questions.length) return "";
  const chips = questions
    .filter(q => q && typeof q === "string" && q.trim())
    .map(q => {
      const display = q.replace(/\*\*(.+?)\*\*/g,"$1").replace(/\*(.+?)\*/g,"$1");
      const safe = q.replace(/`/g,"'").replace(/"/g,"&quot;");
      return `<span class="q-chip" onclick="injectQuestion(\`${safe}\`)">${display}</span>`;
    }).join("");
  if (!chips) return "";
  return `<div class="suggestions">
    <span class="suggestions-label">💡 Follow-up questions</span>
    ${chips}
  </div>`;
}

function injectQuestion(text) {
  const input = document.getElementById("user-input");
  input.value = text;
  input.focus();
  autoResize(input);
}

// ── Booking conversation context ─────────────────────────────────────────────
// Stores last extracted filters so follow-up queries stay in the same context
let bookingContext = {
  location: null,
  budget_max: null,
  budget_min: null,
  passengers: null,
  travel_month: null,
  boat_type: null,
};

function updateBookingContext(req) {
  // Only overwrite if the new query explicitly provided a value
  if (req.location)     bookingContext.location     = req.location;
  if (req.budget_max)   bookingContext.budget_max   = req.budget_max;
  if (req.budget_min)   bookingContext.budget_min   = req.budget_min;
  if (req.passengers)   bookingContext.passengers   = req.passengers;
  if (req.travel_month) bookingContext.travel_month = req.travel_month;
  if (req.boat_type && req.boat_type !== "any") bookingContext.boat_type = req.boat_type;
}

function buildContextHint() {
  const parts = [];
  if (bookingContext.location)     parts.push(`location: ${bookingContext.location}`);
  if (bookingContext.budget_max)   parts.push(`budget under ₹${bookingContext.budget_max}`);
  if (bookingContext.budget_min)   parts.push(`budget above ₹${bookingContext.budget_min}`);
  if (bookingContext.passengers)   parts.push(`${bookingContext.passengers} passengers`);
  if (bookingContext.travel_month) parts.push(`travel month: ${bookingContext.travel_month}`);
  if (bookingContext.boat_type)    parts.push(`boat type: ${bookingContext.boat_type}`);
  return parts.length > 0 ? parts.join(", ") : null;
}

function resetBookingContext() {
  bookingContext = { location: null, budget_max: null, budget_min: null,
                     passengers: null, travel_month: null, boat_type: null };
  pendingBooking = null;
}
async function crewApply(jobId, jobTitle) {
  if (!lastCandidateId) {
    appendMessage("ai", "⚠️ Please upload your resume first to apply for jobs.");
    return;
  }
  if (!confirm(`Apply for: ${jobTitle}?`)) return;

  // Disable button immediately to prevent double-click
  const btn = document.getElementById(`apply-btn-${jobId}`);
  if (btn) { btn.disabled = true; btn.textContent = "Applying…"; }

  try {
    const res  = await fetch(`${API}/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id: lastCandidateId, job_id: jobId }),
    });
    const data = await res.json();

    if (data.error) {
      if (btn) { btn.disabled = false; btn.innerHTML = "📝 Apply Now"; }
      appendMessage("ai","❌ " + data.error);
      return;
    }

    // Mark button as applied — non-clickable
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = "✅ Applied";
      btn.style.background = "rgba(255,255,255,.1)";
      btn.style.color = "rgba(255,255,255,.4)";
      btn.style.border = "1px solid rgba(255,255,255,.12)";
      btn.style.cursor = "default";
    }
    appliedJobs.add(jobId); // persist state so re-renders show Applied too

    if (data.status === "already_applied") { appendMessage("ai","ℹ️ " + data.message); return; }

    const name = data.candidate_name || "there";
    const missingList = (data.missing_mandatory||[]);
    const confirmHTML = `
      <div style="line-height:1.8">
        Hey <strong>${name}</strong> 👋<br><br>
        Your application for <strong>${data.job_title}</strong> has been successfully submitted!<br><br>
        <div style="background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.15);border-radius:10px;padding:.75rem 1rem;margin:.4rem 0">
          📊 <strong>Skill Match:</strong> ${data.skill_match_pct}%<br>
          ${data.is_eligible
            ? `✅ <strong>Status:</strong> You meet the requirements for this role`
            : `⚠️ <strong>Status:</strong> Partially meets requirements`}
          ${missingList.length ? `<br>📌 <strong>Skills to work on:</strong> ${missingList.join(", ")}` : ""}
        </div>
        <br>If you are shortlisted, the hiring team will reach out to you directly.<br>
        <span style="color:rgba(255,255,255,.45);font-size:.82rem">Good luck! 🚢</span>
      </div>`;
    appendMessage("ai", confirmHTML, true);
  } catch (e) {
    if (btn) { btn.disabled = false; btn.innerHTML = "📝 Apply Now"; }
    appendMessage("ai","❌ Could not submit: " + e.message);
  }
}

// ── HR helpers ────────────────────────────────────────────────────────────────
async function hrViewResume(candidateId, candidateName) {
  setTyping(true);
  try {
    const res  = await fetch(`${API}/hr/candidate/${candidateId}`);
    const c    = await res.json();
    setTyping(false);
    if (c.error) { appendMessage("ai","❌ " + c.error); return; }

    const info = c.personal_info || {};
    const skills = (c.skills||[]).slice(0,15).join(", ") || "—";
    const certs = (c.certifications||[]).map(cert => {
      if (typeof cert === "string") return cert;
      return cert.name || cert.title || cert.certificate || JSON.stringify(cert);
    }).filter(Boolean).join(", ") || "None";
    const expYrs = c.experience_years || 0;
    const edu    = (c.education||[]).map(e => typeof e === "string" ? e : (e.degree||e.institution||JSON.stringify(e))).join("; ") || "—";
    const exp    = (c.experience||[]).slice(0,3).map(e => typeof e === "string" ? e : (e.title||e.position||e.company||JSON.stringify(e))).join(" · ") || "—";

    const html = `
      <div style="line-height:1.8;font-size:.85rem">
        <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.7rem">
          <div style="width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#1e6fa8,#0d4a7a);display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0">👤</div>
          <div>
            <div style="font-size:1rem;font-weight:700;color:#e8f2ff">${info.name || candidateName}</div>
            <div style="color:rgba(255,255,255,.45);font-size:.78rem">${info.email||""} ${info.phone ? "· "+info.phone : ""} ${info.location ? "· "+info.location : ""}</div>
          </div>
        </div>
        ${c.summary ? `<p style="color:rgba(255,255,255,.6);margin-bottom:.7rem;font-style:italic">${c.summary}</p>` : ""}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem">
          <div style="background:rgba(255,255,255,.05);border-radius:8px;padding:.6rem .8rem">
            <div style="color:rgba(255,255,255,.4);font-size:.68rem;text-transform:uppercase;letter-spacing:.6px;margin-bottom:.3rem">Experience</div>
            <strong style="color:#e8f2ff">${expYrs} years</strong>
          </div>
          <div style="background:rgba(255,255,255,.05);border-radius:8px;padding:.6rem .8rem">
            <div style="color:rgba(255,255,255,.4);font-size:.68rem;text-transform:uppercase;letter-spacing:.6px;margin-bottom:.3rem">Education</div>
            <span style="color:#ccdcf0;font-size:.8rem">${edu}</span>
          </div>
        </div>
        <div style="margin-top:.6rem;background:rgba(255,255,255,.05);border-radius:8px;padding:.6rem .8rem">
          <div style="color:rgba(255,255,255,.4);font-size:.68rem;text-transform:uppercase;letter-spacing:.6px;margin-bottom:.35rem">Skills</div>
          <span style="color:#ccdcf0;font-size:.8rem">${skills}</span>
        </div>
        <div style="margin-top:.6rem;background:rgba(255,255,255,.05);border-radius:8px;padding:.6rem .8rem">
          <div style="color:rgba(255,255,255,.4);font-size:.68rem;text-transform:uppercase;letter-spacing:.6px;margin-bottom:.35rem">Certifications</div>
          <span style="color:#fde68a;font-size:.8rem">${certs}</span>
        </div>
        ${exp !== "—" ? `<div style="margin-top:.6rem;background:rgba(255,255,255,.05);border-radius:8px;padding:.6rem .8rem">
          <div style="color:rgba(255,255,255,.4);font-size:.68rem;text-transform:uppercase;letter-spacing:.6px;margin-bottom:.35rem">Recent Experience</div>
          <span style="color:#ccdcf0;font-size:.8rem">${exp}</span>
        </div>` : ""}
      </div>`;
    appendMessage("ai", html, true);
  } catch(e) {
    setTyping(false);
    appendMessage("ai","❌ Could not load resume: " + e.message);
  }
}

async function hrEditJD(jobId) {
  // Fetch current JD data
  setTyping(true);
  try {
    const res = await fetch(`${API}/hr/jobs/${jobId}`);
    const job = await res.json();
    setTyping(false);
    if (job.error) { appendMessage("ai", "❌ " + job.error); return; }

    const editId = `edit-${jobId}`;
    const html = `
      <div id="${editId}" style="font-size:.83rem;line-height:1.8">
        <strong style="color:#e8f2ff">✏️ Edit Job Description</strong>
        <p style="color:rgba(255,255,255,.5);font-size:.78rem;margin:.3rem 0 .8rem">Change any field below and click Save.</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.6rem">
          <div class="field-group"><label>Title</label><input id="${editId}-title" value="${job.title||""}" /></div>
          <div class="field-group"><label>Location</label><input id="${editId}-location" value="${job.location||""}" /></div>
          <div class="field-group"><label>Salary</label><input id="${editId}-salary" value="${job.salary||""}" /></div>
          <div class="field-group"><label>Vacancies</label><input id="${editId}-vacancies" type="number" value="${job.vacancies||1}" min="1"/></div>
          <div class="field-group"><label>Min Experience (yrs)</label><input id="${editId}-exp" type="number" value="${job.minimum_experience||0}" min="0"/></div>
        </div>
        <div class="field-group" style="margin-bottom:.6rem"><label>Summary</label>
          <textarea id="${editId}-summary" rows="3" style="background:#0a1828;border:1px solid rgba(59,158,218,.25);border-radius:8px;padding:.4rem .7rem;font-size:.83rem;color:#ccdcf0;font-family:inherit;outline:none;width:100%;resize:vertical">${job.summary||""}</textarea>
        </div>
        <div style="display:flex;gap:.5rem;flex-wrap:wrap">
          <button onclick="hrSaveJD('${jobId}','${editId}')"
            style="background:rgba(74,222,128,.15);color:#4ade80;border:1px solid rgba(74,222,128,.25);padding:.35rem .9rem;border-radius:7px;font-size:.8rem;font-weight:700;cursor:pointer;font-family:inherit">
            💾 Save Changes
          </button>
          <button onclick="hrPublishJob('${jobId}')"
            style="background:rgba(59,158,218,.15);color:#7dd3fc;border:1px solid rgba(59,158,218,.25);padding:.35rem .9rem;border-radius:7px;font-size:.8rem;font-weight:700;cursor:pointer;font-family:inherit">
            🌐 Save & Publish
          </button>
        </div>
      </div>`;
    appendMessage("ai", html, true);
  } catch(e) {
    setTyping(false);
    appendMessage("ai", "❌ Could not load JD: " + e.message);
  }
}

async function hrSaveJD(jobId, editId) {
  const updates = {
    title:              document.getElementById(`${editId}-title`)?.value.trim(),
    location:           document.getElementById(`${editId}-location`)?.value.trim(),
    salary:             document.getElementById(`${editId}-salary`)?.value.trim(),
    vacancies:          parseInt(document.getElementById(`${editId}-vacancies`)?.value) || 1,
    minimum_experience: parseInt(document.getElementById(`${editId}-exp`)?.value) || 0,
    summary:            document.getElementById(`${editId}-summary`)?.value.trim(),
  };
  // Remove empty fields
  Object.keys(updates).forEach(k => { if (!updates[k] && updates[k] !== 0) delete updates[k]; });

  try {
    const res  = await fetch(`${API}/hr/jobs/${jobId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    const data = await res.json();
    if (data.error) { appendMessage("ai","❌ " + data.error); return; }
    appendMessage("ai", `✅ JD updated successfully!\n\n**${updates.title || "Job"}** has been saved. You can now publish it using the Publish button.`);
  } catch(e) {
    appendMessage("ai", "❌ Save failed: " + e.message);
  }
}

async function hrPublishJob(jobId) {
  try {
    const res  = await fetch(`${API}/hr/jobs/${jobId}/publish`, { method: "POST" });
    const data = await res.json();
    appendMessage("ai", data.response || `✅ Job ${shortId(jobId)} published successfully!`);
  } catch (e) {
    appendMessage("ai","❌ Publish failed: " + e.message);
  }
}

async function hrCloseJob(jobId) {
  try {
    const res  = await fetch(`${API}/hr/jobs/${jobId}/close`, { method: "POST" });
    const data = await res.json();
    appendMessage("ai", data.response || `Job ${shortId(jobId)} closed.`);
  } catch (e) {
    appendMessage("ai","❌ Close failed: " + e.message);
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    // Brief visual feedback via a transient message
    const toast = document.createElement("div");
    toast.textContent = "✅ Copied!";
    toast.style.cssText = "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1a2332;color:#fff;padding:.4rem 1.2rem;border-radius:20px;font-size:.82rem;z-index:9999;pointer-events:none;";
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 1800);
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  updateHeaderDot("booking");
  showWelcomeIfEmpty();

  // Wire attach button to file input
  const attachBtn = document.getElementById("attach-btn");
  if (attachBtn) {
    attachBtn.addEventListener("click", () => {
      document.getElementById("c-file").click();
    });
    // Hidden by default (booking is default agent)
    attachBtn.classList.add("hidden");
  }
});






