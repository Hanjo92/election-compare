const DISTRICT_INDEX_PATH = "./data/district-index.json";

const $ = (selector) => document.querySelector(selector);

const normalize = (value) => String(value || "").toLowerCase().trim();
const ALL_ELECTIONS = "__all__";

const renderDistricts = (districts) => {
  const container = $("#district-list");

  if (!districts.length) {
    container.innerHTML = `<p class="empty-state">일치하는 지역구가 없습니다.</p>`;
    return;
  }

  container.innerHTML = districts
    .map(
      (district) => `
        <a class="district-list-item" href="${district.path}">
          <div>
            <strong>${district.name}</strong>
            <p>${district.electionName}</p>
          </div>
          <span class="tag">${district.candidateCount}명</span>
        </a>
      `,
    )
    .join("");
};

const updateElectionSummary = (elections, selectedElectionKey, filteredDistricts) => {
  const summary = $("#election-summary");
  if (!summary) {
    return;
  }

  const selectedElection =
    selectedElectionKey === ALL_ELECTIONS
      ? null
      : elections.find((election) => election.key === selectedElectionKey);

  if (!filteredDistricts.length) {
    summary.textContent = "현재 조건에 맞는 지역구가 없습니다.";
    return;
  }

  if (!selectedElection) {
    summary.textContent = `전체 ${filteredDistricts.length}개 지역구`;
    return;
  }

  summary.textContent = `${selectedElection.name} · ${filteredDistricts.length}개 지역구`;
};

const setupFilters = (payload) => {
  const districts = payload.districts || [];
  const elections = payload.elections || [];
  const input = $("#district-search");
  const select = $("#election-select");

  if (select) {
    const options = [
      `<option value="${ALL_ELECTIONS}">전체 선거</option>`,
      ...elections.map(
        (election) =>
          `<option value="${election.key}">${election.name} (${election.districtCount}개 지역구)</option>`,
      ),
    ];
    select.innerHTML = options.join("");
  }

  const applyFilters = () => {
    const keyword = normalize(input.value);
    const selectedElectionKey = select?.value || ALL_ELECTIONS;
    const filtered = districts.filter((district) => {
      if (selectedElectionKey !== ALL_ELECTIONS && district.electionKey !== selectedElectionKey) {
        return false;
      }
      const haystack = [district.name, district.region, district.code, district.electionName]
        .map(normalize)
        .join(" ");
      return !keyword || haystack.includes(keyword);
    });
    renderDistricts(filtered);
    updateElectionSummary(elections, selectedElectionKey, filtered);
  };

  renderDistricts(districts);
  updateElectionSummary(elections, ALL_ELECTIONS, districts);
  input.addEventListener("input", applyFilters);
  select?.addEventListener("change", applyFilters);
};

const renderError = () => {
  const container = $("#district-list");
  container.innerHTML = `<p class="empty-state">지역구 목록을 불러오지 못했습니다.</p>`;
};

fetch(DISTRICT_INDEX_PATH)
  .then((response) => {
    if (!response.ok) {
      throw new Error("Failed to load district index");
    }
    return response.json();
  })
  .then((payload) => setupFilters(payload))
  .catch(renderError);
