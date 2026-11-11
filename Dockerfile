# docker build -t <dockerhub-user>/kittyson .

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /code
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/code/.venv/bin:$PATH"

# 의존성만 먼저 설치해 레이어 캐시를 살린다
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 프로젝트는 editable로 설치된다. 화면 파일(static)은 src 안에서 그대로 서빙된다.
COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# 오늘의 고양이 캐시와 직접 넣은 사진: /code/data (볼륨)
EXPOSE 8000
CMD ["uvicorn", "kittyson.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
