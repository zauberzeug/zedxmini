FROM zauberzeug/rosys:latest

# Install git and other dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Clone and install norospy
RUN git clone https://gitlab.kit.edu/kit/aifb/ATKS/public/norospy.git /norospy
WORKDIR /norospy
RUN pip install -e .

# Install additional Python packages
RUN pip install foxglove-websocket

# Set working directory back to /app
WORKDIR /app
