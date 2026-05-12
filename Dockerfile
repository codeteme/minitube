FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG INSTALL_ASR_DEPS=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-asr.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN if [ "$INSTALL_ASR_DEPS" = "1" ]; then pip install --no-cache-dir -r requirements-asr.txt; fi

COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "src.video_crud_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
