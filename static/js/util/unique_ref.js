var _ = require("lodash");

class UniqueRef {
    constructor(name) {
        this.name = arguments.length ? name : _.uniqueId("UniqueRef");
        Object.freeze(this);
    }

    toString() { return this.name; }
    valueOf() { return this.name; }
}

module.exports = UniqueRef;
