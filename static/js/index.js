// Polyfills
require('es6-promise').polyfill();

var $ = require("jquery");
var Api = window.Api = require('remote/api');
var React = require('react');
var App = require('components/app');

window.stores = {
    cluster: require('stores/cluster'),
    cluster_form: require('stores/cluster_form'),
    flavor: require('stores/flavor'),
    status: require('stores/status'),
};

window.interfaces = {
    cluster: require('interfaces/cluster'),
    flavor: require('interfaces/flavor'),
    status: require('interfaces/status'),
};

$(function() {
    interfaces.cluster.start_poller();
    interfaces.status.start_poller();
    interfaces.flavor.load();

    React.render(<App />, document.body);
});
