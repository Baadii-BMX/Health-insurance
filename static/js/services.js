(function () {
    'use strict';

    angular
        .module('core.services', [])
        .factory('ChatService', ChatService);

    ChatService.$inject = ['$http'];

    function ChatService($http) {
        var service = {
            sendMessage: sendMessage,
            getHospitals: getHospitals,
            getMedicines: getMedicines,
            saveUnansweredQuestion: saveUnansweredQuestion
        };

        return service;

        // Function to send message to the chatbot
        function sendMessage(message) {
            return $http.post('/chat', {
                message: message
            });
        }

        // Function to get hospitals list
        function getHospitals() {
            return $http.get('/api/hospitals');
        }

        // Function to get medicines list
        function getMedicines() {
            return $http.get('/api/medicines');
        }

        // Function to save unanswered questions
        function saveUnansweredQuestion(question) {
            return $http.post('/api/save-unanswered', {
                question: question
            });
        }
    }
})();