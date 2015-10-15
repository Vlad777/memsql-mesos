SHELL := /bin/bash
SCHEDULER_IMAGE := memsql/mesos-scheduler
EXECUTOR_IMAGE := memsql/mesos-executor
UI_IMAGE := psy3.memcompute.com/mesos-memsql-ui:latest

ifeq ($(strip $(shell uname)), Linux)
    IP_ADDRESS := $(shell ip a show dev eth0 | grep 'inet ' | awk '{ print $$2 }' | cut -d'/' -f1)
else
    IP_ADDRESS := $(shell boot2docker ssh "ip a show dev eth2 | grep 'inet ' | awk '{ print \$$2 }' | cut -d'/' -f1")
endif

##############################
# env
#
.git/hooks/pre-commit: .pre-commit
	@cp .pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit

.PHONY: git-commit-template
git-commit-template: .commit_template
	@git config commit.template .commit_template

.PHONY: lint
lint:
	source ./activate && flake8 --config=.flake8 memsql_framework

.PHONY: deps
deps: .git/hooks/pre-commit git-commit-template node-modules venv

.PHONY: venv
venv: venv/bin/activate
venv/bin/activate: requirements.txt
	test -d venv || virtualenv venv
	. venv/bin/activate; pip install -r requirements.txt
	touch venv/bin/activate

##############################
# version
#
MEMSQL_MESOS_FRAMEWORK_VERSION := $(shell python -c "import memsql_framework; print memsql_framework.__version__")
export MEMSQL_MESOS_FRAMEWORK_VERSION

.PHONY: version
version:
	@echo $(MEMSQL_MESOS_FRAMEWORK_VERSION)

##############################
# scheduler
#
.PHONY: build-scheduler
build-scheduler:
	docker build -f Dockerfile-scheduler -t $(SCHEDULER_IMAGE):$(MEMSQL_MESOS_FRAMEWORK_VERSION) .
	docker tag -f $(SCHEDULER_IMAGE):$(MEMSQL_MESOS_FRAMEWORK_VERSION) $(SCHEDULER_IMAGE):latest

.PHONY: run-scheduler
run-scheduler:
	docker run --net=host --env "LIBPROCESS_IP=$(IP_ADDRESS)" -it -v $(shell pwd):/dev-framework $(SCHEDULER_IMAGE) /dev-framework/bin/scheduler

.PHONY: push-scheduler
push-scheduler:
	docker push $(SCHEDULER_IMAGE):$(MEMSQL_MESOS_FRAMEWORK_VERSION)
	docker push $(SCHEDULER_IMAGE):latest

.PHONY: console
console:
	docker run --net=host --env "LIBPROCESS_IP=$(IP_ADDRESS)" -it -v $(shell pwd):/dev-framework $(SCHEDULER_IMAGE) /dev-framework/bin/console

.PHONY: resiliency-test
resiliency-test:
	docker run --net=host --env "LIBPROCESS_IP=$(IP_ADDRESS)" --env "MESOS_MASTER_URL=$(MESOS_MASTER_URL)" --env "ZOOKEEPER_URL=$(ZOOKEEPER_URL)" -it $(SCHEDULER_IMAGE) /memsql_framework/resiliency_test.service

##############################
# executor
#
build-executor:
	docker build -f Dockerfile-executor -t $(EXECUTOR_IMAGE):$(MEMSQL_MESOS_FRAMEWORK_VERSION) .
	docker tag -f $(EXECUTOR_IMAGE):$(MEMSQL_MESOS_FRAMEWORK_VERSION) $(EXECUTOR_IMAGE):latest

push-executor:
	docker push $(EXECUTOR_IMAGE):$(MEMSQL_MESOS_FRAMEWORK_VERSION)
	docker push $(EXECUTOR_IMAGE):latest

prod-executor:
	docker run -p 9000:9000 -p 3306:3306 -d $(EXECUTOR_IMAGE)

dev-executor:
	docker run -it -v $(shell pwd):/dev_executor $(EXECUTOR_IMAGE) /bin/bash

dev-executor-web:
	open http://$(IP_ADDRESS):9000


##############################
# web stuff
#
.PHONY: run-ui-only
run-ui-only:
	docker run --net=host -it -v $(shell pwd):/dev-framework $(SCHEDULER_IMAGE) /dev-framework/bin/scheduler --ui-only

.PHONY: node-modules
node-modules:
	npm install

.PHONY: watch-ui
watch-ui:
	@source activate && gulp watch

.PHONY: open-ui
open-ui:
	open http://$(IP_ADDRESS):9000
