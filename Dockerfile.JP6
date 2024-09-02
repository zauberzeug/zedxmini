FROM stereolabs/zed:4.1-py-devel-l4t-r36.3

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update && apt install -y \
    sudo vim less ack-grep rsync wget curl cmake build-essential 

RUN python3 -m pip install --upgrade pip

RUN --mount=type=cache,target=/home/zauberzeug/.cache/pip \ 
        python3 -m pip install rosys==0.12.0

# ENTRYPOINT ["tail"]
# CMD ["-f","/dev/null"]
WORKDIR /app
CMD python3 main.py