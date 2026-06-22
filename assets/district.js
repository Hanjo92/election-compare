const districtCode = window.location.pathname.split("/").filter(Boolean).at(-1) || "seocho-gu-gap";
const DISTRICT_DATA_PATH = `../../data/district-${districtCode}.json`;

const COMPARISON_ROWS = [
  ["학력", "education", (candidate) => candidate.education],
  ["주요 경력", "career", (candidate) => candidate.career.join(", ")],
  ["재산", "assets", (candidate) => candidate.assets],
  ["병역", "military", (candidate) => candidate.military],
  ["납세", "tax", (candidate) => candidate.tax],
  ["전과", "crime", (candidate) => candidate.crime],
  [
    "핵심 공약",
    "pledges",
    (candidate) =>
      candidate.pledges.map((pledge) => `${pledge.title}: ${pledge.summary}`).join("\n\n"),
  ],
];

const $ = (selector) => document.querySelector(selector);
const formatAge = (age) => (/^\d+$/.test(String(age)) ? `${age}세` : String(age));
const escapeHtml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const renderFieldSource = (candidate, fieldKey) => {
  const source = candidate.fieldSources?.[fieldKey];
  const note = candidate.fieldNotes?.[fieldKey];
  const sourceHtml =
    source?.url && source?.label
      ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.label)}</a>`
      : "";
  const noteHtml = note ? `<div class="field-note">${escapeHtml(note)}</div>` : "";

  if (!sourceHtml && !noteHtml) {
    return "";
  }

  return `<div class="field-source">${sourceHtml}${noteHtml}</div>`;
};

const renderCandidateCards = (candidates) => {
  const grid = $("#candidate-grid");
  grid.innerHTML = candidates
    .map(
      (candidate) => `
        <article class="candidate-card">
          <div class="candidate-topline">
            <div>
              <h2 class="candidate-name">${candidate.name}</h2>
              <p class="candidate-party">${candidate.party}</p>
            </div>
            <span class="tag">${candidate.number}번</span>
          </div>
          <div class="candidate-meta">
            <div class="candidate-meta-item">
              <span class="meta-key">직업</span>
              <strong>${candidate.job}</strong>
            </div>
            <div class="candidate-meta-item">
              <span class="meta-key">나이</span>
              <strong>${formatAge(candidate.age)}</strong>
            </div>
            <div class="candidate-meta-item">
              <span class="meta-key">현직 여부</span>
              <strong>${candidate.incumbentLabel ?? (candidate.incumbent ? "현직" : "비현직")}</strong>
            </div>
          </div>
          <div>
            <p class="section-kicker">Key pledges</p>
            <ul class="pledge-list">
              ${(candidate.pledges?.length ? candidate.pledges : [{ title: "공약", summary: "자료 미확인" }])
                .map((pledge) => `<li><strong>${pledge.title}</strong> ${pledge.summary}</li>`)
                .join("")}
            </ul>
          </div>
        </article>
      `,
    )
    .join("");
};

const renderComparisonTable = (candidates) => {
  const table = $("#comparison-table");
  const headerCells = candidates.map((candidate) => `<th>${candidate.name}</th>`).join("");

  const bodyRows = COMPARISON_ROWS.map(
    ([label, fieldKey, getValue]) => `
      <tr>
        <th scope="row" class="row-label">${label}</th>
        ${candidates
          .map((candidate) => {
            const value = escapeHtml(String(getValue(candidate) ?? "자료 미확인")).replaceAll("\n", "<br />");
            return `<td>${value}${renderFieldSource(candidate, fieldKey)}</td>`;
          })
          .join("")}
      </tr>
    `,
  ).join("");

  table.innerHTML = `
    <thead>
      <tr>
        <th>항목</th>
        ${headerCells}
      </tr>
    </thead>
    <tbody>${bodyRows}</tbody>
  `;
};

const renderSources = (candidates) => {
  const container = $("#source-grid");

  container.innerHTML = candidates
    .map(
      (candidate) => `
        <article class="source-card">
          <p class="section-kicker">${candidate.name}</p>
          <h3>${candidate.party}</h3>
          <div class="source-list">
            <a class="source-link" href="${candidate.sources.profile}" target="_blank" rel="noreferrer">후보 정보</a>
            <a class="source-link" href="${candidate.sources.policy}" target="_blank" rel="noreferrer">공약 보기</a>
            <a class="source-link" href="${candidate.sources.data}" target="_blank" rel="noreferrer">데이터 출처</a>
          </div>
        </article>
      `,
    )
    .join("");
};

const renderPage = (payload) => {
  $("#district-region").textContent = payload.district.region;
  $("#district-name").textContent = payload.district.name;
  $("#election-name").textContent = payload.election.name;
  $("#updated-at").textContent = payload.meta?.updatedAt || payload.election.updatedAt;
  $("#candidate-count").textContent = `${payload.candidates.length}명`;

  renderCandidateCards(payload.candidates);
  renderComparisonTable(payload.candidates);
  renderSources(payload.candidates);
};

const renderError = () => {
  $("#election-name").textContent = "데이터를 불러오지 못했습니다.";
};

fetch(DISTRICT_DATA_PATH)
  .then((response) => {
    if (!response.ok) {
      throw new Error("Failed to load district data");
    }

    return response.json();
  })
  .then(renderPage)
  .catch(renderError);
