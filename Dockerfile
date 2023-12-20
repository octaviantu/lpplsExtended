# Use an official Python runtime as a parent image
FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . /usr/src/app

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install the lppls package using setup.py
RUN python setup.py install

# Expose port for the app
EXPOSE 8000

CMD ["python", "/usr/src/app//update_and_check_bubbles.py", "--backtest-start", "400"]
