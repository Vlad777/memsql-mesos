var React = require('react');
var RB = require('react-bootstrap');

var ClusterList = require('components/cluster_list');
var CreateClusterModal = require('components/create_cluster_modal');

var StatusStore = require('stores/status');

var App = React.createClass({
    mixins: [ StatusStore.change_mixin("status_change") ],

    getInitialState: () => ({ show_create_cluster: false, server_connected: true }),

    status_change: function() {
        this.setState({
            server_connected: StatusStore.alive
        });
    },

    render: function() {
        var modal;
        if (this.state.show_create_cluster) {
            modal = <CreateClusterModal onClose={ this.hide_create_cluster } />;
        }

        var alert;
        if (!this.state.server_connected) {
            alert = (
                <RB.Alert bsStyle="warning">
                    <strong>Disconnected from server.</strong> Trying to reconnect...
                </RB.Alert>
            );
        }

        return (
            <div className="app">
                <RB.Navbar brand="MemSQL on Mesosphere" staticTop inverse>
                    <div className="navbar-right">
                        <RB.Button onClick={ this.show_create_cluster } className="navbar-btn" bsSize="small" bsStyle="success">
                            Create Cluster
                        </RB.Button>
                    </div>
                </RB.Navbar>
                <div className="container">
                    { alert }
                    <ClusterList />
                </div>
                { modal }
            </div>
        );
    },

    show_create_cluster: function() {
        this.setState({ show_create_cluster: true });
    },

    hide_create_cluster: function() {
        this.setState({ show_create_cluster: false });
    }
});

module.exports = App;
