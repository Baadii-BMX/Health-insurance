#!/bin/bash

# Replace with your GitHub username and repo
GITHUB_USER="Baadii-BMX"
REPO="Health-insurance"

# You'll need to create a Personal Access Token on GitHub
# and use it instead of a password when prompted

# For each file
while read -r file; do
  # Create necessary directories
  dir=$(dirname "$file")
  curl -X PUT \
    -H "Authorization: token YOUR_GITHUB_TOKEN" \
    -d "{\"message\": \"Add $file\", \"content\": \"$(base64 -w 0 "$file")\"}" \
    "https://api.github.com/repos/$GITHUB_USER/$REPO/contents/$file"
  echo "Uploaded $file"
  sleep 1
done < filelist.txt
