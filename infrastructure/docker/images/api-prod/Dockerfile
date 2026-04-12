FROM orbitdec-foundation:latest

WORKDIR /app

USER root

# Install SSH server for remote access
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server sudo curl ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY infrastructure/docker/images/api-prod/requirements.txt .
RUN pip install -r requirements.txt && \
    rm requirements.txt

ARG PROD_USER_PASSWORD=jenkins123
RUN useradd -m prod_user && \
    echo "prod_user:${PROD_USER_PASSWORD}" | chpasswd && \
    mkdir -p /home/prod_user/.ssh && \
    chmod 700 /home/prod_user/.ssh

# Configure SSH daemon
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config

RUN echo "prod_user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/prod_user && \
    chmod 440 /etc/sudoers.d/prod_user

COPY --chown=prod_user:prod_user . .

RUN mkdir -p logs data reports && \
    chown -R prod_user:prod_user /app

ARG API_PORT=8000
ARG SSH_PORT=2224
EXPOSE ${API_PORT} ${SSH_PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

COPY infrastructure/docker/images/api-prod/prod_init_script.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/prod_init_script.sh

USER prod_user
CMD ["/usr/local/bin/prod_init_script.sh"]
