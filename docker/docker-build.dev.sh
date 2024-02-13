export ENVIRONMENT=dev

cp ../requirements.txt .

docker compose -f docker-compose.yml build
