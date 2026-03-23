# Stage 1: Get autotrace binary from Debian Buster (last release that ships it)
FROM debian:buster-slim AS autotrace-src
# Buster is EOL, repos moved to archive.debian.org
RUN sed -i 's|http://deb.debian.org/debian|http://archive.debian.org/debian|g' /etc/apt/sources.list \
    && sed -i 's|http://security.debian.org/debian-security|http://archive.debian.org/debian-security|g' /etc/apt/sources.list \
    && sed -i '/buster-updates/d' /etc/apt/sources.list \
    && apt-get update && apt-get install -y --no-install-recommends autotrace

# Stage 2: Runtime image
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y \
    potrace \
    libglib2.0-0 \
    libpng16-16 \
    libjpeg62-turbo \
    libmagickcore-6.q16-6 \
    libmagickwand-6.q16-6 \
    libtiff5 \
    libgd3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=autotrace-src /usr/bin/autotrace /usr/local/bin/autotrace
RUN ldconfig

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
