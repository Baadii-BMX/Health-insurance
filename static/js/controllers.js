(function () {
    'use strict';

    angular
        .module('core', ['core.services'])
        .controller('ChatController', ChatController);

    ChatController.$inject = ['$scope', 'ChatService'];

    function ChatController($scope, ChatService) {
        var vm = this;

        // Initialize variables
        vm.messageText = '';
        vm.chatMessages = [];
        vm.isLoadingResponse = false;
        vm.darkMode = localStorage.getItem('darkMode') === 'true' || false;
        vm.isRecording = false;
        vm.recognition = null;
        vm.isMicAvailable = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;

        // Initialize speech recognition if available
        if (vm.isMicAvailable) {
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            vm.recognition = new SpeechRecognition();
            vm.recognition.continuous = false;
            vm.recognition.interimResults = false;
            vm.recognition.lang = 'mn-MN'; // Mongolian language

            vm.recognition.onresult = function(event) {
                var transcript = event.results[0][0].transcript;
                vm.messageText = transcript;
                $scope.$apply();
            };

            vm.recognition.onerror = function(event) {
                console.error('Speech recognition error:', event.error);
                vm.isRecording = false;
                $scope.$apply();
            };

            vm.recognition.onend = function() {
                vm.isRecording = false;
                $scope.$apply();
            };
        }

        // Function to toggle recording state
        vm.toggleRecording = function() {
            if (vm.isRecording) {
                vm.recognition.stop();
                vm.isRecording = false;
            } else {
                vm.recognition.start();
                vm.isRecording = true;
            }
        };

        // Function to toggle dark mode
        vm.toggleDarkMode = function() {
            vm.darkMode = !vm.darkMode;
            localStorage.setItem('darkMode', vm.darkMode);
            document.documentElement.setAttribute('data-bs-theme', vm.darkMode ? 'dark' : 'light');
        };

        // Apply dark mode on initialization
        document.documentElement.setAttribute('data-bs-theme', vm.darkMode ? 'dark' : 'light');

        // Function to send message
        vm.sendMessage = function() {
            if (!vm.messageText.trim()) return;

            var userMessage = {
                text: vm.messageText,
                sender: 'user',
                timestamp: new Date()
            };

            vm.chatMessages.push(userMessage);
            vm.isLoadingResponse = true;
            vm.messageText = '';

            // Send message to backend
            ChatService.sendMessage(userMessage.text)
                .then(function(response) {
                    var botMessage = {
                        text: response.data.text || 'Уучлаарай, хариулт олдсонгүй.',
                        sender: 'bot',
                        timestamp: new Date()
                    };
                    vm.chatMessages.push(botMessage);
                })
                .catch(function(error) {
                    console.error('Error sending message:', error);
                    vm.chatMessages.push({
                        text: 'Уучлаарай, алдаа гарлаа. Дараа дахин оролдоно уу.',
                        sender: 'bot',
                        timestamp: new Date()
                    });

                    // Save the unanswered question
                    ChatService.saveUnansweredQuestion(userMessage.text)
                        .catch(function(error) {
                            console.error('Error saving unanswered question:', error);
                        });
                })
                .finally(function() {
                    vm.isLoadingResponse = false;
                    // Scroll to bottom of chat
                    setTimeout(function() {
                        var chatContainer = document.querySelector('.chat-messages');
                        if (chatContainer) {
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    }, 100);
                });
        };
    }
})();