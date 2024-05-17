export ENVIRONMENT=dev

COMPOSE_PROJECT_NAME=dev-xai-law

docker compose -p $COMPOSE_PROJECT_NAME up -d
