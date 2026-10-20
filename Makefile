.PHONY: up down logs test test-backend test-frontend lint

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f backend

test: test-backend test-frontend

test-backend:
	$(MAKE) -C backend test

test-frontend:
	cd frontend && npm test

lint:
	$(MAKE) -C backend lint
	cd frontend && npm run lint
