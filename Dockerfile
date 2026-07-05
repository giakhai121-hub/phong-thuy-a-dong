FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (Render sets $PORT dynamically, but default to 8000)
EXPOSE 8000

# Start command
CMD ["python", "app.py"]
