# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# # Install system dependencies
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#     && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /toolbox-alerts

# Copy the current directory contents into the container at /app
COPY . /toolbox-alerts

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8009 5672 5555 15672

