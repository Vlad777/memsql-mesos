This code comes with a small script that runs the scheduler for a long period
of time and checks the number of file descriptors and TCP sockets that it
opens.  To run this test, one simply needs Docker, a running Mesos master, and
a running Zookeeper instance:

1. Set up some environment variables:

        MESOS_MASTER_URL=mesos_master_url.com:5050
        ZOOKEEPER_URL=zookeeper_url.com:2181

2. From the root directory of this repository, run:

        make build-scheduler

3. Run the resiliency test:

        make resiliency-test

By default, the test will run for an hour, although you can cancel it before
then with ctrl-C.  The output should look something like:

        MemSQL Mesos framework resiliency test ran for 3725 seconds
        We initially had:
        7 open file descriptors
        19 open TCP sockets
        We finished with:
        36 open file descriptors
        31 open TCP sockets
