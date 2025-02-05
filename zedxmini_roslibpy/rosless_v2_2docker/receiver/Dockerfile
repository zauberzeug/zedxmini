FROM python:3.10-slim

# Install minimal dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install "opencv-python==4.9.0.80" "numpy>=1.20.1,<2.0.0" "flask"

WORKDIR /app

# Copy source code
COPY . .

# Command to run the service
CMD ["python3", "src/receiver.py"] 