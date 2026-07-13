#!/usr/bin/env sh 
set -eu 
## Purpose : To check for failed HTTP responses and show useful error output 

API_BASE_URL = "${API_BASE_URL:-http://api:8000}

curl -fsS "${API_BASE_URL}/health"
curl -fsS "${API_BASE_URL}/ready"
curl -fsS "${API_BASE_URL}/api/v1/lines/current-status"

