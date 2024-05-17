export ENVIRONMENT=prod

COMPOSE_PROJECT_NAME=prod-xai-law

cp ../requirements.txt .

docker compose -f docker-compose.yml build
