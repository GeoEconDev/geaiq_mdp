SHELL := /usr/bin/bash
.PHONY: sync-from-develop sync-develop sync clean clean-cache clean-reports clean-logs show-status upload-statics


sync : sync-from-develop sync-develop sync-from-develop


sync-from-develop :
	@bash -c 'for b in cr jp jm vs na fc; do git switch $$b && git pull && git merge origin/develop && git push; done'


sync-develop :
	@bash -c 'git switch develop; git pull; for b in cr jp jm vs na fc; do git merge origin/$$b; done; git push'


clean-cache:
	rm -r ~/.geoecon-cache


clean-reports:
	rm report.*


clean-logs:
	rm -r ~/.geoecon-logs


clean-all: clean-cache clean-reports clean-logs


show-status:
	grep -r "status:" metadata/


upload-statics:
	gsutil -m cp -r src/geaiq_mdp/statics/* gs://geoecon-dev-static/


ifdef file
file_normalized := $(subst \,/,$(file))
COMMIT_HASH := $(shell git rev-parse HEAD)
FILE_BASENAME := $(shell bash -c "basename $(file) | cut -d '.' -f 1")
RELATIVE_FILE := $(file)
endif


solve_vars:
	@bash -c 'if [[ "$(file_normalized)" =~ ^metadata(/[^/]+)?/[^/]+\.ya?ml$$ ]]; then \
		echo "✅ Archivo válido: $(file)"; \
	else \
		echo "💥 Error: file debe estar en el directorio 'metadata' y ser un archivo YAML."; \
		echo "--- $(file) : $(file_normalized) ---"; \
		exit 1; \
	fi'
 

check-vars: solve_vars
	@echo Commit hash: $(COMMIT_HASH)
	@echo Base name: $(FILE_BASENAME)
	@echo Relative file: $(RELATIVE_FILE)


check-metadata: solve_vars
	gcloud run jobs execute metadata \
		--region=us-central1 --project=geoecon-dev \
		--args="--commit,$(COMMIT_HASH),check,--format,html,--output,report.$(FILE_BASENAME).check.dev.html,$(RELATIVE_FILE)"


deploy-metadata: solve_vars
	gcloud run jobs execute metadata \
		--region=us-central1 --project=geoecon-dev \
		--args="--commit,$(COMMIT_HASH),deploy,--format,html,--output,report.$(FILE_BASENAME).deploy.dev.html,$(RELATIVE_FILE)"

reset-metadata: solve_vars
	gcloud run jobs execute metadata \
		--region=us-central1 --project=geoecon-dev \
		--args="--commit,$(COMMIT_HASH),reset,$(RELATIVE_FILE)"

metadata-task-describe:
	gcloud run jobs describe metadata --region=us-central1 --project=geoecon-dev

metadata-task-running:
	gcloud run jobs executions list --job metadata --region=us-central1 --project=geoecon-dev --limit 10