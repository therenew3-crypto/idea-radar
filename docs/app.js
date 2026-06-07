// 정적 대시보드 — docs/data/*.json 을 읽어 렌더한다. 빌드 도구 불필요.
const app = document.querySelector("#app");
let current = null;
let currentId = null;

// ⚡ 새 분석(과금 발생)은 비밀번호로 보호. 해시(SHA-256)만 저장해 평문 노출을 피한다.
const REANALYZE_HASH = "5728c992e0c03fa48754a8636ffb192f1e2aa23f20be242c290d5eefd9b80182";

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function guardReanalyze(e) {
  e.preventDefault();
  const pw = prompt("⚡ 새 분석은 비용이 발생합니다 (Claude 호출).\n실행하려면 비밀번호를 입력하세요:");
  if (pw === null) return; // 취소
  if ((await sha256(pw)) === REANALYZE_HASH) {
    window.open(e.currentTarget.href, "_blank", "noopener");
  } else {
    alert("비밀번호가 틀렸습니다.");
  }
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const list = (arr) => (Array.isArray(arr) && arr.length ? `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "<p class='muted'>—</p>");

// index.json 을 다시 읽어 스냅샷 목록을 갱신하고, 원하는 스냅샷(없으면 최신)을 로드한다.
async function loadIndex(preferId) {
  const index = await fetch("data/index.json", { cache: "no-store" }).then((r) => r.json());
  // 신규 스키마(entries) 우선, 구버전(dates) 호환
  const entries = index.entries || (index.dates || []).map((d) => ({ id: d, label: d }));
  const select = document.querySelector("#date-select");
  select.innerHTML = entries
    .map((e) => `<option value="${e.id}">${esc(e.label)}${e.idea_count ? ` · ${e.idea_count}개` : ""}</option>`)
    .join("");
  const ids = entries.map((e) => e.id);
  const target = preferId && ids.includes(preferId) ? preferId : index.latest || ids[0];
  if (target) {
    select.value = target;
    await loadDate(target);
  }
}

async function init() {
  try {
    await loadIndex();
  } catch {
    app.innerHTML = `<div class="warn">아직 생성된 데이터가 없습니다. ⚡새로 분석 버튼으로 워크플로우를 한 번 실행하세요.</div>`;
    return;
  }
  document.querySelector("#date-select").addEventListener("change", (e) => loadDate(e.target.value));
  document.querySelector("#refresh").addEventListener("click", refresh);
  document.querySelector("#reanalyze").addEventListener("click", guardReanalyze);
}

// 🔄 최신 데이터 다시 불러오기 (캐시 무시)
async function refresh() {
  const btn = document.querySelector("#refresh");
  const status = document.querySelector("#status");
  btn.classList.add("spinning");
  status.textContent = "새로고침 중…";
  try {
    await loadIndex(currentId);
    const when = current?.label || fmtKST(current?.generated_at) || "";
    status.textContent = `✓ 새로고침됨 · 🕑 ${when}`;
  } catch {
    status.textContent = "새로고침 실패 (네트워크 확인)";
  } finally {
    setTimeout(() => btn.classList.remove("spinning"), 700);
  }
}

// generated_at(UTC ISO) -> "YYYY-MM-DD HH:MM" (KST)
function fmtKST(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const k = new Date(d.getTime() + 9 * 3600 * 1000);
  const p = (n) => String(n).padStart(2, "0");
  return `${k.getUTCFullYear()}-${p(k.getUTCMonth() + 1)}-${p(k.getUTCDate())} ${p(k.getUTCHours())}:${p(k.getUTCMinutes())}`;
}

async function loadDate(id) {
  document.querySelector("#status").textContent = "불러오는 중…";
  current = await fetch(`data/${id}.json`, { cache: "no-store" }).then((r) => r.json());
  currentId = id;
  const when = current.label || fmtKST(current.generated_at) || id;
  document.querySelector("#status").textContent = `🕑 갱신: ${when}`;
  render();
}

function scoreClass(s) {
  return s >= 7 ? "good" : s >= 4 ? "mid" : "low";
}

function render() {
  if (!current) return;
  let html = "";
  for (const w of current.warnings || []) html += `<div class="warn">⚠️ ${esc(w)}</div>`;

  if (current.common_themes?.length) {
    html += `<div class="themes"><div class="label">오늘의 공통 테마</div>${list(current.common_themes)}</div>`;
  }

  const ideas = current.ideas || [];
  if (!ideas.length) {
    html += `<p class="loading">아이디어가 없습니다. 잠시 후 다시 시도하세요.</p>`;
    app.innerHTML = html;
    return;
  }
  html += ideas.map((idea, i) => renderIdea(idea, i)).join("");
  app.innerHTML = html;

  // 아코디언 토글 (첫 번째는 펼침)
  document.querySelectorAll(".idea-head").forEach((head, i) => {
    if (i === 0) head.parentElement.classList.add("open");
    head.addEventListener("click", () => head.parentElement.classList.toggle("open"));
  });
}

function renderIdea(idea, i) {
  const v = idea.verdict || {};
  const score = Number.isFinite(v.score) ? v.score : "?";
  const m = idea.market || {};
  const p = idea.pricing_analysis || {};
  const sf = idea.solo_founder || {};
  const comps = idea.competitors || [];

  const compRows = comps
    .map(
      (c) => `<tr><td><b>${esc(c.name)}</b></td><td>${esc(c.pricing)}</td>
        <td>${esc(c.strengths)}</td><td>${esc(c.weaknesses)}</td></tr>`
    )
    .join("");

  return `<div class="idea">
    <div class="idea-head">
      <span class="rank">${esc(idea.rank ?? i + 1)}</span>
      <div class="titles">
        <h3>${esc(idea.title)}</h3>
        <div class="sub">${esc(idea.one_liner || idea.problem || "")}</div>
      </div>
      <div class="score ${scoreClass(score)}">${esc(score)}<small>/10</small></div>
      <span class="chev">▶</span>
    </div>
    <div class="idea-body">

      <div class="sec">
        <div class="label">📊 시장 규모 <span class="verify">추정·검증필요</span></div>
        <dl class="kv">
          <dt>TAM</dt><dd>${esc(m.tam)}</dd>
          <dt>SAM</dt><dd>${esc(m.sam)}</dd>
          <dt>SOM</dt><dd>${esc(m.som)}</dd>
          <dt>성장세</dt><dd>${esc(m.growth_trend)}</dd>
        </dl>
        <p class="muted">${esc(m.reasoning)}</p>
      </div>

      <div class="sec">
        <div class="label">🎯 경쟁사 분석 <span class="verify">추정</span></div>
        <table><thead><tr><th>경쟁사</th><th>요금제</th><th>강점</th><th>약점=기회</th></tr></thead>
          <tbody>${compRows || `<tr><td colspan="4">—</td></tr>`}</tbody></table>
      </div>

      <div class="sec">
        <div class="label">💰 요금제 분석</div>
        <dl class="kv">
          <dt>가격대</dt><dd>${esc(p.price_range)}</dd>
          <dt>과금방식</dt><dd>${esc((p.common_models || []).join(", "))}</dd>
          <dt>빈틈</dt><dd>${esc(p.gap)}</dd>
          <dt>추천가</dt><dd><b>${esc(p.our_suggested_pricing)}</b></dd>
        </dl>
      </div>

      <div class="sec">
        <div class="label">👤 1인 창업 가능성</div>
        <dl class="kv">
          <dt>구축난이도</dt><dd>${esc(sf.build_difficulty)}</dd>
          <dt>MVP기간</dt><dd>${esc(sf.time_to_mvp)}</dd>
          <dt>필요역량</dt><dd>${esc((sf.required_skills || []).join(", "))}</dd>
          <dt>수익화</dt><dd>${esc(sf.monetization)}</dd>
          <dt>해자</dt><dd>${esc(sf.moat)}</dd>
        </dl>
        <div class="cols">
          <div class="box pros"><h4>✅ 장점</h4>${list(sf.pros)}</div>
          <div class="box cons"><h4>⚠️ 단점</h4>${list(sf.cons)}</div>
        </div>
        <p class="risk">🔴 최대 리스크: ${esc(sf.biggest_risk)}</p>
      </div>

      <div class="sec">
        <div class="label">⚖️ 최종 사업 판단</div>
        <div class="verdict">
          <span class="reco">판정: ${esc(v.recommendation)} (${esc(score)}/10)</span>
          <p>${esc(v.summary)}</p>
          <div class="first">👉 첫걸음: ${esc(v.first_step)}</div>
        </div>
      </div>

    </div>
  </div>`;
}

init();
