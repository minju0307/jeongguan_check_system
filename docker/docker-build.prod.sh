export ENVIRONMENT=prod

cp ../requirements.txt .

docker compose -f docker-compose.yml build
