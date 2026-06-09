const API = "http://localhost:4000";

// ── Markdown → HTML (lightweight) ────────────────────────────────────────────
function md(text) {
  if (!text || typeof text !== "string") return "";

  // Strip any leaked ---QUESTIONS--- block from response text
  if (text.includes("---QUESTIONS---")) {
    text = text.split("---QUESTIONS---")[0].trim();
  }

  return text
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    // headings
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm,  "<h2>$1</h2>")
    .replace(/^# (.+)$/gm,   "<h1>$1</h1>")
    // bold + italic
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g,     "<strong>$1</strong>")
    // bullet lists: handle *, +, - as list markers
    .replace(/(^[*+\-] .+$\n?)+/gm, match => {
      const items = match.trim().split("\n")
        .map(l => `<li>${l.replace(/^[*+\-] /,"")}</li>`).join("");
      return `<ul>${items}</ul>`;
    })
    // remaining single * for italic (not bullet)
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // line breaks
    .replace(/\n{2,}/g, "</p><p>")
    .replace(/\n/g, "<br>");
}

// ── Tab switching ─────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(t => t.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.remove("hidden");
  });
});

document.querySelectorAll(".sub-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".sub-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".sub-content").forEach(t => t.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById("sub-" + btn.dataset.sub).classList.remove("hidden");
  });
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function show(id)   { document.getElementById(id).classList.remove("hidden"); }
function hide(id)   { document.getElementById(id).classList.add("hidden"); }
function setText(id, html) { document.getElementById(id).innerHTML = html; }

function statusClass(s) {
  if (!s) return "";
  s = s.toLowerCase();
  if (s.includes("fully")) return "status-booked";
  if (s.includes("partial")) return "status-partial";
  return "status-available";
}
function statusLabel(s) {
  if (!s) return "Available";
  s = s.toLowerCase();
  if (s.includes("fully")) return "🔴 Fully Booked";
  if (s.includes("partial")) return "🟡 Partially Booked";
  return "🟢 Available";
}

