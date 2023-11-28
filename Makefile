sync-new-env:
	@while IFS='=' read -r key value; do \
		if [ -n "$$key" ]; then \
			if ! grep -q "^$$key=" .env; then \
				echo "$$key=$$value" >> .env; \
			fi; \
		fi; \
	done < .env-copy

alembic-autogenerate:
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

alembic-upgrade:
	alembic upgrade head

init:
	@make sync-new-env
	@poetry install
	@poetry shell
	@docker-compose build
	@docker-compose up -d
	@sleep 5
	@make alembic-upgrade
	@docker-compose exec minio sh -c "mc mb minio/$$(grep S3_BUCKET .env | cut -d '=' -f2)"
	@docker-compose down
	@pre-commit install
