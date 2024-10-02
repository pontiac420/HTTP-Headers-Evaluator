# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the Container directory contents into the container at /app
COPY Container /app

# Install any needed packages
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Set the environment variable for the script directory
ENV SCRIPT_DIR=/app 

# Run streamlit when the container launches
CMD ["streamlit", "run", "streamlit_app.py"]