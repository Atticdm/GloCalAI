#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-http://localhost:8080}
VIDEO_PATH=${1:-assets/source.mp4}
EMAIL=${EMAIL:-admin@glocal.ai}
PASSWORD=${PASSWORD:-admin12345}
S3_PUBLIC=${S3_PUBLIC_URL:-http://localhost:9000}

if [ ! -f "$VIDEO_PATH" ]; then
  echo "Video file $VIDEO_PATH not found. Run scripts/dev/generate-test-video.sh first." >&2
  exit 1
fi

echo "Authenticating..."
TOKEN=$(curl -s "$API_URL/auth/sign-in" -H "Content-Type: application/json" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

AUTH_HEADER="Authorization: Bearer $TOKEN"

echo "Creating smoke test project..."
PROJECT_ID=$(curl -s "$API_URL/projects" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{"name":"Smoke Test"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

echo "Requesting upload URL..."
UPLOAD_RESPONSE=$(curl -s "$API_URL/assets/upload-url" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d "{\"projectId\":\"$PROJECT_ID\",\"type\":\"video\",\"filename\":\"$(basename "$VIDEO_PATH")\",\"mime\":\"video/mp4\"}")
ASSET_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c 'import sys,json; print(json.load(sys.stdin)["asset_id"])')
UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | python3 -c 'import sys,json; print(json.load(sys.stdin)["upload_url"])')
OBJECT_KEY=$(echo "$UPLOAD_RESPONSE" | python3 -c 'import sys,json; print(json.load(sys.stdin)["object_key"])')

echo "Uploading video to MinIO..."
curl -s -X PUT "$UPLOAD_URL" -H "Content-Type: video/mp4" --data-binary "@$VIDEO_PATH" > /dev/null

echo "Completing asset registration..."
S3_URL="$S3_PUBLIC/glocal-media/$OBJECT_KEY"
ASSET_RESPONSE=$(curl -s "$API_URL/assets/complete" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d "{\"projectId\":\"$PROJECT_ID\",\"type\":\"video\",\"s3_url\":\"$S3_URL\",\"meta\":{\"source\":\"smoke\"}}")
SOURCE_ASSET_ID=$(echo "$ASSET_RESPONSE" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

echo "Starting localization job..."
JOB_RESPONSE=$(curl -s "$API_URL/jobs" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d "{\"projectId\":\"$PROJECT_ID\",\"sourceAssetId\":\"$SOURCE_ASSET_ID\",\"languages\":[\"es\",\"pt-BR\"],\"voiceProfileId\":null,\"options\":{\"subs\":true,\"dub\":true,\"replace_text_in_frame\":true,\"upload_to_youtube\":false}}")
JOB_ID=$(echo "$JOB_RESPONSE" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

echo "Waiting for job $JOB_ID to finish..."
STATUS=""
while true; do
  STATUS=$(curl -s "$API_URL/jobs/$JOB_ID" -H "$AUTH_HEADER" | python3 -c 'import sys,json; data=json.load(sys.stdin); print(data["status"])')
  echo "Current status: $STATUS"
  if [ "$STATUS" = "done" ] || [ "$STATUS" = "error" ] || [ "$STATUS" = "partial" ]; then
    break
  fi
  sleep 10
done

echo "Fetching variant download links..."
VARIANTS_JSON=$(curl -s "$API_URL/jobs/$JOB_ID" -H "$AUTH_HEADER")
export TOKEN
export VARIANTS_JSON
python3 - <<'PY'
import json
import os
import urllib.request

API = os.environ.get("API_URL", "http://localhost:8080")
TOKEN = os.environ.get("TOKEN")
data = json.loads(os.environ["VARIANTS_JSON"])

def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

for variant in data["variants"]:
    links = fetch_json(f"{API}/variants/{variant['id']}/download")
    print(f"Variant {variant['lang']} -> MP4: {links.get('mp4')} SRT: {links.get('srt')}")
PY

echo "Smoke test complete"
