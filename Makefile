DOCKER_REPO=radioastro/simms

.PHONY: build clean

all: run

build:
	docker build --pull -t ${DOCKER_REPO} .

run: build
	docker run -ti ${DOCKER_REPO}

clean:
	docker rmi ${DOCKER_REPO}
