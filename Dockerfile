FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tools/ tools/
COPY config/ config/

RUN mkdir -p data .tmp/runs

EXPOSE 8001

CMD ["uvicorn", "tools.api:app", "--host", "0.0.0.0", "--port", "8001"]
