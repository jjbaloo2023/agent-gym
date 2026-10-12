FROM python:3.13-slim@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 gym && useradd --uid 10001 --gid gym --create-home gym \
    && mkdir /data && chown gym:gym /data
COPY agent_gym/ ./agent_gym/
COPY tests/ ./tests/
COPY scripts/*.py ./scripts/
COPY evidence/cfd-interruption-v1/ ./evidence/cfd-interruption-v1/
USER gym
ENTRYPOINT ["python", "-m", "agent_gym"]
CMD ["--help"]