function renderQuestions(questions, targetQueryId) {
  if (!questions || !Array.isArray(questions) || !questions.length) return "";
  const chips = questions
    .filter(q => q && typeof q === "string" && q.trim().length > 0)
    .map(q => {
      const safe    = q.replace(/`/g, "'").replace(/"/g, "&quot;");
      // Strip markdown from display text but keep plain text readable
      const display = q
        .replace(/\*\*(.+?)\*\*/g, "$1")
        .replace(/\*(.+?)\*/g,     "$1")
        .replace(/`(.+?)`/g,       "$1");
      return `<span class="q-chip" onclick="fillQuery('${targetQueryId}', \`${safe}\`)">${display}</span>`;
    }).join("");
  if (!chips) return "";
  return `<div class="questions-section" style="margin-top:1rem">
    <h4>💡 Suggested follow-up questions</h4>${chips}</div>`;
}

function fillQuery(id, text) {
  const el = document.getElementById(id);
  if (el) { el.value = text; el.focus(); }
}

function renderThought(thought) {
  if (!thought || !thought.length) return "";
  const lines = thought.map(t => `<p>${t}</p>`).join("");
  return `<div class="thought-section" style="margin-top:1rem">
    <p style="color:#aaa;margin-bottom:0.5rem;font-size:0.75rem">AGENT REASONING</p>
    ${lines}</div>`;
}

// ── BOOKING ───────────────────────────────────────────────────────────────────
async function runBooking() {
  const query   = document.getElementById("b-query").value.trim();
  const name    = document.getElementById("b-name").value.trim() || "Guest";
  const payment = document.getElementById("b-payment").value;
  const confirm = document.getElementById("b-confirm").value === "true";
  const thought = document.getElementById("b-thought").value === "true";

  if (!query) { alert("Please enter a query"); return; }

  hide("b-result"); hide("b-error");
  show("b-loading");

  try {
    const params = new URLSearchParams({
      query, user_name: name,
      confirm_booking: confirm,
      payment_method: payment,
      include_thought_process: thought,
    });
    const res  = await fetch(`${API}/booking/run?${params}`, { method: "POST" });
    const data = await res.json();
    hide("b-loading");

    if (data.error) {
      setText("b-error", `<strong>❌ ${data.error}</strong>${data.response ? "<br><br>" + md(data.response) : ""}`);
      show("b-error"); return;
    }

    show("b-result");
    setText("b-result", renderBookingResult(data, thought));

  } catch (e) {
    hide("b-loading");
    const msg = e.message === "Failed to fetch"
      ? "❌ Cannot reach server. Check your internet connection or if the server is running."
      : "❌ Server error: " + e.message;
    setText("b-error", msg);
    show("b-error");
  }
}

function renderBookingResult(data, showThought) {
  const meta = `
    <div class="meta-row">
      <span class="badge">🤖 ${data.agent}</span>
      <span class="badge green">👤 ${data.user_name}</span>
      <span class="badge orange">🎯 ${String(data.intent||"").replace("_"," ")}</span>
      <span class="badge">🚢 ${data.data?.total_boats_found ?? 0} boats found</span>
    </div>`;

  // Response text
  const response = `<div class="response-card">
    <div class="rc-title">📋 Agent Response</div>
    <p>${md(data.response)}</p>
  </div>`;

  // Boat cards
  const boats = data.data?.top_recommendations || [];
  const boatCards = boats.length ? `
    <h3 style="margin:1rem 0 0.6rem;color:#0d47a1">🚢 Top Recommendations</h3>
    <div class="boats-grid">
      ${boats.map(b => `
        <div class="boat-card">
          <h4>${b.name}</h4>
          <div class="price">₹${(b.price_per_day||0).toLocaleString()}/day</div>
          <div class="boat-meta">
            <span class="${statusClass(b.booking_status)}">${statusLabel(b.booking_status)}</span><br>
            📍 ${b.location || "—"} &nbsp;|&nbsp; 🧑‍🤝‍🧑 Capacity: ${b.capacity}<br>
            ⭐ ${b.rating} rating &nbsp;|&nbsp; ${b.type}<br>
            👨‍✈️ ${(b.crew||[]).join(", ") || "—"}<br>
            🎯 ${(b.activities||[]).join(", ") || "—"}<br>
            🏷️ ${(b.amenities||[]).slice(0,4).join(", ")}
          </div>
        </div>`).join("")}
    </div>` : "";

  // Booking confirmation
  const booking = data.data?.booking;
  const bookingHtml = booking ? `
    <div class="confirm-card">
      <h3>✅ Booking Confirmed!</h3>
      <div class="meta-row">
        <span class="badge green">🆔 ${booking.booking_id}</span>
        <span class="badge green">🚢 ${booking.boat_name}</span>
        <span class="badge green">📅 ${booking.travel_date}</span>
        <span class="badge green">💳 Txn: ${booking.transaction_id?.slice(0,12)}...</span>
      </div>
    </div>` : "";

  const questions = renderQuestions(data.suggested_questions, "b-query");
  const thoughtHtml = showThought ? renderThought(data.thought_process) : "";

  return meta + response + boatCards + bookingHtml + questions + thoughtHtml;
}

// ── CREW: Upload ──────────────────────────────────────────────────────────────
// Store last candidate_id for apply button
let _lastCandidateId = "";

async function runCrewUpload() {
  const query  = document.getElementById("c-query-upload").value.trim();
  const file   = document.getElementById("c-file").files[0];
  const thought= document.getElementById("c-thought-upload").value === "true";

  if (!query) { alert("Please enter a query"); return; }
  if (!file)  { alert("Please select a resume file"); return; }

  hide("c-result"); hide("c-error");
  show("c-loading");

  try {
    const form = new FormData();
    form.append("query",   query);
    form.append("file",    file);
    form.append("save_candidate", true);  // always save
    form.append("include_thought_process", thought);

    const res  = await fetch(`${API}/agent/run-with-resume`, { method: "POST", body: form });
    const data = await res.json();
    hide("c-loading");

    if (data.error) {
      setText("c-error", `❌ ${data.error}`);
      show("c-error"); return;
    }

    show("c-result");
    _lastCandidateId = data.candidate_id || data.data?.candidate_id || "";
    setText("c-result", renderCrewResult(data, thought));

  } catch (e) {
    hide("c-loading");
    const msg = e.message === "Failed to fetch"
      ? "❌ Cannot reach server. Check your internet connection or if the server is running."
      : "❌ Server error: " + e.message;
    setText("c-error", msg);
    show("c-error");
  }
}

// ── CREW: ID ──────────────────────────────────────────────────────────────────
async function runCrewId() {
  const query  = document.getElementById("c-query-id").value.trim();
  const cid    = document.getElementById("c-id").value.trim();
  const thought= document.getElementById("c-thought-id").value === "true";

  if (!query) { alert("Please enter a query"); return; }
  if (!cid)   { alert("Please enter a candidate ID"); return; }

  hide("c-result"); hide("c-error");
  show("c-loading");

  try {
    const res  = await fetch(`${API}/agent/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, candidate_id: cid, include_thought_process: thought }),
    });
    const data = await res.json();
    hide("c-loading");

    if (data.error) {
      setText("c-error", `❌ ${data.error}`);
      show("c-error"); return;
    }

    show("c-result");
    _lastCandidateId = cid;
    setText("c-result", renderCrewResult(data, thought));

  } catch (e) {
    hide("c-loading");
    setText("c-error", "❌ Server error: " + e.message);
    show("c-error");
  }
}

