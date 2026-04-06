# net-os central API — multi-stage build
# Stage 1: dependency builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv
RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Stage 2: runtime
FROM python:3.12-slim

# Install docker CLI (to inspect containers via mounted socket)
# and openssh-client (for SSH to PC host)
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        openssh-client \
        docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

COPY main.py .

# Create data directory for SQLite
RUN mkdir -p /data /configs

# SSH config for reaching the PC host
# Mount your SSH key at /root/.ssh/id_rsa via Docker secret or volume
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Default SSH config — override by mounting /root/.ssh/config
RUN echo "Host pc\n\
    HostName 192.168.0.27\n\
    User batma\n\
    StrictHostKeyChecking no\n\
    IdentityFile /root/.ssh/id_rsa\n\
    ConnectTimeout 5\n" > /root/.ssh/config && \
    chmod 600 /root/.ssh/config

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/ping 2>/dev/null || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
