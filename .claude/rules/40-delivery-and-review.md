# Delivery And Review

## Report format

- report 단계에서 반드시 포함할 섹션:
  - 변경 목적
  - 변경 파일
  - 위험 요소
  - 검증 결과
  - 남은 이슈

- 보고서 파일 저장 위치 및 명명 규칙:
  - 위치: `.report/` 디렉토리 (없으면 자동 생성)
  - 파일명: `[YYYYMMDD]_[ISSUE#]_[간단한설명].md`
  - 예시: `20260401_#205_주문완료_페이지_개발.md`
  - 날짜: 작업 완료 시점 (YYYYMMDD 형식)
  - 설명: 한글/영문, 단어 구분은 언더스코어
  - `.report/`는 `.gitignore`로 제외된 로컬 전용 디렉토리다. 파일은 반드시 로컬에 작성만 하고, `git add -f` 등 force 옵션으로 `.gitignore`를 우회해 강제로 git에 추적시키지 않는다(git 관련 절대 규칙은 `20-team-conventions.md`의 "Git 안전 규칙" 참고).

- 보고서 작성 핵심 원칙:
  - **작성자/작성일 필드 절대 포함 금지** — 파일명에 날짜 포함되므로 별도 기록 불필요
  - **AI 도구명 언급 금지** (Claude, GPT, Copilot, Cursor 등)
  - 능동태, 키워드 기반 문장으로 가독성 향상
  - 민감 정보(토큰, 비밀번호, API Key) 발견 시 `{TOKEN}`, `{API_KEY}`, `{PASSWORD}` 형식으로 마스킹

- 보고서 구조:

  ```markdown
  ### 📌 작업 개요
  [2-3줄 요약]

  ### 🎯 구현 목표 (기능 구현) 또는 🔍 문제 분석 (버그 수정)
  [목적 또는 문제 원인]

  ### ✅ 구현 내용

  #### [주요 변경사항 1]
  - **파일**: `경로/파일명`
  - **변경 내용**: [구체적인 설명]
  - **이유**: [왜 이렇게 수정했는지]

  ### 🔧 주요 변경사항 상세
  [코드 변경 내용을 자연스럽게 설명. 특이사항 포함]

  ### 🧪 검증 결과
  [lint, build, 테스트 결과. PASS/FAIL 명시]

  ### ⚠️ 위험 요소
  [없으면 "없음" 명시]

  ### 📌 남은 이슈
  [후속 작업, 미검증 경로, TODO 등]
  ```

- 작성 스타일 기준:

  **좋은 예:**
  ```
  "gitignore 중복 항목 추가 문제 확인. 정규화 함수 추가하여 중복 체크 로직 구현"
  "주문 저장 실패 시 에러 모달 노출 처리 누락 확인. onError 핸들러 추가로 수정"
  ```

  **나쁜 예:**
  ```
  "중복 항목 추가 문제가 확인되었습니다. 정규화 함수가 생성되었습니다."  # 수동태 금지
  "Claude가 분석한 결과..."  # AI 이름 금지
  "작성자: Claude Code"  # 작성자 필드 금지
  ```

- 보고서 분석 프로세스:
  1. `git status` 한 번만 실행 → 변경된 파일명 확인
  2. 이슈 내용 기반으로 관련 파일만 선별
  3. 선별된 파일을 직접 읽어서 변경 내용 분석
  4. 이후 추가 git 명령어 사용 금지 (토큰 낭비)

## Pull request expectations

- PR 제목 규칙:
  - 형식: `[브랜치명] : [타입] : [설명] [이슈링크]`
  - 타입: `feat` (기능), `fix` (버그), `refactor`, `chore`, `docs`
  - 예시: `eodaego_ai_FastAPI_프로젝트_초기_스캐폴딩_구축 : feat : Dockerfile을 uv 기반 Python 3.12·포트 8000 구성으로 교체 https://github.com/eodaego/eodaego-AI/issues/1`
  - 브랜치명·커밋 메시지는 이슈 코멘트의 helper 블록(Chuseok22 issue-helper Action이 이슈 생성 시 자동 추가)을 그대로 사용한다 — 현재 프로젝트의 실제 커밋 메시지 패턴 참고: `git log` 확인

- PR 본문 구조:
  - `.report/` 에 저장된 보고서 내용을 기반으로 작성
  - 변경 목적, 주요 변경 파일, 검증 결과 포함
  - 스크린샷: 해당 없음(API 전용 서버, UI 없음). Swagger UI/curl 검증 결과가 있으면 첨부

- reviewer 지정 방식:
  - 팀 내 규칙에 따름 (미정의)

- linked issue 규칙:
  - PR 제목 또는 본문에 이슈 URL 포함
  - 현재 패턴: `https://github.com/eodaego/eodaego-AI/issues/[번호]`

## Delivery constraints

- 배포 전 확인 사항:
  - `uv run ruff check .` — 0 errors
  - `uv run ruff format .` — 포맷 적용 완료
  - `uv run mypy app` — strict 통과, 에러 없음
  - (테스트 코드 미작성 정책 — `30-testing-and-verification.md` 참고)
  - `docker build -t eodaego-ai .` — 빌드 성공 확인
  - 환경변수(`APP_ENV`, `INTERNAL_API_KEY`, `DATABASE_URL`) `.env.local`/`.env.production` 및 CI `secrets.ENV_FILE` 설정 확인
  - CI(`python-server-cicd.yml`) 배포 시 `eodaego-internal` 네트워크로 join되는지 확인. **임시 예외(2026-07-24~실서비스 전환 전까지)**: 개발 편의 목적의 `-p 8001:8000` 추가는 정상이며, 그 외 포트가 추가되지 않았는지만 확인. 실서비스 전환 시 `-p` 옵션이 완전히 제거되었는지 반드시 재확인한다.

- feature flag 정책:
  - 현재 미사용. 내부 전용 CRUD/추천 API로 사용자 대상 A/B 테스트 대상이 아니라 도입 필요성이 낮음.

- rollback 필요 시 기준:
  - `GET /health`가 503을 반환하거나 컨테이너가 기동에 실패하는 경우 즉시 롤백
  - `X-Internal-Api-Key` 인증 또는 `eodaego-internal` 네트워크 격리 설정 오류로 BE 연동이 끊긴 경우 즉시 롤백
  - **임시 예외 기간 중(2026-07-24~실서비스 전환 전까지) 8001 포트로 비정상 접근·보안 이슈가 확인된 경우 즉시 `-p` 옵션을 제거해 원복한 뒤 재배포**
  - 롤백 방법: 이전 커밋으로 revert PR 생성 후 재배포, 또는 NAS에서 이전 DockerHub 이미지 태그로 재배포
