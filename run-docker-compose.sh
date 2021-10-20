#!/bin/bash
# NOTE: Host port NEEDS to be 81, as setup with nginx + certbot for forwarding to

ENV_FILE=docker-compose.env
COMPOSE_FILE=docker-compose.yml

# Run  (add --build flag at end to build before activating, -v to remove persisting volumes, i.e. database data)
docker-compose \
    --env-file $ENV_FILE \
    -f $COMPOSE_FILE down \
        --remove-orphans && \
docker-compose \
    --env-file $ENV_FILE \
    -f $COMPOSE_FILE up --build

