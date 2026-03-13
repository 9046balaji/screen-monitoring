FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the API port
EXPOSE 5000

# Start the Flask backend
CMD ["python", "app.py"]
