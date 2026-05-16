# CIPHER Local POC — Makefile
# WBS Task: T-001 | Layer: DRS

.PHONY: up down status logs lint test poc-demo clean

# ─── Infrastructure ───────────────────────────────────────────────────────────

up:
	docker compose --env-file .env up -d --wait

down:
	docker compose down

status:
	docker compose ps

logs:
	docker compose logs -f --tail=50

health:
	@echo "=== Redis ===" && docker exec cipher-redis redis-cli ping
	@echo "=== Qdrant ===" && curl -sf http://localhost:6333/healthz && echo " OK"
	@echo "=== NATS ===" && curl -sf http://localhost:8222/healthz && echo " OK"
	@echo "=== OPA ===" && curl -sf http://localhost:8181/health && echo " OK"
	@echo "=== MinIO ===" && curl -sf http://localhost:9000/minio/health/live && echo " OK"
	@echo "=== Langfuse ===" && curl -sf http://localhost:3000/api/public/health && echo " OK"

# ─── Development ──────────────────────────────────────────────────────────────

lint:
	cd ../.. && ruff check . && pyright .

test:
	cd ../.. && pytest tests/ -v --tb=short

test-unit:
	cd ../.. && pytest tests/unit/ -v --tb=short

test-integration:
	cd ../.. && pytest tests/integration/ -v --tb=short

test-e2e:
	cd ../.. && pytest tests/e2e/ -v --tb=short

# ─── POC Demo ─────────────────────────────────────────────────────────────────

poc-demo:
	cd ../.. && pytest tests/e2e/test_poc_spine.py -v --tb=long

# ─── Cleanup ──────────────────────────────────────────────────────────────────

clean:
	docker compose down -v
	rm -rf ./data
