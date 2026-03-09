FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        iproute2 \
        iputils-ping \
        netcat-openbsd \
        openssh-client \
        procps \
        rsync \
        sudo \
        vim \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash -u 1000 druser \
    && echo "druser ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-druser

USER druser
WORKDIR /workspace

CMD ["bash"]
