# Project Overview

## Purpose

- 이 프로젝트의 목적:
- 해결하려는 문제:
- 주요 사용자 또는 시스템 소비자:

## Primary Stack

- Language:
- Framework:
- Runtime:
- Database / storage:
- Infra / deployment:

## Important directories

- src/:
- app/:
- features/:
- modules/:
- test/ or tests/:
- docs/:
- scripts/:

## Main commands

- install:
- lint:
- typecheck:
- build:
- unit-test:
- integration-test:
- e2e-test:
- run-dev:
- run-prod-like:

## Project-specific constraints

- 반드시 지켜야 하는 제약:
  - **모듈 임포트/컨테이너 기동 시점에 외부에서 모델·가중치를 동기 다운로드하는 라이브러리 도입 금지(원칙)**: 이 AI 서버는 호스트 포트 미바인딩 + `eodaego-internal` 내부망 전용으로 배포된다(인바운드만 차단, 아웃바운드는 개인 LLM 서버/Vertex AI 호출을 위해 열려 있어야 함). 다른 사내 내부망 전용 AI 서버에서 실제로 발생한 사례: TrustMark류 라이브러리가 `import` 시점에 인터넷에서 모델을 다운로드하는데, 다운로드가 실패하면 앱 자체가 기동되지 않아 `/health`조차 응답하지 못함. 향후 `recommendation` 도메인 등에 로컬 임베딩/토크나이저 모델을 쓰는 라이브러리를 추가할 경우, (1) 다운로드를 첫 실제 요청 시점으로 지연 로딩하거나 (2) 이미지 빌드 타임에 모델 가중치를 이미지 안에 미리 포함시켜 런타임 다운로드를 없앨 것. 임포트 시점 동기 다운로드 방식은 채택하지 않는다.
- 사용 금지 기술 / 패턴:
- 현재 프로젝트에서 중요하게 보는 품질 기준:

## Change policy

- 어떤 변경은 허용되고 어떤 변경은 금지되는지:
- 지금 레포에서 수정해도 되는 범위:
- 절대 건드리면 안 되는 영역: