const DEFAULT_ELECTION_ID = "20240410";
const DEFAULT_DISTRICT_CODE = "seocho-gu-gap";
const REPO_DATA_REQUEST_BASE =
  "https://github.com/Hanjo92/election-compare/issues/new?template=data-request.md";

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

const getBasePath = () => {
  const marker = "/district/";
  const { pathname } = window.location;
  const markerIndex = pathname.indexOf(marker);
  if (markerIndex === -1) {
    return ".";
  }

  const prefix = pathname.slice(0, markerIndex);
  return `${prefix || ""}`;
};

const buildDataPath = (electionId, districtCode) =>
  `${getBasePath()}/data/elections/${electionId}/district-${districtCode}.json`;
const buildDistrictIndexPath = () => `${getBasePath()}/data/district-index.json`;

const escapeHtml = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const buildRequestIssueUrl = (meta, routeParams) => {
  const issueTitle = `[data-request] ${meta.electionName || routeParams.electionId} / ${meta.name || routeParams.districtCode}`;
  const issueBody = [
    "## Request Metadata",
    `- electionId: ${routeParams.electionId}`,
    `- electionTypecode: ${meta.electionTypecode || ""}`,
    `- electionName: ${meta.electionName || ""}`,
    `- region: ${meta.region || ""}`,
    `- districtName: ${meta.name || routeParams.districtCode}`,
    `- districtCode: ${routeParams.districtCode}`,
    "",
    "## Notes",
    "- requested from district viewer",
  ].join("\n");
  return `${REPO_DATA_REQUEST_BASE}&title=${encodeURIComponent(issueTitle)}&body=${encodeURIComponent(issueBody)}`;
};

const detectRouteParams = () => {
  const params = new URLSearchParams(window.location.search);
  const queryElectionId = params.get("electionId");
  const queryDistrictCode = params.get("code");
  if (queryElectionId && queryDistrictCode) {
    return {
      electionId: queryElectionId,
      districtCode: queryDistrictCode,
      canonical: `${getBasePath()}/district/?electionId=${encodeURIComponent(queryElectionId)}&code=${encodeURIComponent(queryDistrictCode)}`,
    };
  }

  const pathSegments = window.location.pathname.split("/").filter(Boolean);
  const districtIndex = pathSegments.lastIndexOf("district");
  return {
    electionId: pathSegments[districtIndex + 1] || DEFAULT_ELECTION_ID,
    districtCode: pathSegments[districtIndex + 2] || DEFAULT_DISTRICT_CODE,
    canonical: null,
  };
};

const formatAge = (age) => (/^\d+$/.test(String(age)) ? `${age}세` : String(age));
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

const fetchDistrictMeta = async (routeParams) => {
  const response = await fetch(buildDistrictIndexPath());
  if (!response.ok) {
    throw new Error("Failed to load district index");
  }

  const payload = await response.json();
  const match = (payload.districts || []).find(
    (district) =>
      String(district.electionId) === String(routeParams.electionId) &&
      String(district.code) === String(routeParams.districtCode),
  );

  return (
    match || {
      code: routeParams.districtCode,
      name: routeParams.districtCode,
      region: "미확인",
      electionId: routeParams.electionId,
      electionTypecode: "",
      electionName: routeParams.electionId,
    }
  );
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

const renderPage = (payload, routeParams) => {
  const districtPath = `${getBasePath()}/district/?electionId=${encodeURIComponent(routeParams.electionId)}&code=${encodeURIComponent(routeParams.districtCode)}`;
  document.title = `Ballot Mirror | ${payload.district.name} | ${payload.election.name}`;
  $("#district-region").textContent = payload.district.region;
  $("#district-name").textContent = payload.district.name;
  $("#election-name").textContent = payload.election.name;
  $("#updated-at").textContent = payload.meta?.updatedAt || payload.election.updatedAt;
  $("#candidate-count").textContent = `${payload.candidates.length}명`;
  $("#canonical-link")?.setAttribute("href", districtPath);

  renderCandidateCards(payload.candidates);
  renderComparisonTable(payload.candidates);
  renderSources(payload.candidates);
};

const renderError = async (routeParams) => {
  const meta = await fetchDistrictMeta(routeParams).catch(() => ({
    code: routeParams.districtCode,
    name: routeParams.districtCode,
    region: "미확인",
    electionTypecode: "",
    electionName: routeParams.electionId,
  }));
  const requestUrl = buildRequestIssueUrl(meta, routeParams);
  $("#district-region").textContent = meta.region || "미확인";
  $("#district-name").textContent = meta.name || routeParams.districtCode;
  $("#election-name").textContent = "아직 이 지역구 데이터가 준비되지 않았습니다.";
  $("#candidate-grid").innerHTML = `
    <article class="candidate-card">
      <p>필요한 JSON이 아직 없어서 비교표를 바로 보여주지 못하고 있어.</p>
      <p>요청을 남기면 GitHub Actions가 이 지역구 데이터를 수집해서 사이트 반영을 시도해.</p>
      <p><a class="button button-primary" href="${requestUrl}" target="_blank" rel="noreferrer">이 지역구 데이터 요청하기</a></p>
    </article>
  `;
};

const routeParams = detectRouteParams();
const districtDataPath = buildDataPath(routeParams.electionId, routeParams.districtCode);

fetch(districtDataPath)
  .then((response) => {
    if (!response.ok) {
      throw new Error("Failed to load district data");
    }

    return response.json();
  })
  .then((payload) => renderPage(payload, routeParams))
  .catch(() => renderError(routeParams));
