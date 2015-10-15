var I = require("immutable");
var Base = require("stores/base");
var _ = require("lodash");

var FlavorInterface = require("interfaces/flavor");

var FlavorAttributes = I.Record({
    flavor_id: undefined,
    memory: undefined,
    cpu: undefined,
    disk: undefined
});

class Flavor extends FlavorAttributes {
    get description() {
        return [
            this.flavor_id,
            this.cpu + " Cores",
            this.memory + "GB RAM",
            this.disk + "GB Disk"
        ].join(" - ");
    }
}

class FlavorStore extends Base {
    constructor() {
        super();
        this.state = this.state.merge({
            records: I.List()
        });
    }

    get records() { return this.state.get("records"); }

    get choices() {
        return this.state.get("records")
            .sortBy(f => f.memory)
            .map(f => [ f.flavor_id, f.description ]);
    }

    lookup(flavor_id) { return this.records.find(r => r.flavor_id === flavor_id); }

    handle_message(msg) {
        switch(msg.message) {
            case FlavorInterface.messages.FLAVORS:
                this.state = this.state.set(
                    "records",
                    I.Seq(msg.params).map(
                        flavor => new Flavor(flavor)
                    ).toList().sortBy(f => f.flavor_id)
                );
                break;
        }
    }
}

module.exports = new FlavorStore();
