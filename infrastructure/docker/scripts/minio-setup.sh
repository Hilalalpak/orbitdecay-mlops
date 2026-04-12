#!/bin/bash
# MinIO state_bucket initialization script
# Author: Hilal Alpak
# Version: 1.0.1 (Fixed checkpoint_handler issue)

set -e

echo "Waiting for MinIO to be ready..."
sleep 10

echo "Setting MinIO alias..."
mc alias set minio http://minio:9000 "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY"

echo "Creating buckets (ignoring if exist)..."
mc mb minio/pipeline-cache || true
mc mb minio/pipeline-state || true
mc mb minio/api-compliance || true
mc mb minio/orbit-data || true
mc mb minio/environment-data || true
mc mb minio/training-store || true
mc mb minio/"$S3_MLFLOW_BUCKET" || true

echo "Setting bucket policies..."
mc policy set public minio/pipeline-cache || true

# --- DÜZELTİLEN KISIM BAŞLANGICI ---

METADATA_FILE="minio/pipeline-state/run-history/pipeline_runs.json"
COMPLIANCE_FILE="minio/api-compliance/setup_info.json"

# 1. Metadata Dosyası Kontrolü
if mc ls "$METADATA_FILE" > /dev/null 2>&1; then
    echo "✅ Metadata file already exists. SKIPPING overwrite to preserve history."
else
    echo "⚠️ Metadata file not found. Creating initial metadata..."
    cat > /tmp/initial_metadata.json << EOF
{
  "version": "1.0",
  "created": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "filter_history": [],
  "system_info": {
    "storage_backend": "minio",
    "bucket_structure": "smart_systems_v1",
    "setup_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "setup_script_version": "1.0"
  }
}
EOF
    mc cp /tmp/initial_metadata.json "$METADATA_FILE"
fi

# 2. Compliance Dosyası Kontrolü
if mc ls "$COMPLIANCE_FILE" > /dev/null 2>&1; then
    echo "✅ Compliance file already exists. SKIPPING overwrite to preserve API limits."
else
    echo "⚠️ Compliance file not found. Creating initial compliance data..."
    cat > /tmp/initial_compliance.json << EOF
{
  "version": "1.0",
  "created": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "compliance_setup": true,
  "daily_limits": {
    "max_requests": 200,
    "current_date": "$(date -u +"%Y-%m-%d")",
    "requests_today": 0
  },
  "setup_info": {
    "setup_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "setup_script_version": "1.0"
  }
}
EOF
    mc cp /tmp/initial_compliance.json "$COMPLIANCE_FILE"
fi

# --- DÜZELTİLEN KISIM BİTİŞİ ---

echo "MinIO setup completed successfully"
exit 0