function renderCrewResult(data, showThought) {
  const meta = `
    <div class="meta-row">
      <span class="badge">🤖 ${data.agent}</span>
      <span class="badge green">👤 ${data.candidate_name || "—"}</span>
      <span class="badge orange">🎯 ${String(data.intent||"").replace("_"," ")}</span>
      <span class="badge">💼 ${data.data?.eligible_jobs ?? 0} / ${data.data?.total_jobs ?? 0} eligible</span>
    </div>`;

  const response = `<div class="response-card">
    <div class="rc-title">📋 Agent Response</div>
    <p>${md(data.response)}</p>
  </div>`;

  // Job cards from best_matches or skill_gap_report
  const matches = data.data?.best_matches || data.data?.skill_gap_report || [];
  const jobCards = matches.length ? `
    <h3 style="margin:1.2rem 0 0.7rem;color:#1b5e20;font-size:1rem;font-weight:700">💼 Job Results</h3>
    <div class="jobs-grid">
      ${matches.map(j => {
        const score = j.gap_score ?? j.skill_match_pct ?? 0;
        const eligible = j.is_eligible;
        const borderColor = eligible ? "#198754" : "#dc3545";
        const scoreColor  = score >= 70 ? "#198754" : score >= 50 ? "#e65100" : "#dc3545";
        const salary  = j.salary  || "";
        const loc     = j.location || "";
        const minExp  = j.minimum_experience != null ? j.minimum_experience + "+ yrs" : "";
        const jobId   = j.job_id || "";
        const shortJobId = jobId ? jobId.slice(0,8)+"…" : "";
        return `
        <div class="job-card" style="border-top-color:${borderColor}">
          <h4 style="font-size:.95rem;font-weight:700;color:#0b1f3a">${j.title || j.job_title || "—"}</h4>
          <div class="score" style="color:${scoreColor};font-size:1rem;font-weight:800">Score: ${score}</div>
          <div class="job-meta" style="margin-top:.5rem;font-size:.82rem;line-height:1.85">
            ${eligible !== undefined
              ? (eligible
                  ? '<span style="color:#198754;font-weight:700">✅ Eligible</span>'
                  : '<span style="color:#dc3545;font-weight:700">❌ Not Eligible</span>')
              : ""}
            ${j.eligibility_label ? `&nbsp;<em style="color:#555">${j.eligibility_label}</em>` : ""}
            ${j.skill_match_pct != null ? `<br>🎯 <strong>Skill match:</strong> ${j.skill_match_pct}%` : ""}
            ${loc     ? `<br>📍 ${loc}` : ""}
            ${salary  ? `<br>💰 <strong>${salary}</strong>` : ""}
            ${minExp  ? `<br>🕒 Requires: ${minExp}` : ""}
            ${j.experience_years != null ? `<br>👤 Your exp: <strong>${j.experience_years} yrs</strong>` : ""}
            ${j.missing_mandatory?.length
              ? `<br><span style="color:#c62828">⚠️ <strong>Missing:</strong> ${j.missing_mandatory.join(", ")}</span>` : ""}
            ${j.missing_certs?.length
              ? `<br><span style="color:#e65100">📜 <strong>Certs needed:</strong> ${j.missing_certs.join(", ")}</span>` : ""}
            ${j.present_skills?.length
              ? `<br><span style="color:#1b5e20">✔ <strong>Has:</strong> ${j.present_skills.slice(0,4).join(", ")}</span>` : ""}
          </div>
          ${eligible && jobId ? `
          <div style="margin-top:.7rem;display:flex;gap:.4rem;flex-wrap:wrap;align-items:center">
            <button onclick="crewApply('${jobId}', '${(j.title||j.job_title||'').replace(/'/g,'')}')"
              style="background:linear-gradient(135deg,#198754,#0d6832);color:#fff;border:none;padding:.35rem .9rem;border-radius:6px;font-size:.8rem;font-weight:700;cursor:pointer">
              📝 Apply
            </button>
            ${shortJobId ? `<span style="font-size:.72rem;color:#999">Job: <code>${shortJobId}</code></span>` : ""}
          </div>` : ""}
        </div>`;
      }).join("")}
    </div>` : "";

  const questions  = renderQuestions(data.suggested_questions, "c-query-upload");
  const thoughtHtml = showThought ? renderThought(data.thought_process) : "";

  return meta + response + jobCards + questions + thoughtHtml;
}

