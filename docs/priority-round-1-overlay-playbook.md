# Priority Round 1 Overlay Playbook

`configs/election-batch.priority.local.json` 기준 25개 지역구를 수동 보강할 때 쓰는 운영 메모다.

## 목표

- 전국 분산형 표본 25개를 빠르게 usable 상태로 만든다.
- 수동 보강은 꼭 필요한 5개 필드만 채운다.
- 후보자별 완벽 수집보다 지역구별 비교 가능 상태를 먼저 만든다.

## 대상 파일

- 배치 설정: `configs/election-batch.priority.local.json`
- base JSON: `data/base/district-<code>.json`
- overlay JSON: `data/overlays/district-<code>.json`
- merged JSON: `data/district-<code>.json`

## 운영 원칙

1. 먼저 25개 전체의 base JSON을 수집한다.
2. 그 다음 25개 전체의 overlay 템플릿을 생성한다.
3. 각 지역구에서 모든 후보의 `assets`, `tax`, `crime`부터 먼저 채운다.
4. 시간이 남으면 `military`, `incumbentLabel`을 채운다.
5. 한 지역구에서 5개 필드를 다 끝내는 방식보다, 25개 전체에 최소 비교 필드를 먼저 깐다.

## 필드 우선순위

### P0

- `assets`
  후보 간 차이를 한눈에 보여주기 좋고 누락 체감이 크다.
- `tax`
  유권자 관점에서 민감도가 높고 비교 가치가 높다.
- `crime`
  비교 페이지에서 가장 눈에 띄는 검증 포인트 중 하나다.

### P1

- `military`
  후보별 의미는 크지만 일부 후보에서는 해당없음/면제/복무형태 정리가 필요하다.
- `incumbentLabel`
  단순하지만 표시 품질에 도움이 된다. 다른 필드보다 뒤로 둬도 된다.

## 출처 우선순위

### 1순위

- 후보자공보 또는 선관위 후보 정보 페이지
- 기본 표기 라벨:
  `label: "후보자공보"`
  `url: "https://info.nec.go.kr/"`

### 2순위

- 선관위 선거통계/후보 상세 페이지에서 같은 값이 명확히 보일 때

### 3순위

- 국회/정당/언론 자료
- 이 경우 `fieldNotes`에 왜 이 출처를 썼는지 짧게 남긴다.

## 표기 규칙

- `assets`: 공보 기준 금액 표기를 최대한 유지한다.
- `tax`: `체납사실 없음`, `체납액 있음`, `최근 5년 체납액 ...`처럼 사실형 문장으로 쓴다.
- `crime`: `전과 0건`, `전과 1건`처럼 건수 중심으로 통일한다.
- `military`: `군필`, `미필`, `면제`, `해당없음`처럼 짧게 쓰고 필요하면 notes에 보충한다.
- `incumbentLabel`: `현직`, `전직`, `원외`처럼 짧은 배지형 문자열로 맞춘다.

## 작업 순서

### 1. base JSON 수집

```bash
cd /home/seunghus/.openclaw/workspace/election-compare
python3 scripts/fetch_nec_batch.py --config configs/election-batch.priority.local.json --generate-overlays --build-site
```

### 2. overlay 템플릿 재생성

기존 템플릿을 덮어쓸 때만 `--force`를 붙인다.

```bash
cd /home/seunghus/.openclaw/workspace/election-compare
python3 scripts/generate_overlay_templates.py --fields assets,military,tax,crime,incumbentLabel
```

### 3. P0 필드 먼저 채우기

각 지역구 overlay 파일에서 모든 후보의 아래 3개를 우선 입력한다.

- `assets`
- `tax`
- `crime`

### 4. P1 필드 채우기

P0가 25개 전체에서 끝난 뒤 아래를 채운다.

- `military`
- `incumbentLabel`

### 5. 병합 결과 재생성

```bash
cd /home/seunghus/.openclaw/workspace/election-compare
python3 scripts/build_site.py
```

## 지역구 묶음

### Core metro

- 서울특별시: `jongno-gu`, `mapo-gu-gap`, `yeongdeungpo-gu-eul`, `gwanak-gu-gap`, `seocho-gu-gap`
- 경기도: `seongnam-bundang-gap`, `hwaseong-eul`, `gimpo-gap`
- 부산광역시: `haeundae-gu-gap`, `suyeong-gu`

### Broad national coverage

- 대구광역시: `suseong-gu-gap`
- 인천광역시: `yeonsu-gu-eul`
- 광주광역시: `gwangsan-gu-gap`
- 대전광역시: `yuseong-gu-eul`
- 울산광역시: `nam-gu-gap-ulsan`
- 세종특별자치시: `sejong-gap`
- 강원특별자치도: `wonju-gap`
- 충청북도: `cheongju-sangdang`
- 충청남도: `cheonan-gap`
- 전북특별자치도: `jeonju-byeong`, `gunsan-gimje-buan-eul`
- 전라남도: `mokpo`
- 경상북도: `andong-yecheon`
- 경상남도: `changwon-seongsan`
- 제주특별자치도: `jeju-gap`

## 완료 기준

- 최소 완료:
  25개 전체에서 `assets`, `tax`, `crime`가 모두 채워짐
- 권장 완료:
  25개 전체에서 `assets`, `tax`, `crime`, `military`, `incumbentLabel`가 모두 채워짐
- 품질 확인:
  `fieldSources`와 `fieldNotes`가 patch와 함께 들어가 있는지 확인

## 메모

- `patch` 값이 `null`이면 병합 시 무시된다.
- 값이 애매하면 빈칸으로 두고, 추측으로 채우지 않는다.
- 지역구 하나를 과하게 완성하기보다 25개 전체의 기본 비교 가능 상태를 먼저 만든다.
