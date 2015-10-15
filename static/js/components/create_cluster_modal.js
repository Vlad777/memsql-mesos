var React = require('react');
var RB = require('react-bootstrap');
var I = require('immutable');
var _ = require('lodash');
var $ = require('jquery');

var ClusterInterface = require("interfaces/cluster");
var ClusterFormStore = require("stores/cluster_form");

var CreateClusterModal = React.createClass({
    mixins: [ ClusterFormStore.change_mixin("form_changed") ],

    getInitialState: () => ({ fields: I.List() }),

    form_changed: function() {
        if (ClusterFormStore.saved) {
            window.setTimeout(() => ClusterInterface.cluster_form_reset(), 0);
            this.props.onClose();
        } else {
            this.setState({ fields: ClusterFormStore.fields });
        }
    },

    componentDidMount: function() {
        if (this.state.fields.size) {
            var first_field = this.state.fields.first();
            $(this.refs["field_" + first_field.id].getDOMNode()).find("input").focus();
        }
    },

    render: function() {
        var tab_index = 0;
        var next_tab_index = () => ++tab_index + "";

        var fields = this.state.fields
            .filter(f => f.active)
            .map(f => this.render_field(next_tab_index, f))
            .toArray();

        return (
            <RB.Modal title="Create MemSQL Cluster" bsStyle="primary" onRequestHide={ this.cancel }>
                <div className="modal-body">
                    <form onSubmit={ this.create }>
                        { fields }
                        <input type="submit" style={{ display: "none" }} />
                    </form>
                </div>
                <div className="modal-footer">
                    <RB.Button tabIndex="-1" onClick={ this.cancel }>Cancel</RB.Button>
                    <RB.Button tabIndex={ next_tab_index() } bsStyle="primary" onClick={ this.create }>Create Cluster</RB.Button>
                </div>
            </RB.Modal>
        );
    },

    render_field: function(next_tab_index, field) {
        var children;
        if (field.type === "select") {
            children = field.choices.map(choice => {
                return (
                    <option key={ choice[0] } value={ choice[0] }>
                        { choice[1] }
                    </option>
                );
            }).toArray();
        }

        var change_field = evt => {
            var value = field.type === "checkbox" ? evt.target.checked : evt.target.value;
            ClusterInterface.cluster_form_change(field.id, value);
        };

        return (
            <RB.Input
                type={ field.type }
                key={ field.id }
                ref={ "field_" + field.id }
                tabIndex={ next_tab_index() }
                bsStyle={ field.has_error ? "error": undefined }
                hasFeedback={ field.has_error }
                help={ field.error }
                label={ field.label }
                value={ field.value }
                checked={ field.value }
                onChange={ change_field } >
                { children }
            </RB.Input>
        );
    },

    cancel: function() {
        this.props.onClose();
    },

    create: function(evt) {
        ClusterInterface.create_cluster(ClusterFormStore.serialize());
        if (evt) { evt.preventDefault(); }
    }
});

module.exports = CreateClusterModal;
