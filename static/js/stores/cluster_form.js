var I = require("immutable");
var Base = require("stores/base");
var _ = require('lodash');

var FlavorInterface = require("interfaces/flavor");
var FlavorStore = require("stores/flavor");

var ClusterInterface = require("interfaces/cluster");

const EDITION_ENTERPRISE = "ENTERPRISE";
const EDITION_COMMUNITY = "COMMUNITY";

var FieldAttributes = I.Record({
    id: undefined,
    active: true,
    label: undefined,
    type: "text",
    value: undefined,
    error: undefined,
    choices: I.List(),
    validator: undefined
});

class FormField extends FieldAttributes {
    get has_error() {
        return !!this.error;
    }

    update_value(value) {
        var change = { error: undefined };
        if (this.validator) {
            try {
                value = this.validator(value);
            } catch (err) {
                change.error = err.toString();
            }
        }
        change.value = value;
        return this.merge(change);
    }
}

var validate_number = function(min) {
    return function(raw) {
        var num = parseInt(raw, 10);
        if (_.isNaN(num)) {
            throw new Error("Invalid field, must be a number");
        }
        if (num < min) {
            throw new Error("Invalid field, must be greater than " + min + ".");
        }
        return num;
    };
};

class ClusterFormStore extends Base {
    constructor() {
        super();
        this._set_defaults();
    }

    get loading() { return this.state.get("loading"); }
    get saved() { return this.state.get("saved"); }

    get fields() { return this.state.get("fields"); }

    _set_defaults() {
        var first_flavor = FlavorStore.records.first();

        this.state = this.state.merge({
            loading: false,
            saved: false,
            error: undefined,
            fields: I.List([
                new FormField({
                    id: "display_name",
                    label: "Cluster Name",
                    value: ""
                }),
                new FormField({
                    id: "num_aggs",
                    label: "Number of Child Aggregators (excluding the Master Aggregator)",
                    value: 2,
                    validator: validate_number(0)
                }),
                new FormField({
                    id: "num_leaves",
                    label: "Number of Leaf Nodes",
                    value: 2,
                    validator: validate_number(1)
                }),
                new FormField({
                    id: "flavor",
                    type: "select",
                    label: "MemSQL Node Size",
                    value: first_flavor ? first_flavor.flavor_id : undefined,
                    choices: FlavorStore.choices
                }),
                new FormField({
                    id: "install_demo",
                    type: "checkbox",
                    label: "Install MemSQL Demo",
                    value: true
                }),
                new FormField({
                    id: "edition",
                    type: "select",
                    label: "MemSQL Edition",
                    value: EDITION_COMMUNITY,
                    choices: I.List([
                        [ EDITION_COMMUNITY, "Community Edition" ],
                        [ EDITION_ENTERPRISE, "Enterprise Edition" ]
                    ])
                }),
                new FormField({
                    id: "license_key",
                    active: false,
                    label: "Enterprise License Key",
                    value: "",
                }),
                new FormField({
                    id: "high_availability",
                    active: false,
                    type: "checkbox",
                    label: "Enable High Availability",
                    value: false
                })
            ])
        });
    }

    id_to_index(field_id) {
        return this.fields.findIndex(f => f.id === field_id);
    }

    field_update(field_id, updater) {
        var idx = this.id_to_index(field_id);
        if (idx < 0) { throw new Error("Unknown field: " + field_id); }
        this.state = this.state.mergeIn(
            [ "fields", idx ],
            updater(this.fields.get(idx))
        );
    }

    field_set(field_id, key, value) {
        this.field_update(field_id, f => f.set(key, value));
    }

    change_field(field_id, value) {
        this.field_update(field_id, f => f.update_value(value));

        if (field_id === "edition") {
            var active = value === EDITION_ENTERPRISE;
            this.field_set("license_key", "active", active);
            this.field_set("high_availability", "active", active);
        }
    }

    update_flavors() {
        var first_flavor = FlavorStore.records.first();
        this.field_update("flavor", f => f.merge({
            value: first_flavor ? first_flavor.flavor_id : undefined,
            choices: FlavorStore.choices
        }));
    }

    handle_error(err) {
        if (err.error_type === "Invalid") {
            var field_id = _.last(err.error_path);
            var idx = this.id_to_index(field_id);
            if (idx >= 0) {
                this.field_set(field_id, "error", err.error);
                return;
            }
        }
        this.state = this.state.set("error", err.error);
    }

    handle_message(msg) {
        switch(msg.message) {
            case FlavorInterface.messages.FLAVORS:
                FlavorStore.wait();
                this.update_flavors();
                break;
            case ClusterInterface.messages.CLUSTER_FORM_RESET:
                this._set_defaults();
                break;
            case ClusterInterface.messages.CLUSTER_FORM_CHANGE:
                this.change_field(msg.params.field_id, msg.params.value);
                break;
            case ClusterInterface.messages.CLUSTER_CREATE:
                this.state = this.state.set("loading", true);
                break;
            case ClusterInterface.messages.CLUSTER_CREATE_SUCCESS:
                this.state = this.state.set("saved", true);
                break;
            case ClusterInterface.messages.CLUSTER_CREATE_ERROR:
                this.handle_error(msg.params);
                break;
        }
    }

    serialize() {
        var edition = this.fields.find(f => f.id === "edition");

        return this.fields
            .filter(field => field.active && field.id !== "edition")
            .toMap()
            .mapKeys((idx, field) => field.id)
            .map(field => field.value)
            .toJS();
    }
}

module.exports = new ClusterFormStore();
