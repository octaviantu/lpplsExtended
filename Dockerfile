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


# Execute commands during build
RUN python /usr/src/app/prices_db_management/create_db.py
RUN python /usr/src/app/prices_db_management/parse_largest_ETFs.py --fetch-tickers
RUN python /usr/src/app/prices_db_management/parse_most_traded_stocks_US.py --fetch-tickers
RUN python /usr/src/app/prices_db_management/parse_SP500_components.py --fetch-tickers
RUN python /usr/src/app/prices_db_management/parse_indexes.py

CMD ["python", "/usr/src/app/lppls/demo/demo_all_tickers.py", "--backtest-start", "200"]
