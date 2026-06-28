FROM python:3.13-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs

# Install tzdata
RUN apt-get update && \
    apt-get install -y tzdata

ENV TZ=Asia/Singapore

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python","query_entry.py","--ui"]