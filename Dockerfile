# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path for module imports
ENV PYTHONPATH=/app

# Run Evo-AI CLI
CMD ["python", "cli/cli.py"]