async function crewApply(jobId, jobTitle) {
  if (!_lastCandidateId) {
    alert("Please upload your resume first to apply for jobs.");
    return;
  }
  if (!confirm(`Apply for: ${jobTitle}?`)) return;

  try {
    const res  = await fetch(`${API}/apply`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ candidate_id: _lastCandidateId, job_id: jobId }),
    });
    const data = await res.json();

    if (data.error) { alert("❌ " + data.error); return; }
    if (data.status === "already_applied") { alert(`ℹ️ ${data.message}`); return; }

    const msg = data.is_eligible
      ? `✅ Successfully applied for "${data.job_title}"!\n\nSkill Match: ${data.skill_match_pct}%\nYou are a strong match for this role! 🎉`
      : `⚠️ Applied for "${data.job_title}".\n\nSkill Match: ${data.skill_match_pct}%\nYou may not fully meet all requirements.\nMissing skills: ${(data.missing_mandatory||[]).join(", ")||"None"}`;

    alert(msg);
  } catch (e) {
    alert("❌ Could not submit application: " + e.message);
  }
}

// ══════════════════════════════════════════════════════════════
// HR AGENT
// ══════════════════════════════════════════════════════════════

async function hrCall(endpoint, body, method = "POST") {
  hide("hr-result"); hide("hr-error");
  show("hr-loading");
  try {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res  = await fetch(`${API}${endpoint}`, opts);
    const data = await res.json();
    hide("hr-loading");
    if (data.error) {
      setText("hr-error", `<strong>❌ ${data.error}</strong>`);
      show("hr-error"); return null;
    }
    return data;
  } catch(e) {
    hide("hr-loading");
    setText("hr-error", `❌ Server error: ${e.message}`);
    show("hr-error"); return null;
  }
}

