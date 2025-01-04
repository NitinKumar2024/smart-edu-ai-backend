# Use the latest Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the application's port
EXPOSE 5000

# Use Gunicorn as the WSGI server for production
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
