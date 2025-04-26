# Use an official Python runtime as a parent image
FROM python:3.10-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /telnyx-chatbot

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir git+https://github.com/pipecat-ai/pipecat.git

# Copy the entire application first
COPY . .

# Download the audio file if it doesn't exist
RUN mkdir -p static && \
    if [ ! -f static/office-ambience.mp3 ]; then \
        echo "Downloading office-ambience.mp3..." && \
        curl -L -o static/office-ambience.mp3 https://raw.githubusercontent.com/Ayushbh6/Telnyx_AIbyDNA/main/static/office-ambience.mp3; \
    fi

# Verify the audio file exists and has content
RUN test -f static/office-ambience.mp3 && \
    test -s static/office-ambience.mp3 || \
    (echo "office-ambience.mp3 not found or empty in static directory" && exit 1)

# Expose the desired port
EXPOSE 8765

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765"]
