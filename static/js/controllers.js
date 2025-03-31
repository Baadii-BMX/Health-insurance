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
        vm.showQuickQuestions = true;
        
        // Quick questions categories
        vm.currentCategory = 'main';
        
        // Main quick questions list
        vm.mainQuestions = [
            { id: 1, text: 'ЭМД төлбөр хэмжээ хэд вэ?', category: 'payment' },
            { id: 2, text: 'Эмийн үнийн хөнгөлөлт', category: 'medicine' },
            { id: 3, text: 'Хөнгөлөлттэй эмийн жагсаалт', category: 'medicine' },
            { id: 4, text: 'ЭМД-ын гэрээт эмнэлгүүд', category: 'hospitals' },
            { id: 5, text: 'Даатгалын шимтгэлийн дутуу саруудаа хэрхэн шалгах вэ?', category: 'payment' },
            { id: 6, text: 'Эрүүл мэндийн даатгалаа хэрхэн төлөх вэ?', category: 'payment' },
            { id: 7, text: 'Даатгалаараа ямар оношилгоонд хамрагдаж болох вэ?', category: 'services' }
        ];
        
        // Medicine related questions
        vm.medicineQuestions = [
            { id: 8, text: 'Зүрх судасны эмийн хөнгөлөлт' },
            { id: 9, text: 'Чихрийн шижингийн эмийн хөнгөлөлт' },
            { id: 10, text: 'Астма, уушгины эмийн хөнгөлөлт' },
            { id: 11, text: 'Буцах' }
        ];
        
        // Payment related questions
        vm.paymentQuestions = [
            { id: 12, text: 'И-Баримт гар утасны апп ашиглах' },
            { id: 13, text: 'Банкны салбар ашиглах' },
            { id: 14, text: 'E-Mongolia аппликейшн ашиглах' },
            { id: 15, text: 'Буцах' }
        ];
        
        // Hospital related questions
        vm.hospitalsQuestions = [
            { id: 16, text: 'Улаанбаатар хотын эмнэлгүүд' },
            { id: 17, text: 'Орон нутгийн эмнэлгүүд' },
            { id: 18, text: 'Хувийн эмнэлгүүд' },
            { id: 19, text: 'Буцах' }
        ];
        
        // Services related questions
        vm.servicesQuestions = [
            { id: 20, text: 'Оношилгоо, шинжилгээ' },
            { id: 21, text: 'Хэвтүүлэн эмчлэх тусламж' },
            { id: 22, text: 'Өдрийн эмчилгээ' },
            { id: 23, text: 'Буцах' }
        ];
        
        // Set active questions based on category
        vm.quickQuestions = vm.mainQuestions;

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

        // Function to change question category
        vm.changeQuestionCategory = function(category) {
            if (category === 'main') {
                vm.quickQuestions = vm.mainQuestions;
                vm.currentCategory = 'main';
            } else if (category === 'medicine') {
                vm.quickQuestions = vm.medicineQuestions;
                vm.currentCategory = 'medicine';
            } else if (category === 'payment') {
                vm.quickQuestions = vm.paymentQuestions;
                vm.currentCategory = 'payment';
            } else if (category === 'hospitals') {
                vm.quickQuestions = vm.hospitalsQuestions;
                vm.currentCategory = 'hospitals';
            } else if (category === 'services') {
                vm.quickQuestions = vm.servicesQuestions;
                vm.currentCategory = 'services';
            }
        };
        
        // Function to handle quick question selection
        vm.selectQuickQuestion = function(question) {
            // If it's the "Буцах" option
            if (question.text === 'Буцах') {
                vm.changeQuestionCategory('main');
                return;
            }
            
            // If the question has a category, show that category's questions after answer
            if (question.category) {
                setTimeout(function() {
                    vm.changeQuestionCategory(question.category);
                    $scope.$apply();
                }, 1000);
            }
            
            vm.messageText = question.text;
            vm.sendMessage();
        };
        
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
            // Scroll to bottom immediately after user sends message
            setTimeout(function() {
                var chatContainer = document.querySelector('.chat-messages');
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }, 50);

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
                    
                    // Log for debugging
                    console.log('Chat messages:', vm.chatMessages);
                });
        };
    }
})();