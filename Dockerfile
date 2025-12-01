# Dockerfile for Library Management System (Flask)
# - Base: small Python image
# - Runs Flask app on port 5000
# - Uses internal SQLite DB (auto-initialized by app at startup)

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

EXPOSE 5000

# Run the Flask development server bound to all interfaces
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

# Build & Run:
#   docker build -t library-app .
#   docker run -p 5000:5000 library-app

