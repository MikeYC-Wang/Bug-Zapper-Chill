# 🐛⚡ Bug-Zapper & Chill

<div align="center">

[繁體中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

</div>

<div align="center">

<img src="./profile-hud.svg" alt="Bug-Zapper & Chill hardware HUD dashboard" width="850" />

**제 GitHub 활동을 실시간으로 반영하는 사이버펑크 블랙 & 골드 하드웨어 콘솔**
*(위 이미지가 아직 보이지 않는다면 [HUD Updater](.github/workflows/hud-updater.yml)가 아직 한 번도 실행되지 않은 것입니다)*

</div>

---

## 이것은 무엇인가요?

`Bug-Zapper & Chill`은 완전히 독창적인 GitHub 프로필 동적 대시보드 프로젝트입니다. 매일 자동으로 다음을 수행합니다:

1. GitHub GraphQL API v4를 통해 지난 365일간의 Contribution Calendar 통계를 가져옵니다.
2. 순수 Python 문자열 포매팅만으로(matplotlib / Pillow 같은 드로잉 라이브러리는 **전혀 사용하지 않음**) 네이티브 SVG를 직접 조립합니다.
3. `profile-hud.svg`를 생성하여 좌우 두 개의 핵심 하드웨어 컴포넌트를 그립니다:

| 컴포넌트 | 설명 |
|---|---|
| 🧪 **과열 액체 냉각 순환 시스템** | CPU 워터블록에 연결된 사각 루프형 저장 탱크. 냉각수 수위, 떠오르는 기포 애니메이션, PUMP SPEED / COOLANT TEMP / SYS PRESSURE 수치가 오늘의 커밋 수에 따라 동적으로 변합니다（`24°C [STANDBY]` ~ `84°C [OVERCLOCK]`）. |
| ⚡ **EM 버그 요격 방어 타워** | 번개를 발사하는 원뿔형 방어 타워. 매일 당신의 커밋 수로 "오늘 제거한 버그 수"를 계산하고, 발버둥치는 노란색 버그와 `NullPointer` 예외를 함께 전격으로 처치합니다. |

이 이미지는 매일 [GitHub Actions](.github/workflows/hud-updater.yml)에 의해 자동으로 다시 생성되어 `main` 브랜치에 커밋되며, 수동 유지 관리가 필요하지 않습니다.

---

## 프로젝트 구조

```
Bug-Zapper-Chill/
├── src/generate_hud.py             # 핵심: 데이터 수집 + SVG 수동 조립
├── profile-hud.svg                 # 자동 생성 결과물 (workflow가 매일 덮어씀)
├── .github/workflows/hud-updater.yml   # 매일 실행되는 예약 자동화 워크플로우
└── README.md
```

---

## 내 프로필에 적용하는 방법

1. **Personal Access Token (classic)**을 생성합니다. 최소 `read:user` 권한이 필요합니다 (대상 저장소가 비공개라면 `repo` 권한도 추가하세요).
2. 이 저장소의 **Settings → Secrets and variables → Actions**에서 `GH_PAT`라는 이름의 Repository secret을 새로 만들고 방금 발급받은 토큰을 붙여넣습니다.
3. (선택 사항) 다른 사용자를 모니터링하려면 workflow의 `HUD_USERNAME` 환경 변수를 변경하세요 (기본값은 `MikeYC-Wang`).
4. **Actions → HUD Updater → Run workflow**를 한 번 수동으로 실행하여 `profile-hud.svg`가 올바르게 생성되고 커밋되는지 확인합니다.
5. 이후에는 2시간마다(UTC 0, 2, 4, ... 22) 자동으로 갱신되어, 오늘의 커밋을 더 빠르게 반영합니다.

자신의 개인 프로필 README (`<username>/<username>` 저장소)에 이 이미지를 삽입하려면 이 저장소가 생성하는 raw SVG를 직접 참조하면 됩니다:

```markdown
![Bug-Zapper & Chill HUD](https://raw.githubusercontent.com/MikeYC-Wang/Bug-Zapper-Chill/main/profile-hud.svg)
```

---

## 로컬 테스트

```bash
pip install requests
set GH_PAT=ghp_xxxxxxxxxxxxxxxxxxxx      # PowerShell: $env:GH_PAT="ghp_xxx"
set HUD_USERNAME=MikeYC-Wang
python src/generate_hud.py
```

성공하면 프로젝트 루트 디렉터리에 `profile-hud.svg`가 생성됩니다.

---

## 기술적 특징

- **드로잉 라이브러리 의존성 제로**: 루프 배관, 발광 필터, 그라디언트, 번개 지그재그 선 등 모든 시각 요소는 네이티브 `<svg>` 태그 문자열을 손으로 조립한 것이며, 래스터 이미지나 서드파티 드로잉 라이브러리를 전혀 사용하지 않습니다.
- **동적으로 연동되는 데이터**: 냉각 시스템과 방어 타워의 수치는 모두 "오늘의 커밋 수"로부터 실시간으로 계산되며, 하드코딩된 정적 값이 아닙니다.
- **실패는 실패로, 조작하지 않음**: 데이터 수집에 실패하면 스크립트는 즉시 0이 아닌 상태 코드로 종료되며, 가짜 데이터로 오해를 불러일으키는 HUD를 생성하지 않습니다.

---

## 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)로 배포됩니다. 원본 저작권 고지를 유지하는 한 자유롭게 사용, 수정, 재배포할 수 있습니다.

---

<div align="center">

**ENGINEER: MikeYC-Wang** · SYSTEM STATUS: ONLINE

</div>
