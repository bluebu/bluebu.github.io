.PHONY: serve stop clean

serve:
	docker compose up

serve_bg:
	docker compose up -d

stop:
	docker compose down

clean:
	docker compose down -v
