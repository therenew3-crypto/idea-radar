// 정적 대시보드 — docs/data/*.json 을 읽어 렌더한다. 빌드 도구 불필요.
const $ = (sel) => document.querySelector(sel);
const app = $("#app");
let current = null;
let activeTab = "ideas";

const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function init() {
  let index;
  try {
    index = await fetch("data/index.json", { cache: "no-store" }).then((r) => r.json());
  } catch {
    app.innerHTML = `<div class="warn">아직 생성된 데이터가 없습니다. 파이프라인(run.py)을 한 번 실행하세요.</div>`;
    return;
  }
  const select = $("#date-select");
  select.innerHTML = index.dates.map((d) => `<option value="${d}">${d}</option>`).join("");
  select.addEventListener("change", () => loadDate(select.value));

  document.querySelectorAll(".tabs button").forEach((btn) =>
    btn.addEventListener("click", () => {
      activeTab = btn.dataset.tab;
      document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
      render();
    })
  );

  if (index.latest) loadDate(index.latest);
}

async function loadDate(d) {
  $("#status").textContent = "불러오는 중…";
  current = await fetch(`data/${d}.json`, { cache: "no-store" }).then((r) => r.json());
  $("#status").textContent = `갱신: ${d}`;
  render();
}

function render() {
  if (!current) return;
  let html = "";
  for (const w of current.warnings || []) html += `<div class="warn">⚠️ ${esc(w)}</div>`;
  html += { ideas: renderIdeas, reddit: renderReddit, competitors: renderCompetitors }[activeTab]();
  app.innerHTML = html;
}

function renderIdeas() {
  const a = current.producthunt?.analysis || {};
  const ideas = a.top_ideas || [];
  if (!ideas.length) return `<p class="loading">아이디어 데이터 없음.</p>`;
  let h = "";
  if (a.common_themes?.length) {
    h += `<div class="card"><div class="label">공통 테마</div><ul>${a.common_themes
      .map((t) => `<li>${esc(t)}</li>`)
      .join("")}</ul></div>`;
  }
  h += ideas
    .map(
      (i) => `<div class="card">
      <h3><span class="rank">${esc(i.rank)}</span>${esc(i.title)}</h3>
      <p>${esc(i.problem)}</p>
      <div class="meta">
        <span class="tag diff-${esc(i.solo_dev_difficulty)}">난이도: ${esc(i.solo_dev_difficulty)}</span>
        <span class="tag">📊 ${esc(i.market_size_estimate)}</span>
      </div>
      <div class="label">왜 미개척인가</div><p>${esc(i.why_untapped)}</p>
    </div>`
    )
    .join("");
  return h;
}

function renderReddit() {
  const r = current.reddit;
  if (!r?.analysis) return `<p class="loading">Reddit 데이터 없음.</p>`;
  const a = r.analysis;
  let h = `<div class="card"><div class="label">분석 대상 아이디어</div><h3>${esc(r.target_idea)}</h3>`;
  if (a.opportunity_signal) h += `<p>💡 ${esc(a.opportunity_signal)}</p>`;
  h += `</div>`;
  if (a.communities?.length)
    h += `<div class="card"><div class="label">관련 커뮤니티</div><ul>${a.communities
      .map((c) => `<li><b>${esc(c.name)}</b> — ${esc(c.why_relevant || "")}</li>`)
      .join("")}</ul></div>`;
  if (a.unsolved_problems?.length)
    h += `<div class="card"><div class="label">미해결 문제</div><ul>${a.unsolved_problems
      .map((p) => `<li>${esc(p)}</li>`)
      .join("")}</ul></div>`;
  if (a.frequent_complaints?.length)
    h += `<div class="card"><div class="label">자주 나오는 불만</div><ul>${a.frequent_complaints
      .map((p) => `<li>${esc(p)}</li>`)
      .join("")}</ul></div>`;
  return h;
}

function renderCompetitors() {
  const c = current.competitors;
  if (!c?.analysis) return `<p class="loading">경쟁사 데이터 없음.</p>`;
  const a = c.analysis;
  let h = `<div class="card"><div class="label">분석 대상</div><h3>${esc(c.target_idea)}
    <span class="verify-badge">검증 필요</span></h3></div>`;
  if (a.competitors?.length)
    h += `<div class="card"><div class="label">경쟁사 & 요금제</div><ul>${a.competitors
      .map((x) => `<li><b>${esc(x.name)}</b> — ${esc(x.pricing)} <i>(${esc(x.positioning || "")})</i></li>`)
      .join("")}</ul></div>`;
  if (a.top_complaints?.length)
    h += `<div class="card"><div class="label">가장 큰 불만 3가지 = 빈 공간</div>${a.top_complaints
      .map(
        (x, i) =>
          `<p><span class="rank">${i + 1}</span> <b>${esc(x.complaint)}</b><br/>↳ 빈 공간: ${esc(x.gap)}</p>`
      )
      .join("")}</div>`;
  if (a.our_wedge)
    h += `<div class="card"><div class="label">우리가 파고들 차별화 기획</div><p>${esc(a.our_wedge)}</p></div>`;
  return h;
}

init();
