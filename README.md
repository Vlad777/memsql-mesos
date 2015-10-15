MemSQL Mesos Framework
===========================

This is a framework for the Apache Mesos system that allows users to install and manage multiple MemSQL clusters on a Mesos cluster.  It contains both a Mesos scheduler and a Mesos executor; the Mesos scheduler runs a web UI which can spin up, monitor, and delete MemSQL clusters on demand.  The executor runs on Mesos slaves and starts up a MemSQL instance. This framework is fault-tolerant and can transparently recover from the loss of any Mesos slave at any time.

# Running
The easiest way to run this framework is with Marathon; there is a `marathon.json` file available in the root directory of this repository.

This framework is also available from Mesosphere's DCOS repository; if you have DCOS's command-line tool installed, simply run `dcos package install memsql` in order to start using this framework.

# Building
Both the scheduler and the executor are built as Docker containers. Simply run `make build-scheduler` and `make build-executor` to build them.
