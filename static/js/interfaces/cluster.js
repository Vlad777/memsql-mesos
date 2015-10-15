var BaseInterface = require("interfaces/base");
var Api = require("remote/api");

var POLL_INTERVAL = 5000;

class ClusterInterface extends BaseInterface {
    constructor() {
        this.define_messages({
            CLUSTERS: null,
            CLUSTER_FORM_CHANGE: null,
            CLUSTER_FORM_RESET: null,
            CLUSTER_CREATE: null,
            CLUSTER_CREATE_SUCCESS: null,
            CLUSTER_CREATE_ERROR: null
        });
    }

    get_clusters() {
        return Api.call("cluster/list", {})
            .then(
                data => this.dispatch(this.messages.CLUSTERS, data),
                err => console.error(err)
            );
    }

    start_poller() {
        var poll = () => {
            this.get_clusters()
                .then(() => window.setTimeout(poll, POLL_INTERVAL));
        };

        poll();
    }

    create_cluster(params) {
        this.dispatch(this.messages.CLUSTER_CREATE);

        var promise = Api.call("cluster/create", params)
        .then(
            message => {
                this.dispatch(this.messages.CLUSTER_CREATE_SUCCESS);
                this.get_clusters();
            },
            error => this.dispatch(this.messages.CLUSTER_CREATE_ERROR, error)
        );
    }

    remove_cluster(cluster_id) {
        var promise = Api.call("cluster/delete", { cluster_id });
        promise.then(() => this.get_clusters());
    }

    cluster_form_reset() {
        this.dispatch(this.messages.CLUSTER_FORM_RESET);
    }

    cluster_form_change(field_id, value) {
        this.dispatch(this.messages.CLUSTER_FORM_CHANGE, { field_id, value });
    }
}

module.exports = new ClusterInterface();
