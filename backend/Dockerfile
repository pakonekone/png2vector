# Stage 1: Build autotrace from source
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libglib2.0-dev \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/autotrace/autotrace.git /tmp/autotrace \
    && cd /tmp/autotrace \
    && ./autogen.sh \
    && ./configure --without-magick --without-pstoedit \
    && make -j$(nproc) \
    && make install

# Stage 2: Runtime image
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y \
    potrace \
    libglib2.0-0 \
    libpng16-16 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/autotrace /usr/local/bin/autotrace
COPY --from=builder /usr/local/lib/libautotrace* /usr/local/lib/
RUN ldconfig

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
