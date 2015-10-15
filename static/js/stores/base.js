var EventEmitter = require("events").EventEmitter;
var Dispatch = require("dispatch");
var _ = require("lodash");
var I = require("immutable");

var CHANGE_EVENT = "change";

class BaseStore extends EventEmitter {
    constructor() {
        this.setMaxListeners(512);
        this.dispatch_id = Dispatch.register(_.bind(this._handle_message, this));
        this.state = I.Map();
    }

    /**
     * Wait for this store to finish -- used to handle inter-store dependencies.
     */
    wait() {
        Dispatch.waitFor([this.dispatch_id]);
    }

    _handle_message(record) {
        var start_state = this.state;
        try {
            this.handle_message(record);
        } finally {
            if (!I.is(start_state, this.state)) {
                this.changed();
            }
        }
    }

    /**
     * Process a message emitted by an action.
     */
    handle_message(record) {
        throw new Error("Every store must have a handle_message method");
    }

    /**
     * Trigger the change event on this store.
     */
    changed() {
        this.emit(CHANGE_EVENT);
    }

    /**
     * The provided callback will be executed when this store has changed.
     */
    add_change_callback(callback) {
        this.on(CHANGE_EVENT, callback);
    }

    /**
     * Stop emitting changes to the specified callback.
     */
    remove_change_callback(callback) {
        this.removeListener(CHANGE_EVENT, callback);
    }

    /**
     * Returns a React mixin which ensures that the function named by
     * `change_callback_name` is called whenever this store emits a change
     * event.
     *
     * It also will call the callback at initial mount.
     */
    change_mixin(change_callback_name) {
        var store = this;
        return {
            componentWillMount: function() { this[change_callback_name](); },
            componentDidMount: function() {
                store.add_change_callback(this[change_callback_name]);
            },
            componentWillUnmount: function() {
                store.remove_change_callback(this[change_callback_name]);
            }
        };
    }
}

module.exports = BaseStore;
