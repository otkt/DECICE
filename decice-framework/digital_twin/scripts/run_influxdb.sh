#!/bin/bash

# Define the directory for InfluxDB data in the current path
DATA_DIR="./influxdb_data"
INFLUXDB_ORG="decice"
INFLUXDB_BUCKET="cluster_snapshot"
INFLUXDB_URL="http://localhost:8086"

set_env_var() {
  local key="$1"
  local value="$2"
  local env_file=".env"

  # Remove existing key
  sed -i "/^${key}=/d" "$env_file"

  # Ensure file ends with a newline before appending
  [ -s "$env_file" ] && tail -c1 "$env_file" | read -r _ || echo >> "$env_file"

  # Append key
  echo "${key}=${value}" >> "$env_file"
}

# Check if the directory exists
if [ ! -d "$DATA_DIR" ]; then
  echo "Directory $DATA_DIR does not exist. Creating it..."
  mkdir -p "$DATA_DIR"
  FIRST_TIME_SETUP=true
else
  FIRST_TIME_SETUP=false
fi

# Run the InfluxDB container if it's not already running
if [ ! "$(docker ps -q -f name=influxdb)" ]; then
  echo "InfluxDB container not running. Starting container..."
  docker run -d \
    --name=influxdb \
    --restart unless-stopped \
    -p 8086:8086 \
    -v "$(pwd)/influxdb_data:/var/lib/influxdb2" \
    influxdb:latest
else
  echo "InfluxDB container is already running."
fi

# Perform first-time setup only if directory does not exist or container is not set up
if [ "$FIRST_TIME_SETUP" = true ]; then
  echo "First-time setup: Enter username and password for InfluxDB..."

  # Prompt for username and password for InfluxDB setup
  read -p "Enter InfluxDB username: " USERNAME
  read -sp "Enter InfluxDB password: " PASSWORD
  echo

  # Setup InfluxDB with provided username, password, organization, and bucket
  docker exec influxdb influx setup \
    --username "$USERNAME" \
    --password "$PASSWORD" \
    --org "$INFLUXDB_ORG" \
    --bucket "$INFLUXDB_BUCKET" \
    --force

  # Retrieve the InfluxDB token
  INFLUXDB_TOKEN=$(docker exec influxdb bash -c "influx auth ls --json" | jq -r '.[0].token')

  # Ensure .env exists
  touch .env

  # Overwrite or append only InfluxDB-related variables
  set_env_var "INFLUXDB_TOKEN" "$INFLUXDB_TOKEN"
  set_env_var "INFLUXDB_URL" "$INFLUXDB_URL"
  set_env_var "INFLUXDB_BUCKET" "$INFLUXDB_BUCKET"
  set_env_var "INFLUXDB_ORG" "$INFLUXDB_ORG"

  echo "InfluxDB setup complete. .env updated."
else
  echo "Skipping setup as the directory already exists."
fi

echo "InfluxDB container is now running with data persisted to $DATA_DIR."
