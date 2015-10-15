var BaseInterface = require("interfaces/base");
var Api = require("remote/api");

var POLL_INTERVAL = 2000;

class StatusInterface extends BaseInterface {
    constructor() {
        this.define_messages({ UP: null, DOWN: null });
    }

    ping() {
        return Api.call("ping", {})
            .then(
                data => this.dispatch(this.messages.UP),
                err => this.dispatch(this.messages.DOWN)
            );
    }

    start_poller() {
        var poll = () => {
            this.ping()
                .then(() => window.setTimeout(poll, POLL_INTERVAL));
        };

        poll();
    }
}

module.exports = new StatusInterface();
