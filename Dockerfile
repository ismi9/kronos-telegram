FROM python:3.11-slim
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
# CPU-колесо torch ~200МБ замість CUDA на ~2.5ГБ
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
