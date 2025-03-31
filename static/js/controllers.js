(function () {
    'use strict';

    angular
        .module('core')
        .controller('AppController', AppController);

    AppController.$inject = ['$http', '$scope', '$timeout', '$window', 'ChatService'];

    function AppController($http, $scope, $timeout, $window, ChatService) {
        var vm = this;

        // Controller properties
        vm.messages = [];
        vm.userMessage = '';
        vm.loading = false;
        vm.lastBotMessage = '';
        vm.isDarkMode = true; // Default to dark mode (like Egene VQA)

        // Apply dark mode by default
        document.body.setAttribute('data-theme', 'dark');

        // Initial bot message with quick replies matching NLU examples
        vm.messages.push({
            text: "Сайн байна уу? Би Эрүүл Мэндийн Даатгалын бот байна! Яаж туслах вэ?",
            sender: "bot",
            quickReplies: [
                "ЭМД төлбөрөө хаанаас төлөх вэ?",
                "Ямар эмнэлгүүд ЭМД-тэй гэрээтэй вэ?",
                "ЭМД-ийн хураамж хэд вэ?",
                "ЭМД шимтгэлийн дутуу саруудаа хэрхэн шалгах вэ?",
                "ЭМД-аар ямар үйлчилгээ авж болох вэ?",
                "ЭМД-ын хөнгөлөлттэй эмийн жагсаалт",
                "ЭМД шимтгэлийн төлбөрийг хаанаас төлөх вэ?",
                "ЭМД-ийн хөнгөлөлттэй эмийн жагсаалт"
            ]
        });

        // Helper Functions
        function scrollToBottom() {
            $timeout(function () {
                var chatBox = document.getElementById("chat-box");
                if (chatBox) {
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
            }, 100);
        }

        function typeMessage(botResponse) {
            if (!botResponse || !botResponse.trim() || botResponse === "-") return;

            var message = { text: "", sender: "bot" };
            vm.messages.push(message); // Add bot response to chat messages
            var index = 0;

            function typeNextLetter() {
                if (index < botResponse.length) {
                    message.text += botResponse.charAt(index);
                    index++;
                    $timeout(typeNextLetter, 25); // Faster typing for full desktop
                }
                $scope.$apply();
                scrollToBottom();
            }

            typeNextLetter();
        }

        // Public methods
        vm.sendMessage = function () {
            if (!vm.userMessage || vm.userMessage.trim() === "") return;

            // Check for Mongolian Cyrillic characters
            if (!/^[а-яА-ЯөӨүҮёЁ0-9\s.,!?@#$%^&*()_+=<>:;"'{}\[\]\\\/-]+$/.test(vm.userMessage)) {
                var invalidMessage = "Би зөвхөн монгол хэлээр ойлгох тул та асуултаа кирилл үсгээр бичнэ үү.";
                vm.messages.push({ text: vm.userMessage, sender: "user" }); // Add user message to chat
                vm.userMessage = '';
                typeMessage(invalidMessage);
                return;
            }

            vm.messages.push({ text: vm.userMessage, sender: "user" }); // Add user message to chat
            scrollToBottom();
            vm.loading = true;

            ChatService.sendMessage(vm.userMessage)
                .then(function (response) {
                    $timeout(function () {
                        console.log("✅ Success! Response from API:", response);
                
                        var botResponse = response.text || "❌ Алдаа: Хариу илгээсэнгүй.";
                        
                        if (!botResponse.trim()) {
                            console.warn("⚠️ Empty response detected. Using fallback message.");
                            botResponse = "Уучлаарай, би энэ асуултад хариулж чадахгүй байна.";
                        }
                
                        if (vm.lastBotMessage === botResponse) {
                            console.warn("⚠️ Duplicate bot response detected. Skipping...");
                            vm.loading = false;
                            return;
                        }
                        vm.lastBotMessage = botResponse;
                
                        typeMessage(botResponse);
                        vm.loading = false;
                    }, 700);
                })
                .catch(function (error) {
                    console.error("❌ Error:", error);

                    var errorMessage = "❌ Алдаа гарлаа! Интернет холболтоо шалгана уу.";
                    if (error.status === 0) {
                        errorMessage = "❌ Сервер ажиллахгүй байна. Дахин оролдоно уу.";
                    } else if (error.status === 500) {
                        errorMessage = "❌ Серверийн алдаа! Дахин оролдоно уу.";
                    } else if (error.data && error.data.message) {
                        errorMessage = "❌ " + error.data.message;
                    } else if (error.status === 404) {
                        errorMessage = "❌ /chat эндпоинт олдсонгүй! Серверийг шалгана уу.";
                    }

                    $timeout(function () {
                        typeMessage(errorMessage); // Add error message to chat
                        vm.loading = false;
                    }, 500);
                });

            vm.userMessage = ''; // Clear input after sending
        };

        vm.sendQuickReply = function(reply) {
            vm.userMessage = reply;
            vm.sendMessage();
        };

        vm.startVoiceInput = function() {
            // Voice input using Web Speech API
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                typeMessage("❌ Уучлаарай, таны вэб хөтөч дуу таних боломжгүй байна.");
                return;
            }
            
            const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'mn-MN'; // Mongolian language
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onresult = function(event) {
                const voiceMessage = event.results[0][0].transcript;
                vm.userMessage = voiceMessage;
                vm.sendMessage();
                $scope.$apply();
            };

            recognition.onerror = function(event) {
                console.error("Voice recognition error:", event.error);
                typeMessage("❌ Хоолойн тусламжтай алдаа гарлаа. Дахин оролдоно уу.");
            };

            recognition.start();
            typeMessage("Хоолойн тусламж идэвхжлээ. Яриагаа эхлүүлнэ үү...");
        };

        vm.toggleTheme = function () {
            vm.isDarkMode = !vm.isDarkMode; // Toggle mode
        
            if (vm.isDarkMode) {
                document.body.setAttribute('data-theme', 'dark');
            } else {
                document.body.setAttribute('data-theme', 'light');
            }
        };

        // Adjust container size dynamically based on window size
        function adjustContainerSize() {
            const container = document.querySelector('.chat-container');
            if (container) {
                const width = $window.innerWidth * 0.9; // 90% of viewport width
                const height = $window.innerHeight * 0.8; // 80% of viewport height for Egene VQA
                container.style.width = `${Math.min(width, 1000)}px`; // Limit max width
                container.style.height = `${Math.min(height, 800)}px`; // Limit max height
            }
        }

        angular.element($window).on('resize', function() {
            $scope.$apply(adjustContainerSize);
        });

        // Initial size adjustment
        $timeout(function() {
            adjustContainerSize();
            scrollToBottom();
        }, 100);
    }
})();
