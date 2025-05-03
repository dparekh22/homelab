#!/bin/bash
set -eo pipefail

# Fetch all parameters at once
PARAMS=$(aws ssm get-parameters-by-path \
  --path "/cloud-bot" \
  --with-decryption \
  --query "Parameters[*].{Name:Name,Value:Value}")

# Extract individual values
export DISCORD_TOKEN=$(echo "$PARAMS" | jq -r '.[] | select(.Name | contains("DISCORD_TOKEN")) | .Value')
export API_BASE_URL=$(echo "$PARAMS" | jq -r '.[] | select(.Name | contains("API_BASE_URL")) | .Value')
export TARGET_MESSAGE_ID=$(echo "$PARAMS" | jq -r '.[] | select(.Name | contains("TARGET_MESSAGE_ID")) | .Value')
export ROLE_ID=$(echo "$PARAMS" | jq -r '.[] | select(.Name | contains("ROLE_ID")) | .Value')
export DB_HOST=$(echo "$PARAMS" | jq -r '.[] | select(.Name | contains("DB_HOST")) | .Value')
export DB_USER=$(echo "$PARAMS" | jq -r '.[] | select(.Name | contains("DB_USER")) | .Value')
export DB_PASSWORD=$(echo "$PARAMS" | jq -r '.[] | select(.Name | contains("DB_PASSWORD")) | .Value')

# Create secret files
echo "$DB_USER" > db_user.txt
echo "$DB_PASSWORD" > db_password.txt
chmod 600 db_*.txt

# Deploy
docker-compose down
docker-compose up -d --build

# Cleanup (optional)
sleep 30
shred -u db_*.txt
