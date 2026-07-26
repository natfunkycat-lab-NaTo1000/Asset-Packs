VERSION := 0.0.0

# If the first argument is "repack"...
ifeq (repack,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "repack"
  REPACK_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(REPACK_ARGS):;@:)
endif

.PHONY: repack
repack: venv requirements
	./.venv/bin/python3 .utils/repack.py $(REPACK_ARGS)

# If the first argument is "check"...
ifeq (check,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "check"
  CHECK_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(CHECK_ARGS):;@:)
endif

.PHONY: check
check: venv requirements
	./.venv/bin/python3 .utils/check.py $(CHECK_ARGS)

# If the first argument is "previews"...
ifeq (previews,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "previews"
  PREVIEWS_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(PREVIEWS_ARGS):;@:)
endif

.PHONY: previews
previews: venv requirements
	./.venv/bin/python3 .utils/previews.py $(PREVIEWS_ARGS)

venv:
	python3 -m venv .venv

.PHONY: requirements
requirements: venv
	./.venv/bin/pip install -q -r requirements.txt

.PHONY: clean
clean:
	rm -rf .venv

.PHONY: lint
lint: venv requirements
	./.venv/bin/black .utils --check

.PHONY: format
format: venv requirements
	./.venv/bin/black .utils

GITHUB_REPOSITORY ?= natfunkycat-lab-NaTo1000/Asset-Packs
DOCKER_IMAGE := ghcr.io/$(shell echo $(GITHUB_REPOSITORY) | tr '[:upper:]' '[:lower:]')
DOCKER_TAG := $(VERSION)

.PHONY: docker-build
docker-build:
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) -t $(DOCKER_IMAGE):latest .

.PHONY: docker-push
docker-push: docker-build
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_IMAGE):latest
