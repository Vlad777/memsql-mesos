build:
	docker build -f mesos -t psy3.memcompute.com/mesos .
	docker build -f mesos-master -t psy3.memcompute.com/mesos-master .
	docker build -f mesos-slave -t psy3.memcompute.com/mesos-slave .

push:
	docker push psy3.memcompute.com/mesos-master
	docker push psy3.memcompute.com/mesos-slave
