# Hugging Face Space (Docker, CPU) for the Overcut.ai API.
# The build clones the public GitHub repo, so the Space repo only needs this
# Dockerfile and README.md. Rebuild the Space ("Factory rebuild") after pushing
# changes to GitHub.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hf-cache

RUN apt-get update \
 && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/KURO-1125/Overcut.ai.git /app

WORKDIR /app

# CPU wheels first so the pinned requirements do not pull the CUDA builds
RUN pip install torch==2.5.1 torchvision==0.20.1 \
      --index-url https://download.pytorch.org/whl/cpu

RUN pip install -r backend/requirements.txt

ENV OVERCUT_ENV=production \
    OVERCUT_DATA_DIR=/tmp/overcut-data

COPY start.sh /app/start.sh

EXPOSE 7860

CMD ["sh", "/app/start.sh"]
