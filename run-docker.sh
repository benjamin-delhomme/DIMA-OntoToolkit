#!/bin/bash
set -e

IMAGE_NAME="dima-otk"

docker run --rm \
	--env-file .env \
    -v $(pwd)/output:/app/output \
    -v $(pwd)/articles:/app/articles \ 
    $IMAGE_NAME  "$@"

