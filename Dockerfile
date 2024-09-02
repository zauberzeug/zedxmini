FROM stereolabs/zed:4.1-tools-devel-l4t-r35.4

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update && apt install -y \
    sudo vim less ack-grep rsync wget curl cmake build-essential software-properties-common
# The docker image comes with python 3.8, but we want to use python 3.11
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    add-apt-repository -y ppa:deadsnakes/ppa \
    && apt update && apt install -y python3.11 python3.11-dev python3.11-venv \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
RUN python3.11 /usr/local/zed/get_python_api.py
RUN --mount=type=cache,target=/home/zauberzeug/.cache/pip \ 
        python3.11 -m pip install rosys==0.12.0

# ENTRYPOINT ["tail"]
# CMD ["-f","/dev/null"]
WORKDIR /app
CMD python3.11 main.py