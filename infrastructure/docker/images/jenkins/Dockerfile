FROM jenkins/jenkins:lts-jdk17

USER root

WORKDIR /var/jenkins_home

# Install system dependencies and Docker
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        docker.io curl git unzip \
        python3 python3-pip python3-venv python3-dev python3-apt \
        iputils-ping netcat-traditional rsync \
        build-essential libpq-dev jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ARG DOCKER_COMPOSE_VERSION=2.24.0
RUN curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose

ARG DOCKER_GID=999
RUN groupadd -f -g ${DOCKER_GID} docker || true && \
    usermod -aG docker jenkins && \
    usermod -aG root jenkins && \
    usermod -aG sudo jenkins && \
    echo "jenkins ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER jenkins
COPY infrastructure/jenkins/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY infrastructure/jenkins/casc.yaml /var/jenkins_home/casc.yaml
ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc.yaml

RUN mkdir -p workspace jobs logs plugins secrets && \
    chown -R jenkins:jenkins /var/jenkins_home

COPY .env ./.env-template

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/login || exit 1

ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

ARG JENKINS_HTTP_PORT=8080
ARG JENKINS_AGENT_PORT=50000
EXPOSE ${JENKINS_HTTP_PORT} ${JENKINS_AGENT_PORT}

USER root
ENTRYPOINT ["/bin/bash", "-c", "chmod g+rw /var/run/docker.sock 2>/dev/null || true; exec su jenkins -c 'java -Duser.home=/var/jenkins_home -Djenkins.install.runSetupWizard=false -jar /usr/share/jenkins/jenkins.war'"]