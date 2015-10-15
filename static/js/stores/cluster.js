var I = require("immutable");
var Base = require("stores/base");
var _ = require("lodash");

var ClusterInterface = require("interfaces/cluster");

var ClusterAttributes = I.Record({
    cluster_id: undefined,
    display_name: undefined,
    num_leaves: undefined,
    num_aggs: undefined,
    high_availability: undefined,
    flavor: undefined,
    progress: undefined,
    status: undefined,
    install_demo: undefined,
    primary_host: undefined,
    primary_agent_port: undefined,
    primary_memsql_port: undefined,
    primary_demo_port: undefined
});

class Cluster extends ClusterAttributes {
    get agent_uri() {
        if (this.primary_host) {
            return "http://" + this.primary_host + ":" + this.primary_agent_port;
        }
    }

    get demo_uri() {
        if (this.primary_host) {
            return "http://" + this.primary_host + ":" + this.primary_demo_port;
        }
    }

    get memsql_uri() {
        if (this.primary_host) {
            return "mysql -u root -h " + this.primary_host + " -P" + this.primary_memsql_port;
        }
    }
}

class ClusterStore extends Base {
    constructor() {
        super();
        this.state = this.state.merge({
            records: I.List()
        });
    }

    get records() { return this.state.get("records"); }

    handle_message(msg) {
        switch(msg.message) {
            case ClusterInterface.messages.CLUSTERS:
                this.state = this.state.set(
                    "records",
                    I.Seq(msg.params).map(
                        cluster => new Cluster(cluster)
                    ).toList().sortBy(c => c.cluster_id)
                );
                break;
        }
    }
}

module.exports = new ClusterStore();
