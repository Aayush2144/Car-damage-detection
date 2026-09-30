# Stage 1: Build React + Vite Frontend (CrashSite Forensic SPA)
FROM node:20-slim AS web-builder
WORKDIR /build/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Python FastAPI + PyTorch ResNet-50 Runtime
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY model/ ./model/
COPY samples/ ./samples/
COPY api/ ./api/
COPY app.py model_helper.py ./
COPY --from=web-builder /build/web/dist ./web/dist

EXPOSE 8000
CMD ["uvicorn", "main:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8000"]
