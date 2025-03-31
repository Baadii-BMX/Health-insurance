(function () {
    'use strict';

    angular
        .module('core')
        .factory('ChatService', ChatService);

    ChatService.$inject = ['$http', '$q'];

    function ChatService($http, $q) {
        // Service for handling chat communication with backend
        var service = {
            sendMessage: sendMessage,
            getHospitals: getHospitals,
            getMedicines: getMedicines,
            saveUnansweredQuestion: saveUnansweredQuestion
        };

        return service;

        function sendMessage(message) {
            return $http.post('/chat', { message: message })
                .then(function(response) {
                    return response.data;
                })
                .catch(function(error) {
                    console.error('Error sending message:', error);
                    return $q.reject(error);
                });
        }

        function getHospitals() {
            return $http.get('/api/hospitals')
                .then(function(response) {
                    return response.data;
                })
                .catch(function(error) {
                    console.error('Error fetching hospitals:', error);
                    return $q.reject(error);
                });
        }

        function getMedicines(params) {
            return $http.get('/api/medicines', { params: params })
                .then(function(response) {
                    return response.data;
                })
                .catch(function(error) {
                    console.error('Error fetching medicines:', error);
                    return $q.reject(error);
                });
        }

        function saveUnansweredQuestion(question) {
            return $http.post('/api/unanswered', { question: question })
                .then(function(response) {
                    return response.data;
                })
                .catch(function(error) {
                    console.error('Error saving unanswered question:', error);
                    return $q.reject(error);
                });
        }
    }
})();
