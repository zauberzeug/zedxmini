FROM stereolabs/zed:4.1-py-devel-l4t-r36.3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install "numpy>=1.20.1,<2.0.0"

# Ensure Python output isn't buffered
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy source code
COPY . .

# Command to run the service
CMD ["python3", "-u", "src/sender.py"] 