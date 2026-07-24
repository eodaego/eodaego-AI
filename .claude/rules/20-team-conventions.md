# Team Conventions

## Naming

- 변수명 규칙: snake_case (PEP 8)
- 메서드명 규칙: snake_case, 동사+명사 형태 (`create_prompt_template`, `bootstrap_scheduler`)
- 클래스 / 컴포넌트명 규칙: PascalCase. SQLAlchemy 모델은 `ScheduleConfig`, `PromptTemplate`처럼 단수형 도메인 명사. Pydantic 스키마는 `<Model>Create` / `<Model>Update` / `<Model>Response` 접미사 패턴을 고정으로 사용한다.
- 축약 금지 여부 및 예외: 축약은 지양한다. 단 `db: Session`처럼 이미 코드 전반에 자리 잡은 극히 일반적인 축약은 허용한다.

## Code style

- 명시적 타입 사용 규칙: 모든 함수 시그니처에 타입 힌트 필수(`mypy --strict` 통과 기준). `X | None` 형태의 최신 union 문법을 사용한다(Python 3.12, `from __future__ import annotations` 불필요).
- any 사용 여부: 지양한다. `mypy --strict` 모드이므로 `Any` 사용 시 반드시 사유가 있어야 한다.
- deprecated API 사용 기준: 사용 금지. ruff의 `UP`(pyupgrade) 룰이 활성화되어 있어 최신 문법을 강제한다.
- 에러 처리 방식: 라우터/서비스에서 `fastapi.HTTPException`을 던지고, `core/errors.py`의 전역 핸들러가 `{success, data, error:{code, message}}` 포맷으로 통일 변환한다. 개별 라우터에서 직접 `JSONResponse` 에러 바디를 만들지 않는다.
- 주석 작성 기준: 기본적으로 주석 없이 작성하고, 비직관적인 이유(왜 이렇게 결정했는지)가 있을 때만 한글 주석을 추가한다. 예: `app/scheduler/registry.py`의 "잘못된 trigger_config로 앱 기동 전체가 실패하지 않도록 개별 job 실패를 격리한다", `Dockerfile`의 "-p 옵션 없음 → 호스트/외부에서 접근 불가".

## Responsibility separation

- service / repository / controller / component / hook / util 역할 기준: repository 계층은 두지 않는다 — `service`가 SQLAlchemy `Session`으로 직접 CRUD를 수행한다(도메인 수·복잡도가 적어 별도 추상화를 생략하기로 결정). `router`가 controller, `service`가 비즈니스 로직, `model`이 ORM, `schema`가 DTO 역할을 한다.
- 비즈니스 로직 위치 기준: 항상 `service.py`. `router.py`에는 인증 dependency 지정, `service` 호출, 404 등 HTTP 레벨 예외 변환만 둔다.
- 화면 로직과 데이터 로직 분리 기준: 해당 없음 — API 전용 서버로 화면을 제공하지 않는다(관리자 화면은 BE가 SSR로 담당).

## Review expectations

- 리뷰 시 반드시 확인할 항목: 신규 엔드포인트에 `X-Internal-Api-Key` 인증 dependency가 빠지지 않았는지, 도메인 간 직접 import(경계 위반)가 없는지, sync 엔진 원칙을 깨는 async 세션 도입이 없는지, 새 의존성이 import 시점에 외부 네트워크 호출·모델 다운로드를 하지 않는지.
- 성능 / 보안 / 유지보수 관점 체크리스트: 모든 신규 엔드포인트가 `/api/v1` 프리픽스와 공통 에러 포맷을 따르는지, Docker 배포 스크립트에 `-p` 옵션이 (임시 예외 기간 동안 허용된 8001 외에) 추가되지 않았는지.
- 리뷰에서 block 걸어야 하는 기준: 인증 dependency 누락, import 시점 동기 외부 다운로드 라이브러리 도입, 테스트 코드 추가(정책 위반 — 별도 논의 없이는 금지), git force성 명령 사용(아래 참고). **호스트 포트 바인딩 추가는 원칙적으로 block 대상이나, 임시 예외 기간(2026-07-24~실서비스 전환 전까지)의 8001 포트 공개는 예외로 허용한다 — 그 외 포트 추가나 예외 기간 종료 후에도 남아있는 바인딩은 계속 block 대상.**

## Git 안전 규칙 (절대 규칙)

- `git add -f`/`--force`(`.gitignore` 우회 포함), `push -f`/`--force`/`--force-with-lease`, `checkout -f`, `clean -f`(`-fd`/`-fdx` 포함), `branch -D`, `reset --hard`, 공유 브랜치에 대한 `commit --amend` 등 모든 force성 git 명령은 **절대 금지**한다. 사용자가 그 순간 명시적으로 정확히 그 작업을 요청한 경우가 아니면 예외 없이 사용하지 않는다.
- `.gitignore`로 제외된 파일(`docs/`, `.report/` 등)은 제외된 상태를 그대로 존중한다. 커밋이 필요해 보이더라도 강제로 추적시키지 않고 먼저 사용자에게 확인한다.
- 서브에이전트에 작업을 위임할 때도 이 규칙을 프롬프트에 명시하여, 서브에이전트가 임의로 force 옵션을 쓰지 않도록 한다.
