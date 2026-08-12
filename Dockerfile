FROM python:3.12-slim

WORKDIR /srv
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chroma's default embedder pulls a 79MB ONNX model the first time it embeds
# anything. Left to runtime that download lands on the first chat or journal
# request after every deploy — measured at ~20s, and a live dependency on
# Chroma's CDN at exactly the moment someone is waiting for an answer.
#
# Baking it in costs ~167MB of image and makes the first request as fast as
# the thousandth. This sits above the COPY lines on purpose: it only depends
# on requirements.txt, so a code push reuses the cached layer instead of
# re-downloading the model on every build.
#
# Chroma resolves the cache from Path.home(), so build and runtime must agree
# on HOME; pinned here rather than inherited so a base-image change can't
# silently send the runtime looking somewhere empty. The assertion turns that
# same failure into a red build instead of a slow first request in Greece.
ENV HOME=/root
RUN python -c "\
import os, sys; \
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; \
ef = ONNXMiniLM_L6_V2(); ef(['warm']); \
model = os.path.join(ef.DOWNLOAD_PATH, ef.EXTRACTED_FOLDER_NAME, 'model.onnx'); \
sys.exit(0 if os.path.isfile(model) else 'ONNX model not cached at ' + model)"

COPY backend/app ./app
COPY knowledge ./knowledge

ENV KNOWLEDGE_DIR=/srv/knowledge \
    DATA_DIR=/data \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
