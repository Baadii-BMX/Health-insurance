(function () {
    'use strict';

    // Main Angular module
    angular
        .module('emdChatbot', ['core'])
        .config(['$interpolateProvider', function($interpolateProvider) {
            // Change default delimiters to avoid conflict with Flask's Jinja2
            $interpolateProvider.startSymbol('[[');
            $interpolateProvider.endSymbol(']]');
        }]);
})();