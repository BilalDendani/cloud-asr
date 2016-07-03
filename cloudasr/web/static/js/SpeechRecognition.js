(function(window){

    var SpeechRecognition = function(apiUrl) {
        this.continuous = true;
        this.interimResults = true;
        this.onstart = function() {};
        this.onresult = function(event) {};
        this.onerror = function(event) {};
        this.onend = function() {};
        this.onchunk = function(chunk) {};
        this.volumeCallback = function(volume) {};
        this.isRecording = false;
        this.quietForChunks = 0;

        var recognizer = this;
        var recorder = createRecorder();
        var socket = createSocket(apiUrl);

        this.start = function(model) {
            socket.emit('begin', model);
            recorder.record();
            this.isRecording = true;
            this.onstart();
        };

        this.stop = function() {
            socket.emit('end');
            recorder.stop();
            this.isRecording = false;
            this.onend();
        };

        this.changeLM = function(newLM) {
            console.log(newLM);
            socket.emit('change_lm', newLM);
        }

        var handleResult = function(results) {
            recognizer.onresult(results);
        };

        var handleError = function(error) {
            recognizer.onerror(error);
            recognizer.onend();
            recognizer.isRecording = false;
            recorder.stop();
        };

        var handleEnd = function() {
            recognizer.onend();
        };

        function createSocket(apiUrl) {
            socket = io.connect(apiUrl);
            socket.binaryType = "arraybuffer";

            socket.on("connect", function() {
                console.log("Socket connected");
            });

            socket.on("connect_failed", function() {
                handleError("Unable to connect to the server.");
            });

            socket.on("result", function(result) {
                handleResult(result);
            });

            socket.on("error", function(error) {
                handleError(error);
            });

            socket.on("server_error", function(error) {
                handleError(error.message);
            });

            socket.on("end", function(error) {
                handleEnd();
            });

            return socket;
        }

        function createRecorder() {
            recorder = new Recorder({
                bufferCallback: handleChunk,
                errorCallback: handleError,
                volumeCallback: handleVolume,
            });
            recorder.init();

            return recorder;
        }

        function handleChunk(chunk) {
            socket.emit("chunk", 44100, floatTo16BitPcm(chunk[0]));
            recognizer.onchunk(chunk);
        }

        function floatTo16BitPcm(chunk) {
            result = new Int16Array(chunk.length);
            for( i = 0; i < chunk.length; i++ ) {
                var s = Math.max(-1, Math.min(1, chunk[i]));
                result[i] = Math.round(s < 0 ? s * 0x8000 : s * 0x7FFF);
            }

            return result.buffer;
        }

        function handleVolume(volume) {
            if(volume == 0) {
                if(recognizer.quietForChunks >= 10) {
                    return handleError("Microphone is not working!");
                }

                recognizer.quietForChunks++;
            } else {
                recognizer.quietForChunks = 0;
            }

            recognizer.volumeCallback(volume);
        };
    }

    window.SpeechRecognition = SpeechRecognition;

})(window);
