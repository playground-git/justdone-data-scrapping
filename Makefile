.PHONY: db-up db-down db-shell

db-up:
	docker-compose up -d

db-down:
	docker-compose down

db-shell:
	docker exec -it research_papers_db psql -U postgres -d research_papers