function renderHRResult(data) {
  if (!data) return;
  const intent = data.intent || "";

  // Helper: shorten MongoDB ID to first 8 chars
  const shortId = (id) => id ? id.toString().slice(0, 8) + "…" : "";

  let html = `<div class="response-card">
    <div class="rc-title">🧑‍💼 ${data.agent || "HR Agent"} — <em>${intent.replace(/_/g," ")}</em></div>
    <p>${md(data.response || "")}</p>
  </div>`;

  const d = data.data || {};

  // ── JD card ──────────────────────────────────────────────────────────────
  if (intent === "generate_jd" && d.jd) {
    const jd    = d.jd;
    const jobId = d.job_id || "";
    html += `<div class="card" style="border-top:3px solid #7c3aed;margin-top:1rem">
      <div class="meta-row">
        <span class="badge" style="background:#ede9fe;color:#6d28d9">📄 JD Draft</span>
        <span class="badge green">💼 ${jd.title||""}</span>
        <span class="badge">📍 ${jd.location||""}</span>
        <span class="badge amber">💰 ${jd.salary||""}</span>
        <span class="badge">🕒 ${jd.minimum_experience||0}+ yrs</span>
      </div>

      <p style="margin:.7rem 0 .3rem;font-size:.9rem"><strong>Summary:</strong> ${jd.summary||""}</p>
      <p style="margin:.3rem 0"><strong>Department:</strong> ${jd.department||""}</p>

      <div style="margin:.7rem 0">
        <strong>Mandatory Skills:</strong>
        <div style="margin-top:.3rem;display:flex;flex-wrap:wrap;gap:.3rem">
          ${(jd.mandatory_skills||[]).map(s=>`<span style="background:#e3f2fd;color:#0d47a1;padding:.15rem .6rem;border-radius:12px;font-size:.78rem;font-weight:600">${s}</span>`).join("")}
        </div>
      </div>

      <div style="margin:.5rem 0">
        <strong>Required Certifications:</strong>
        <div style="margin-top:.3rem;display:flex;flex-wrap:wrap;gap:.3rem">
          ${(jd.required_certifications||[]).map(c=>`<span style="background:#fff3cd;color:#856404;padding:.15rem .6rem;border-radius:12px;font-size:.78rem;font-weight:600">${c}</span>`).join("")}
        </div>
      </div>

      <div style="margin:.5rem 0">
        <strong>Responsibilities:</strong>
        <ul style="padding-left:1.3rem;margin-top:.3rem;font-size:.88rem;line-height:1.8">
          ${(jd.responsibilities||[]).map(r=>`<li>${r}</li>`).join("")}
        </ul>
      </div>

      <div style="margin:.5rem 0">
        <strong>Benefits:</strong>
        <ul style="padding-left:1.3rem;margin-top:.3rem;font-size:.88rem;line-height:1.8">
          ${(jd.benefits||[]).map(b=>`<li>${b}</li>`).join("")}
        </ul>
      </div>

      <div style="margin-top:1rem;padding:.6rem;background:#f8f4ff;border-radius:8px;font-size:.82rem;color:#6d28d9;word-break:break-all">
        <strong>Job ID:</strong> <code style="font-size:.8rem">${shortId(jobId)}</code>
        <span style="color:#999;font-size:.75rem"> (full: ${jobId})</span>
      </div>

      <div style="margin-top:.8rem;display:flex;gap:.6rem;flex-wrap:wrap">
        <button class="btn-primary" style="font-size:.82rem;padding:.4rem 1rem"
          onclick="copyToClipboard('${jobId}','hr-rank-jobid')">📋 Copy ID</button>
        <button class="btn-primary" style="font-size:.82rem;padding:.4rem 1rem;background:linear-gradient(135deg,#198754,#0d6832)"
          onclick="hrPublishJob('${jobId}')">🌐 Publish Job</button>
      </div>
    </div>`;
  }

  // ── Candidate ranking ─────────────────────────────────────────────────────
  if (intent === "rank_candidates" && d.shortlist) {
    html += `<div class="section-header" style="margin:1.2rem 0 .7rem;font-size:1rem;font-weight:700;color:#0b1f3a">
      🏆 Shortlisted Candidates (Top ${d.shortlist.length} of ${d.total_ranked||"?"})
      &nbsp;<span style="font-size:.8rem;color:#555;font-weight:400">Eligible: <strong>${d.eligible||0}</strong></span>
    </div>
    <div class="jobs-grid">
      ${d.shortlist.map(c => {
        const sc = c.gap_score || 0;
        const scColor = sc >= 70 ? "#198754" : sc >= 50 ? "#e65100" : "#dc3545";
        return `
        <div class="job-card" style="border-top-color:${c.is_eligible?'#198754':'#dc3545'}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <h4 style="font-size:.93rem;font-weight:700;color:#0b1f3a">#${c.rank} ${c.name}</h4>
            <span class="badge ${c.is_eligible?'green':'red'}" style="font-size:.72rem">${c.is_eligible?"✅":"❌"}</span>
          </div>
          <div class="score" style="color:${scColor};font-size:.98rem;font-weight:800">Score: ${sc}</div>
          <div class="job-meta" style="margin-top:.4rem;font-size:.8rem;line-height:1.8">
            🎯 Skill match: <strong>${c.skill_match_pct}%</strong><br>
            <em style="color:#555">${c.eligibility_label||""}</em><br>
            👤 Exp: <strong>${c.experience_years||0} yrs</strong>
            ${c.current_role ? `<br>🏷️ Background: <em>${c.current_role}</em>` : ""}
            ${c.missing_mandatory?.length
              ? `<br><span style="color:#c62828">⚠️ Missing: <strong>${c.missing_mandatory.join(", ")}</strong></span>`
              : '<br><span style="color:#198754">✅ No missing mandatory skills</span>'}
            ${c.missing_certs?.length
              ? `<br><span style="color:#e65100">📜 Certs: ${c.missing_certs.join(", ")}</span>`
              : ""}
          </div>
          <div style="margin-top:.5rem;font-size:.75rem;color:#888">
            ID: <code>${shortId(c.candidate_id)}</code>
            <button onclick="copyToClipboard('${c.candidate_id}','hr-gap-cid')"
              style="margin-left:.4rem;font-size:.7rem;padding:.1rem .4rem;border:1px solid #dce5f0;border-radius:4px;cursor:pointer;background:#f8fafc">
              Copy
            </button>
          </div>
        </div>`;
      }).join("")}
    </div>`;
  }

  // ── Skill gap ─────────────────────────────────────────────────────────────
  if (intent === "skill_gap" && d.gap_score !== undefined) {
    const sc = d.gap_score || 0;
    const scColor = sc >= 70 ? "#198754" : sc >= 50 ? "#e65100" : "#dc3545";
    html += `<div class="card" style="border-top:3px solid #0dcaf0;margin-top:1rem">
      <div class="meta-row">
        <span class="badge">👤 <strong>${d.candidate_name||""}</strong></span>
        <span class="badge amber">💼 ${d.job_title||""}</span>
        <span class="badge ${d.is_eligible?'green':'red'}">${d.is_eligible?"✅ Eligible":"❌ Not Eligible"}</span>
        <span class="badge" style="color:${scColor};font-weight:800">Score: ${sc}</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin-top:.6rem;font-size:.85rem">
        <div><strong>Skill Match:</strong> <span style="color:${scColor}">${d.skill_match_pct}%</span></div>
        <div><strong>Experience:</strong> ${d.experience_years||0} yrs</div>
      </div>
      <div style="margin-top:.7rem">
        <strong>✔ Present Skills:</strong>
        <div style="margin-top:.3rem;display:flex;flex-wrap:wrap;gap:.3rem">
          ${(d.present_skills||[]).length
            ? (d.present_skills||[]).map(s=>`<span style="background:#d1fae5;color:#065f46;padding:.15rem .6rem;border-radius:12px;font-size:.78rem">${s}</span>`).join("")
            : '<span style="color:#888;font-size:.83rem">None</span>'}
        </div>
      </div>
      <div style="margin-top:.6rem">
        <strong style="color:#c62828">⚠️ Missing Mandatory Skills:</strong>
        <div style="margin-top:.3rem;display:flex;flex-wrap:wrap;gap:.3rem">
          ${(d.missing_mandatory||[]).length
            ? (d.missing_mandatory||[]).map(s=>`<span style="background:#fee2e2;color:#991b1b;padding:.15rem .6rem;border-radius:12px;font-size:.78rem;font-weight:600">${s}</span>`).join("")
            : '<span style="color:#198754;font-size:.83rem">None ✅</span>'}
        </div>
      </div>
      <div style="margin-top:.6rem">
        <strong style="color:#e65100">📜 Missing Certifications:</strong>
        <div style="margin-top:.3rem;display:flex;flex-wrap:wrap;gap:.3rem">
          ${(d.missing_certs||[]).length
            ? (d.missing_certs||[]).map(c=>`<span style="background:#fff3cd;color:#856404;padding:.15rem .6rem;border-radius:12px;font-size:.78rem;font-weight:600">${c}</span>`).join("")
            : '<span style="color:#198754;font-size:.83rem">None ✅</span>'}
        </div>
      </div>
    </div>`;
  }

  // ── Recruitment report ────────────────────────────────────────────────────
  if (intent === "recruitment_report" && d.report) {
    const r = d.report;
    html += `<div class="card" style="border-top:3px solid #fd7e14;margin-top:1rem">
      <h3 style="color:#7c4a00;margin-bottom:.8rem;font-size:1rem">${r.report_title||"Recruitment Report"}</h3>
      <div class="meta-row">
        <span class="badge amber">👥 <strong>${r.total_applicants}</strong> applicants</span>
        <span class="badge green">✅ <strong>${r.eligible_count}</strong> eligible</span>
        <span class="badge">📋 <strong>${r.shortlisted_count}</strong> shortlisted</span>
      </div>
      <p style="margin:.7rem 0 .3rem;font-size:.88rem"><strong>Executive Summary:</strong> ${r.executive_summary||""}</p>
      <p style="font-size:.88rem"><strong>Top Candidates:</strong> ${r.top_candidates_analysis||""}</p>
      <div style="margin:.6rem 0">
        <strong>Common Skill Gaps:</strong>
        <div style="margin-top:.3rem;display:flex;flex-wrap:wrap;gap:.3rem">
          ${(r.common_skill_gaps||[]).map(g=>`<span style="background:#fee2e2;color:#991b1b;padding:.15rem .6rem;border-radius:12px;font-size:.78rem">${g}</span>`).join("") || "None"}
        </div>
      </div>
      <p style="font-size:.88rem;margin:.4rem 0"><strong>Hiring Recommendation:</strong> <em>${r.hiring_recommendation||""}</em></p>
      <strong>Next Steps:</strong>
      <ul style="padding-left:1.3rem;margin-top:.3rem;font-size:.85rem;line-height:1.8">
        ${(r.next_steps||[]).map(s=>`<li>${s}</li>`).join("")}
      </ul>
    </div>`;
  }

  // ── Interview summary ─────────────────────────────────────────────────────
  if (intent === "interview_summary") {
    const rec      = data.data?.recommendation || "";
    const recColor = {"hire":"#198754","hold":"#e65100","reject":"#dc3545"}[rec] || "#555";
    const stars    = "⭐".repeat(data.data?.interview_rating || 0);
    html += `<div class="card" style="border-top:3px solid ${recColor};margin-top:1rem">
      <div class="meta-row">
        <span class="badge">👤 <strong>${data.data?.candidate_name||""}</strong></span>
        <span class="badge amber">💼 ${data.data?.job_title||""}</span>
        <span class="badge" style="background:${recColor};color:#fff;font-weight:700">
          ${rec.toUpperCase()||""}
        </span>
        <span class="badge" title="Rating">${stars} ${data.data?.interview_rating||0}/5</span>
      </div>
      <p style="margin:.6rem 0 .3rem;font-size:.88rem"><strong>Overall Impression:</strong> <em>${data.data?.overall_impression||""}</em></p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin-top:.6rem;font-size:.85rem">
        <div>
          <strong style="color:#198754">✔ Strengths:</strong>
          <ul style="padding-left:1.1rem;margin-top:.2rem;line-height:1.8">
            ${(data.data?.strengths||[]).map(s=>`<li>${s}</li>`).join("")}
          </ul>
        </div>
        <div>
          <strong style="color:#c62828">⚠ Concerns:</strong>
          <ul style="padding-left:1.1rem;margin-top:.2rem;line-height:1.8">
            ${(data.data?.concerns||[]).length
              ? (data.data?.concerns||[]).map(c=>`<li>${c}</li>`).join("")
              : "<li style='color:#888'>None</li>"}
          </ul>
        </div>
      </div>
      <p style="margin-top:.6rem;font-size:.85rem"><strong>Technical Assessment:</strong> ${data.data?.technical_assessment||""}</p>
      <p style="font-size:.85rem;margin-top:.3rem"><strong>Reason:</strong> ${data.data?.recommendation_reason||""}</p>
    </div>`;
  }

  setText("hr-result", html);
  show("hr-result");
}

