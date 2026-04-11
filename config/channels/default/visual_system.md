# Eisenherz 채널 비주얼 시스템

> Claude Projects 지식베이스용 문서. 이 문서를 프로젝트에 업로드하면 Claude가 Eisenherz 채널의 톤, 캐릭터, 프롬프트 공식을 자동으로 알고 응답합니다.

---

## 1. 채널 기본 정보

- **채널명**: Eisenherz (@Eisenherzyy)
- **뜻**: 독일어로 "철의 심장"
- **장르**: Underground Schranz & Hard Techno
- **씬**: European underground techno scene
- **호스트(형님) 호칭**: "형님"으로 부를 것 (이름 X)
- **사용 언어**: 한국어 응답, 프롬프트는 영어

---

## 2. 비주얼 정체성 (Visual Identity)

### 기본 방향
- 고정된 시각 시스템은 없음 — 참조 사진을 매번 넣어서 그 톤/무드에 맞게 유연하게 작업
- 아래 컬러 팔레트와 금지 항목은 **감각의 기준선**으로 참고, 절대 규칙 아님

### 컬러 팔레트 (참고용)
- **베이스**: 차콜 블랙 (#0a0a0a), 콘크리트 그레이 (#2a2a2a)
- **포인트**: 인더스트리얼 레드 (#c41e1e), 콜드 스틸 블루 (#3a5a7a)
- **하이라이트**: 더티 화이트 (#e8e4dc), 러스트 오렌지 (#a04020)

### 피하는 것 (유연하게 — 참조 사진 우선)
- 보라/시안 네온 (레트로웨이브 톤)
- 80년대 마이애미 바이브
- 손글씨/필기체 폰트
- 파스텔/밝은 컬러
- 아니메/카툰 스타일
- 밝고 쾌활한 무드

### 폰트 (타이포그래피)
- **Bebas Neue** — 메인 추천, 인더스트리얼 산세리프
- **Anton** — 강한 임팩트
- **Archivo Black** — 브루탈리스트
- **Druk Wide / Druk Condensed** — 프로 브루탈리즘
- **Oswald** — 부드러운 대안
- 공통 원칙: 굵고, 대문자, 자간 넓게

### 레퍼런스 감독/작품
- **Denis Villeneuve** (Dune, Blade Runner 2049, Arrival)
- **Children of Men** (Emmanuel Lubezki)
- **Stalker** (Tarkovsky)
- **Annihilation**
- **Prometheus**
- **The Road**
- **Interstellar**
- **AXEND 채널** (FORSAKEN 시리즈 — 다크 테크노 비주얼 레퍼런스)

---

## 3. 캐릭터/이미지 시리즈 (고정 아님, 확장 가능)

> 아래는 지금까지 만든 것들의 기록. "시그니처 시리즈"로 고정된 건 아님. 참조 사진 보면서 유연하게 새 방향도 열어둠.

### 사신 (The Reaper)
- **컨셉**: 검은 후드 로브의 키 크고 마른 형상
- **핵심 디테일**:
  - Heavy black wool hooded robe, visible fabric weave, frayed edges
  - 얼굴은 후드 안 절대 그림자 속
  - 빨간 눈 두 점만 (faint pinpoint red glows)
  - Pale bony fingers with subtle veins
- **완성작 및 아이디어**:
  - ✅ 오렌지 태비 고양이와 함께
  - 검은 까마귀 (falconer 스타일)
  - 흰 늑대, 흰 부엉이, 검은 말, 흰 토끼

### 우주비행사 (Traces on the Planet)
- **컨셉**: 빈티지 NASA 스타일 우주복, 외계 행성 탐사/사망
- **핵심 디테일**:
  - Vintage NASA-style weathered white spacesuit
  - Yellowed mission patches, scuffs, dust, torn fabric
  - Apollo 패치, NASA 로고, 성조기
  - 깨진 헬멧 유리 (spiderweb crack pattern)
- **완성작 및 아이디어**:
  - ✅ 죽은 우주비행사 + 꽃 피어나는 헬멧 (클로즈업)
  - ✅ 죽은 우주비행사 와이드 (두 개의 태양)
  - 살아있는 발견자 우주비행사, 외계 도시 폐허 탐사

### 마지막 인간 (The Last Ones)
- **컨셉**: 폐허 속 희망 - 가스마스크 정원사
- **핵심 디테일**:
  - Weathered military gas mask, scratched glass lenses
  - Tattered olive trench coat, ash-covered
  - Small terracotta clay pot with single green sprout
- **완성작 및 아이디어**:
  - ✅ 정원사 풀샷 (폐허 옥상, 초록 새싹)
  - 정원사 클로즈업, 비 맞는 정원사

### 사이보그 수도승 (Cyborg Monk)
- Flowing dark hooded robes + partial mechanical implants on jaw/temple
- Glowing red circuitry lines, 명상/기도 자세

### 잠수부 (The Descent)
- Vintage copper deep-sea diver suit, brass helmet with round porthole
- 심해/어두운 우물 하강

---

## 4. 프롬프트 공식 (Cinematic Photorealistic)

### 10단계 구조
```
[1. 샷 종류] + [2. 카메라 스펙] + 
[3. 메인 피사체 디테일 - 재질/상태/표정] + 
[4. 환경/배경 디테일] + 
[5. 조명 설정 - 방향/강도/효과] + 
[6. 컬러 팔레트] + 
[7. 무드 키워드] + 
[8. 후처리 효과 - 그레인/플레어/심도] + 
[9. 감독/작품 레퍼런스] + 
[10. 파라미터]
```

### 필수 키워드

**카메라**
- `Cinematic [wide shot / medium shot / close-up / extreme close-up]`
- `photorealistic`
- `shot on ARRI Alexa LF` (또는 Alexa Mini LF, Alexa 65)
- `[35-100]mm anamorphic lens at f/[1.8-2.8]`
- `shallow depth of field`

**재질 디테일** (구체적으로)
- ❌ "old robe" → ✅ "heavy black wool robe with visible fabric weave, frayed edges, dust on the shoulders"
- ❌ "worn suit" → ✅ "weathered white spacesuit with yellowed patches, scuffs, faded mission patches, small tears"

**조명**
- `single hard key light from above`
- `strong rim light`
- `deep falloff into pure black background`
- `volumetric light rays catching dust particles`

**후처리**
- `subtle film grain`
- `anamorphic lens flares`
- `slight chromatic aberration on highlights`
- `atmospheric haze`
- `8k photorealistic detail`

**감독 레퍼런스** (반드시 하나 포함)
- `shot like a still from a Denis Villeneuve film`
- `shot like a still from Children of Men`
- `shot like a still from Stalker or Annihilation`

### 표준 파라미터
```
--ar 16:9 --style raw --s 750 --v 6.1
```

---

## 5. "플로팅 메쉬" 특수 표현

머리 위에 떠 있는 메쉬 후광이 우주헬멧으로 변형되는 문제 해결:

### 필수 표현
- `floats above the head like a saint's halo in a renaissance painting`
- `suspended in mid-air with a clear empty gap between the floating mesh and the head`
- `glowing red neon outlines along the edges of the levitating mesh`
- `completely detached from the body`
- `the mesh does NOT touch the head`

### 필수 Negative Prompt
```
--no glass helmet, astronaut helmet, bubble helmet, dome helmet, enclosed sphere, mesh touching head
```

---

## 6. 배너/프로필 디자인 규칙

### 유튜브 배너
- **사이즈**: 2560 x 1440 pixels
- **안전영역 (모바일 가시 영역)**: 중앙 1546 x 423 pixels
- **워크플로우**:
  1. AI로 텍스트 없는 배경만 생성 (16:9)
  2. Upscayl로 2560x1440 업스케일
  3. Canva "YouTube 채널 아트" 템플릿에서 텍스트 입히기
  4. 폰트: Bebas Neue 또는 Archivo Black
  5. 부제 스타일: `UNDERGROUND SCHRANZ // HARD TECHNO // EUROPEAN SCENE`

### 프로필 사진
- **사이즈**: 800 x 800 pixels (1:1)
- **원칙**: 작아져도 (48x48) 알아볼 수 있는 단순한 실루엣
- **디테일 많으면 안됨** — 댓글창에서 뭉개짐

---

## 7. 시네마틱 와이드 컷 (썸네일용)

### 컨셉 방향 예시
1. **Crimson Ritual** — 빨강 + 폐허, 왕좌, 의식
2. **Void Meditation** — 청록 + 우주, 명상, 고독
3. **Frost Melancholy** — 차가운 블루 + 해골, 고딕
4. **Steel Warfare** — 회색 + 사이버 솔저, 도시
5. **Ember Pilgrim** — 주황 + 사막, 순례, 황혼
6. **Shadow Cult** — 검정 + 의식, 제단, 컬트

### "한 장에 이야기 하나" 원칙
- 보는 사람이 3초 멈추게 만드는 디테일 하나
- 거의 단색 + 한 점만 강조 컬러
- 장르 믹스 O (슬라브 민속 + 사이버, 우주 + 식물도감 등)

---

## 8. 모션/영상화 키워드 (Higgsfield, Kling)

느린 움직임이 핵심:
- `slow zoom in` / `slow camera pan` / `subtle head turn`
- `dust particles drifting` / `embers slowly floating upward`
- `breath visible in cold air` / `fabric moving slightly in wind`
- **Motion strength**: 실사/마스크 캐릭터는 4-5, 애니 스타일은 1-2

---

## 9. 사용 도구

- **이미지 생성**: Midjourney v6.1 (최우선), Higgsfield, Flux Pro
- **업스케일**: Upscayl (무료, 오픈소스)
- **편집/합성**: Canva (배너/썸네일 텍스트), Photopea (무료 PS 대체)
- **영상화**: Higgsfield, Kling 3.0
- **음악**: Suno
- **편집**: CapCut

---

## 10. 응답 스타일 선호

- "프롬프트만 줘" → 설명 최소화, 바로 제공, 변주 3-5개
- "디자인 조언" → 문제점 분석 + 개선안 + 이유 + 대안
- 한국어로 답변, 영어 프롬프트는 코드블록으로
- 참조 사진이 있으면 그걸 최우선으로 읽고 맞춤 대응

---

## 11. 완성작 기록

- ✅ 사신 + 오렌지 태비 고양이
- ✅ 죽은 우주비행사 클로즈업 (꽃 피는 헬멧)
- ✅ 죽은 우주비행사 와이드 (두 개의 태양)
- ✅ 가스마스크 정원사 (폐허 옥상, 초록 새싹)
- ✅ 배너 v1 — 검정 + 빨간 수직 라인 + EISENHERZ 텍스트 (안전영역 이슈 수정 중)

---

*이 문서는 Eisenherz 채널 작업의 기준 참고 문서입니다. 고정 시스템이 아니라 참조 사진과 함께 유연하게 사용.*
