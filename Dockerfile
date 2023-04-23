# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY mysql-proxy.py .

EXPOSE 3306

# Run the Python script when the container starts
CMD ["python", "mysql-proxy.py"]
