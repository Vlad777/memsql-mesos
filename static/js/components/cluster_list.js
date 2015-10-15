var React = require('react');
var RB = require('react-bootstrap');
var I = require('immutable');

var Cluster = require("components/cluster");

var ClusterInterface = require("interfaces/cluster");
var ClusterStore = require("stores/cluster");

var ClusterList = React.createClass({
    mixins: [ ClusterStore.change_mixin("cluster_change") ],

    getInitialState: () => ({ clusters: I.List() }),

    cluster_change: function() {
        this.setState({
            clusters: ClusterStore.records
        });
    },

    render: function() {
        var clusters = this.state.clusters
            .map(c => <Cluster key={ c.cluster_id } cluster={ c } onDelete={ this.remove_cluster } />)
            .toArray();

        if (!clusters.length) {
            clusters = (
                <RB.Alert>
                    <strong>No MemSQL Clusters.</strong>
                </RB.Alert>
            );
        }

        return (
            <div className="cluster_list">
                { clusters }
            </div>
        );
    },

    remove_cluster: function(cluster) {
        ClusterInterface.remove_cluster(cluster.cluster_id);
    }
});

module.exports = ClusterList;
