FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Generate data & mine on build (so image is ready to run)
RUN python data/generate_synthetic.py && python data/load_data.py && python -m mining.association --min-support 0.015 --min-confidence 0.25 && python -m mining.clustering --k 4 && python -m mining.outliers --contamination 0.05 && python evals/generate_eval.py || true
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
