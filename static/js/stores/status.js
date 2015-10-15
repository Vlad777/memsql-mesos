var I = require("immutable");
var Base = require("stores/base");

var StatusInterface = require("interfaces/status");

class StatusStore extends Base {
    constructor() {
        super();
        this.state = this.state.merge({
            alive: true
        });
    }

    get alive() { return this.state.get("alive"); }

    handle_message(msg) {
        switch(msg.message) {
            case StatusInterface.messages.UP:
                this.state = this.state.set("alive", true);
                break;
            case StatusInterface.messages.DOWN:
                this.state = this.state.set("alive", false);
                break;
        }
    }
}

module.exports = new StatusStore();
