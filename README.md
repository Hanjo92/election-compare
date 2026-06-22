# Ballot Mirror Prototype

정적 페이지 기반 지역구 후보 비교 프로토타입입니다.

## 포함 내용

- `index.html`: 서비스 소개와 샘플 지역구 진입점
- `district/seocho-gu-gap/index.html`: 샘플 지역구 비교 페이지
- `data/district-seocho-gu-gap.json`: 샘플 후보 데이터
- `data/base/`: API 수집 원본 또는 기본 데이터
- `data/overlays/`: 수동 보강 오버레이
- `data/district-index.json`: 홈에서 읽는 지역구 인덱스
- `assets/district.js`: 지역구 데이터를 렌더링하는 스크립트
- `assets/home.js`: 홈 검색과 지역구 목록 렌더링
- `assets/styles.css`: 공통 스타일
- `scripts/generate_overlay_templates.py`: 여러 지역구용 오버레이 템플릿 생성
- `scripts/sync_district_pages.py`: 지역구 라우트 HTML 자동 생성
- `scripts/build_site.py`: 병합 + 라우트 생성 + 홈 인덱스 갱신 일괄 실행
- `scripts/fetch_nec_batch.py`: 여러 지역구 실데이터 일괄 수집
- `configs/election-batch.sample.json`: 배치 수집 설정 샘플
- `configs/election-batch.flat.sample.json`: 단일 시도용 평면 배치 샘플
- `configs/election-batch.priority.local.json`: 전국 분산형 1차 우선수집 운영셋
- `docs/priority-round-1-overlay-playbook.md`: 25개 운영셋용 수동 보강 우선순위 기준서

## 실행

브라우저에서 `fetch()`로 JSON을 읽기 때문에 로컬 서버로 띄우는 편이 안전합니다.

```bash
cd /home/seunghus/.openclaw/workspace/election-compare
python3 -m http.server 4173
```

그 다음 `http://localhost:4173` 에서 확인하면 됩니다.

## 실데이터 수집

선관위 데이터는 공공데이터포털 API 키가 필요합니다.

1. `data.go.kr`에서 중앙선거관리위원회 API 활용신청
2. 서비스 키를 발급받아 환경변수로 넣기

```bash
export NEC_API_KEY='발급받은키'
```

3. 수집 스크립트 실행

```bash
cd /home/seunghus/.openclaw/workspace/election-compare
python3 scripts/fetch_nec_candidates.py \
  --sg-id 20240410 \
  --sg-typecode 2 \
  --sd-name '서울특별시' \
  --sgg-name '서초구갑' \
  --district-code seocho-gu-gap \
  --election-name '제22대 국회의원선거'
```

성공하면 `data/base/district-seocho-gu-gap.json` 이 갱신됩니다.

여러 지역구를 한 번에 수집하려면 배치 설정 파일을 준비한 뒤 아래처럼 실행하면 됩니다.

```bash
cp configs/election-batch.sample.json configs/election-batch.local.json
python3 scripts/fetch_nec_batch.py --config configs/election-batch.local.json --dry-run
python3 scripts/fetch_nec_batch.py --config configs/election-batch.local.json --generate-overlays --build-site
```

배치 설정 파일은 두 가지 형식을 지원합니다.

1. `regions` 형식
서울/부산/전북처럼 여러 시도를 한 파일에서 섞어 다룰 때 권장

```json
{
  "sgId": "20240410",
  "sgTypecode": "2",
  "electionName": "제22대 국회의원선거",
  "regions": [
    {
      "sdName": "서울특별시",
      "districts": [
        { "districtCode": "seocho-gu-gap", "sggName": "서초구갑" },
        { "districtCode": "jongno-gu", "sggName": "종로구" }
      ]
    },
    {
      "sdName": "부산광역시",
      "districts": [
        { "districtCode": "haeundae-gu-gap", "sggName": "해운대구갑" }
      ]
    }
  ]
}
```

2. `districts` 평면 형식
한 시도 안에서만 돌릴 때 단순하게 쓰기 좋음

```json
{
  "sgId": "20240410",
  "sgTypecode": "2",
  "sdName": "서울특별시",
  "electionName": "제22대 국회의원선거",
  "districts": [
    { "districtCode": "seocho-gu-gap", "sggName": "서초구갑" },
    { "districtCode": "jongno-gu", "sggName": "종로구" }
  ]
}
```

각 지역구 객체는 필요하면 `sdName`, `electionName`, `output`으로 개별 override도 할 수 있습니다.
또 `enabled: false`를 넣으면 일시적으로 제외할 수 있습니다.
`regions` 형식에서는 지역 단위에도 `enabled: false`를 넣을 수 있습니다.

그 다음 수동 보강 오버레이를 합쳐서 실제 사이트용 JSON을 생성합니다.

