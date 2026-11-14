#!/bin/bash

# The URL to check
URL="http://localhost:8000/health"

# Use curl to hit the endpoint. 
# -s (silent) hides the progress bar.
# -f (fail) returns an error code if the HTTP status is 400 or higher.
# -o /dev/null throws away the actual JSON response (we just want the status code).
curl -s -f -o /dev/null "$URL"

# Check the exit code of the curl command
# $? gets the exit code of the last command. 0 means success.
if [ $? -eq 0 ]; then
    echo "✅ Healthcheck Passed: API is UP."
    exit 0
else
    echo "❌ Healthcheck Failed: API is DOWN."
    exit 1
fi