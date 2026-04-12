FROM orbitdec-foundation:latest

WORKDIR /app

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server sudo curl ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ARG TEST_USER_PASSWORD=jenkins123
RUN useradd -m test_user && \
    echo "test_user:${TEST_USER_PASSWORD}" | chpasswd && \
    mkdir -p /home/test_user/.ssh && \
    chmod 700 /home/test_user/.ssh

RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config

RUN echo "test_user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/test_user && \
    chmod 440 /etc/sudoers.d/test_user

COPY infrastructure/docker/images/api-test/requirements.txt .
RUN pip install -r requirements.txt && \
    rm requirements.txt

COPY --chown=test_user:test_user . .

ARG API_PORT=8000
ARG SSH_PORT=2223
EXPOSE ${API_PORT} ${SSH_PORT}

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

COPY infrastructure/docker/images/api-test/test_init_script.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/test_init_script.sh

USER test_user
CMD ["/usr/local/bin/test_init_script.sh"]