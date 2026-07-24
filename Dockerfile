# Python 3.12 slim 베이스 이미지 사용
FROM python:3.12-slim

# 기본 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Seoul \
    APP_PORT=8000

# 작업 디렉터리
WORKDIR /app

# 시스템 패키지 (필요 최소한만)
# - ca-certificates: https 요청 시 인증서 문제 방지
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# uv 설치
RUN pip install --no-cache-dir uv

# 의존성 정의 파일 먼저 복사 (Docker 레이어 캐시 효율 ↑)
COPY pyproject.toml uv.lock /app/

# uv.lock에 고정된 의존성 그대로 설치(재해석 없이 재현 가능한 빌드)
RUN uv sync --frozen

# 애플리케이션 소스 코드 복사
COPY . /app

# FastAPI/uvicorn이 리스닝할 포트. 실제 호스트 노출 여부는 EXPOSE가 아닌 `docker run -p` 옵션이 결정한다
# (임시 예외(2026-07-24~실서비스 전환 전까지): 배포 시 -p 8001:8000으로 호스트 공개 중 — .claude/rules/00-project-overview.md 참고)
EXPOSE 8000

# 컨테이너 기본 실행 커맨드
# APP_PORT 환경변수를 이용해 포트 변경 가능 (기본 8000)
CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}"]
