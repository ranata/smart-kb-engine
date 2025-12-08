#!/bin/bash

set -e  # Exit immediately if any command fails

# ✅ Validate input argument
if [ -z "$1" ]; then
  echo "❌ ERROR: Please provide the zip file name."
  echo "✅ Usage: ./deploy_rag_backend.sh 04122025.zip"
  exit 1
fi

ZIP_FILE="$1"
ZIP_NAME=$(basename "$ZIP_FILE" .zip)

echo "📁 Moving to /python_srv..."
cd /python_srv

echo "📦 Unzipping $ZIP_FILE..."
unzip "/home/scbadmin/$ZIP_FILE"

echo "🚚 Moving ragBackend..."
mv "./$ZIP_NAME/ragBackend" .

echo "🔐 Moving ssl_key..."
mv "./$ZIP_NAME/ssl_key" .

echo "🗑️ Removing temporary folder..."
rmdir "$ZIP_NAME"

echo "📂 Moving into ragBackend..."
cd /python_srv/ragBackend

echo "🚀 Starting Python service with nohup..."
nohup /usr/bin/python3.12 IA_LLM_service_App.py > output.log 2>&1 &

echo "✅ Deployment completed successfully!"
echo "📄 Logs: /python_srv/ragBackend/output.log"
