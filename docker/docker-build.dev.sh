export ENVIRONMENT=dev

COMPOSE_PROJECT_NAME=dev-xai-law

cp ../requirements.txt .

docker compose -p $COMPOSE_PROJECT_NAME -f docker-compose.yml build
