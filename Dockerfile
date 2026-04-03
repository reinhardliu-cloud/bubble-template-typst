FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.11 python3-pip \
    pandoc \
    wget tar xz-utils \
    fontconfig \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Install typst
RUN wget -q https://github.com/typst/typst/releases/download/v0.14.2/typst-x86_64-unknown-linux-musl.tar.xz \
    && tar xf typst-x86_64-unknown-linux-musl.tar.xz \
    && mv typst-x86_64-unknown-linux-musl/typst /usr/local/bin/typst \
    && rm -rf typst-x86_64-unknown-linux-musl* \
    && typst --version

COPY requirements.txt /tmp/requirements.txt
RUN python3.11 -m pip install --no-cache-dir -r /tmp/requirements.txt

# Copy app code
COPY app/ /app/

# Copy bubble template resources (template.typ, fonts, assets from repo root)
COPY template.typ /app/templates/bubble/template.typ
COPY fonts/ /app/templates/bubble/fonts/
COPY assets/ /app/templates/bubble/assets/

# Sessions directory
RUN mkdir -p /sessions

WORKDIR /app

EXPOSE 8080

CMD ["python3.11", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