// HR actions
async function hrGenerateJD() {
  const data = await hrCall("/hr/generate-jd", {
    role:             document.getElementById("hr-role").value.trim() || "Chief Officer",
    location:         document.getElementById("hr-location").value.trim() || "Mumbai",
    experience_years: parseInt(document.getElementById("hr-exp").value) || 3,
    extra_context:    document.getElementById("hr-context").value.trim(),
  });
  renderHRResult(data);
}

async function hrRankCandidates() {
  const job_id = document.getElementById("hr-rank-jobid").value.trim();
  if (!job_id) { alert("Enter a Job ID"); return; }
  const data = await hrCall("/hr/rank-candidates", { job_id });
  renderHRResult(data);
}

async function hrSkillGap() {
  const candidate_id = document.getElementById("hr-gap-cid").value.trim();
  const job_id       = document.getElementById("hr-gap-jid").value.trim();
  if (!candidate_id || !job_id) { alert("Fill both Candidate ID and Job ID"); return; }
  const data = await hrCall("/hr/skill-gap", { candidate_id, job_id });
  renderHRResult(data);
}

async function hrReport() {
  const job_id = document.getElementById("hr-report-jid").value.trim();
  if (!job_id) { alert("Enter a Job ID"); return; }
  const data = await hrCall("/hr/recruitment-report", { job_id });
  renderHRResult(data);
}

