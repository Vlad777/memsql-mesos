var BaseInterface = require("interfaces/base");
var Api = require("remote/api");

class FlavorInterface extends BaseInterface {
    constructor() {
        this.define_messages({ FLAVORS: null });
    }

    load() {
        Api.call("flavor/list", {})
            .then(
                data => this.dispatch(this.messages.FLAVORS, data),
                err => console.error(err)
            );
    }
}

module.exports = new FlavorInterface();
