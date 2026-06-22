const DISTRICT_INDEX_PATH = "./data/district-index.json";

const $ = (selector) => document.querySelector(selector);

const normalize = (value) => String(value || "").toLowerCase().trim();

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

const setupSearch = (districts) => {
  const input = $("#district-search");
  renderDistricts(districts);

  input.addEventListener("input", () => {
    const keyword = normalize(input.value);
    if (!keyword) {
      renderDistricts(districts);
      return;
    }

    const filtered = districts.filter((district) => {
      const haystack = [district.name, district.region, district.code, district.electionName]
        .map(normalize)
        .join(" ");
      return haystack.includes(keyword);
    });

    renderDistricts(filtered);
  });
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
  .then((payload) => setupSearch(payload.districts || []))
  .catch(renderError);