async function hrInterview() {
  const notes = document.getElementById("hr-int-notes").value.trim();
  if (!notes) { alert("Enter interview notes"); return; }
  const data = await hrCall("/hr/interview-summary", {
    candidate_name:   document.getElementById("hr-int-name").value.trim() || "Candidate",
    job_title:        document.getElementById("hr-int-title").value.trim() || "Maritime Role",
    interview_notes:  notes,
    interview_rating: parseInt(document.getElementById("hr-int-rating").value),
    job_id:           document.getElementById("hr-int-jid").value.trim(),
  });
  renderHRResult(data);
}

async function hrPublishJob(jobId) {
  const data = await hrCall(`/hr/jobs/${jobId}/publish`, null, "POST");
  if (data) {
    alert(`✅ Job published! Crew can now see this job.`);
    renderHRResult(data);
  }
}

async function hrListJobs() {
  const status = document.getElementById("hr-jobs-filter").value;
  const url    = status ? `/hr/jobs?status=${status}` : `/hr/jobs`;
  hide("hr-error");
  show("hr-loading");
  try {
    const res  = await fetch(`${API}${url}`);
    const data = await res.json();
    hide("hr-loading");
    const jobs = data.jobs || [];
    if (!jobs.length) {
      setText("hr-jobs-list", `<p style="color:#888">No jobs found.</p>`); return;
    }
    const statusColor = { draft:"#6d28d9", published:"#198754", closed:"#dc3545" };
    setText("hr-jobs-list", `<div class="jobs-grid">${jobs.map(j => `
      <div class="job-card" style="border-top-color:${statusColor[j.status]||'#888'}">
        <div style="display:flex;justify-content:space-between">
          <h4>${j.title||j.role||"?"}</h4>
          <span class="badge" style="background:${statusColor[j.status]||'#eee'};color:#fff;font-size:.7rem">${(j.status||"").toUpperCase()}</span>
        </div>
        <div class="job-meta">
          📍 ${j.location||"?"} &nbsp;|&nbsp; 💰 ${j.salary||"?"}
          &nbsp;|&nbsp; 🧑‍💼 ${j.minimum_experience||0}+ yrs<br>
          🔑 ${(j.mandatory_skills||[]).slice(0,3).join(", ")}
        </div>
        <div style="margin-top:.6rem;display:flex;gap:.4rem;flex-wrap:wrap">
          <button onclick="copyToClipboard('${j._id}','hr-rank-jobid')"
            style="font-size:.75rem;padding:.25rem .7rem;border:1px solid #dce5f0;border-radius:6px;cursor:pointer;background:#f8fafc">
            📋 Copy ID
          </button>
          ${j.status==="draft"?`<button onclick="hrPublishJob('${j._id}')"
            style="font-size:.75rem;padding:.25rem .7rem;border:none;border-radius:6px;cursor:pointer;background:#198754;color:#fff">
            🌐 Publish
          </button>`:""}
          ${j.status==="published"?`<button onclick="hrCloseJob('${j._id}')"
            style="font-size:.75rem;padding:.25rem .7rem;border:none;border-radius:6px;cursor:pointer;background:#dc3545;color:#fff">
            ✖ Close
          </button>`:""}
        </div>
      </div>`).join("")}</div>`);
  } catch(e) {
    hide("hr-loading");
    setText("hr-error", `❌ ${e.message}`);
    show("hr-error");
  }
}

async function hrCloseJob(jobId) {
  if (!confirm(`Close job ${jobId}?`)) return;
  const data = await hrCall(`/hr/jobs/${jobId}/close`, null, "POST");
  if (data) { alert("Job closed."); hrListJobs(); }
}

function copyToClipboard(val, targetId) {
  navigator.clipboard?.writeText(val);
  const el = document.getElementById(targetId);
  if (el) { el.value = val; el.focus(); }
  alert(`Copied: ${val}`);
}
