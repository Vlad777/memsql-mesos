var Dispatch = require("dispatch");
var _ = require("lodash");
var UniqueRef = require("util/unique_ref");

class BaseInterface {
    constructor() {
        this.messages = {};
        _.bindAll(this);
    }

    define_messages(messages) {
        this.messages = _.reduce(messages, function(memo, val, key) {
            memo[key] = new UniqueRef(key);
            return memo;
        }, {});
    }

    dispatch(message, params={}) {
        Dispatch.dispatch({ message, params });
    }
}

module.exports = BaseInterface;
