.PHONY: serve stop clean pdf

serve:
	docker compose up

serve_bg:
	docker compose up -d

stop:
	docker compose down

clean:
	docker compose down -v

pdf:
	python3 scripts/build-pdf.py
	open dist/agent-harness.html