```bash
python3 scripts/apply_manual_overlays.py --district-code seocho-gu-gap
```

여러 지역구용 수동 입력 틀을 먼저 뽑고 싶으면 템플릿 생성 스크립트를 사용할 수 있습니다.

```bash
python3 scripts/generate_overlay_templates.py
```

지역구 HTML 라우트도 자동 생성할 수 있습니다.

```bash
python3 scripts/sync_district_pages.py
```

수집 후 홈 목록도 다시 생성하면 좋습니다.

```bash
python3 scripts/build_district_index.py
```

반복 작업은 한 번에 이렇게 돌리면 됩니다.

```bash
python3 scripts/build_site.py
```

GitHub Pages 배포용 dist를 로컬에서 미리 확인하려면:

```bash
python3 scripts/prepare_pages_dist.py
cd dist
python3 -m http.server 4173
```

## 현재 수집 범위

- 후보 기본정보: 선관위 후보자 정보 API
- 공약: 선관위 선거공약 API

아직 자동 수집 안 되는 항목:

- 재산
- 전과
- 병역
- 납세
- 현직 여부

이 값들은 기본적으로 `자료 미확인`으로 채워집니다. 수동 보강은 `data/overlays/`에서 별도 관리합니다.

## 수동 보강 구조

- `data/base/district-<code>.json`
  API 수집 결과나 기본 원본 데이터
- `data/overlays/district-<code>.json`
  후보별 수동 패치와 필드별 출처
- `data/district-<code>.json`
  사이트가 실제로 읽는 병합 결과

권장 수동 보강 필드셋:

- `assets`: 재산신고액
- `military`: 병역사항
- `tax`: 납세/체납
- `crime`: 전과기록
- `incumbentLabel`: 현직 여부 표기

25개 우선수집 운영셋을 기준으로 실제 입력 순서와 출처 우선순위를 굳혀둔 문서는 아래를 보면 됩니다.

- `docs/priority-round-1-overlay-playbook.md`

오버레이 파일 형식은 아래처럼 맞추면 됩니다.

```json
{
  "meta": {
    "updatedAt": "2026-06-18 12:45 KST",
    "note": "후보자공보 기준 수동 보강"
  },
  "candidates": [
    {
      "match": { "id": "cand-1", "number": 1 },
      "patch": { "assets": "12억 3,000만원" },
      "fieldSources": {
        "assets": {
          "label": "후보자공보",
          "url": "https://info.nec.go.kr/"
        }
      },
      "fieldNotes": {
        "assets": "재산신고액 기준"
      }
    }
  ]
}
```

`match`는 `id`, `name`, `number` 같은 기존 후보 필드로 잡을 수 있고, `patch`는 덮어쓸 값만 넣으면 됩니다. `fieldSources`, `fieldNotes`는 `patch`에 실제 값이 들어간 항목에만 병합됩니다.

템플릿 자동 생성 예시:

```bash
python3 scripts/generate_overlay_templates.py --district-code seocho-gu-gap
python3 scripts/generate_overlay_templates.py --fields assets,military,tax,crime,incumbentLabel
python3 scripts/generate_overlay_templates.py --config configs/election-batch.priority.local.json --allow-missing-base
```

기존 오버레이를 다시 만들고 싶으면 `--force`를 붙이면 됩니다.

`--config`를 쓰면 배치 설정에 들어 있는 지역구 기준으로 한 번에 템플릿을 만든다. 이때 `--allow-missing-base`를 같이 쓰면 base JSON이 아직 없는 지역구도 빈 스텁 overlay 파일을 먼저 만들어둘 수 있고, 나중에 실데이터 수집 후 `--force`로 후보 match가 들어간 템플릿으로 다시 생성하면 된다.

## 다음 단계

1. 여러 지역구 base JSON 생성
2. `generate_overlay_templates.py`로 오버레이 템플릿 생성
3. 필요한 필드만 채운 뒤 `build_site.py` 실행
4. 필요하면 정적 배포 또는 Astro 마이그레이션

## GitHub Pages 배포

이 레포에는 `.github/workflows/deploy-pages.yml` 이 포함되어 있다.

1. GitHub에 이 폴더를 새 repo로 push
2. GitHub repo 설정에서 `Pages`를 `GitHub Actions` 소스로 사용
3. `main` 브랜치에 push
4. Actions가 `build_site.py` 실행 후 `dist/`를 만들어 Pages로 배포

로컬에서 배포 산출물만 미리 만들고 싶으면 아래를 실행하면 된다.

```bash
cd /home/seunghus/.openclaw/workspace/election-compare
python3 scripts/build_site.py
python3 scripts/prepare_pages_dist.py
```

배포 산출물에는 아래만 들어간다.

- `index.html`
- `about.html`
- `assets/`
- `district/`
- `data/`
