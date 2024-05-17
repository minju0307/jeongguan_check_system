export ENVIRONMENT=prod

COMPOSE_PROJECT_NAME=prod-xai-law

docker compose -p $COMPOSE_PROJECT_NAME down
