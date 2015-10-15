var React = require('react');
var RB = require('react-bootstrap');

var FlavorStore = require("stores/flavor");

var Cluster = React.createClass({
    mixins: [ FlavorStore.change_mixin("flavor_change") ],

    flavor_change: function() { this.forceUpdate(); },

    render: function() {
        var cluster = this.props.cluster;

        var deleting = cluster.status === "DELETING";
        var creating = cluster.status === "CREATING";
        var waiting_agents = cluster.status === "WAITING_FOR_AGENTS";
        var waiting_memsql = cluster.status === "WAITING_FOR_MEMSQL";
        var running = cluster.status === "RUNNING";

        var progress;
        if (cluster.progress) {
            var percent = Math.min(80, cluster.progress.current / (cluster.progress.total || 1) * 100);
            var style = deleting ? "danger" : "success";
            var label = "Initializing containers";
            if (deleting) {
                label = "Deleting";
            } else if (running) {
                label = "Active";
                percent = 100;
            } else if (waiting_agents) {
                label = "Waiting for containers";
                percent = 80;
            } else if (waiting_memsql) {
                label = "Deploying MemSQL Cluster";
                percent = 90;
            }

            progress = (
                <div className="progress-wrap">
                    { running ? "" : label }
                    <RB.ProgressBar bsStyle={ style } active={ !running } now={ percent } label={ running ? label : "" } />
                </div>
            );
        }

        var flavor = FlavorStore.lookup(cluster.flavor);
        var size = cluster.flavor;
        if (flavor) {
            size = flavor.description;
        }

        return (
            <div className="panel-cluster panel panel-default">
                <div className="panel-heading clearfix">
                    <div className="header-buttons">
                        { progress }
                        <RB.Button disabled={ deleting } bsStyle="danger" bsSize="xsmall" onClick={ this.remove }>
                            Delete Cluster
                        </RB.Button>
                    </div>
                    <h3 className="panel-title">{ cluster.display_name }</h3>
                </div>
                <RB.Table striped bordered condensed>
                    <tbody>
                        <tr>
                            <td>Leaves</td>
                            <td>{ cluster.num_leaves }</td>
                            <td>Aggs</td>
                            <td>{ cluster.num_aggs }</td>
                        </tr>
                        <tr>
                            <td>Instance Size</td>
                            <td>{ size }</td>
                            <td>MemSQL</td>
                            <td>{ running ? cluster.memsql_uri : "loading..." }</td>
                        </tr>
                        <tr>
                            <td>MemSQL Ops</td>
                            <td>
                                { running
                                    ? <a href={ cluster.agent_uri }>{ cluster.agent_uri }</a>
                                    : "loading..." }
                            </td>
                            <td>MemSQL Demo</td>
                            <td>
                                { cluster.install_demo && running
                                    ? <a href={ cluster.demo_uri }>{ running ? cluster.demo_uri : "loading..." }</a>
                                    : cluster.install_demo ? "loading..." : "Disabled" }
                            </td>
                        </tr>
                    </tbody>
                </RB.Table>
            </div>
        );
    },

    remove: function() {
        this.props.onDelete(this.props.cluster);
    }
});

module.exports = Cluster;
