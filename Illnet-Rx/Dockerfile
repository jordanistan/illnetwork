FROM python:3.12-slim

# Tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    clamav clamav-freshclam rkhunter net-tools iproute2 procps \
    coreutils findutils ca-certificates curl sudo tini \
    sshfs fuse \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY scanner/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy code
COPY scanner /opt/scanner
COPY webui /opt/webui
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

ENV OUTPUT_DIR=/opt/data/reports
RUN mkdir -p ${OUTPUT_DIR}

WORKDIR /opt/webui
EXPOSE 5000

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["python","app.py"]

