var Dispatcher = require("flux").Dispatcher;
var batchedUpdates = require("react/addons").addons.batchedUpdates;

class Dispatch extends Dispatcher {
    dispatch(payload) {
        batchedUpdates(() =>
            Dispatcher.prototype.dispatch.call(this, payload));
    }
}

module.exports = new Dispatch();
