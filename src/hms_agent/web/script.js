console.log("[HMS] Script v2.1 loaded");
const ws = new WebSocket(`ws://${window.location.host}/ws/chat`);
const chatLog = document.getElementById('chat-log');
const chatInput = document.getElementById('chat-input');
const micBtn = document.getElementById('mic-btn');

let audioContext;
let processor;
let input;
let isRecording = false;

ws.onmessage = (event) => {
    if (typeof event.data === 'string') {
        const data = JSON.parse(event.data);
        if (data.type === 'text') {
            addMessage(data.content, 'agent');
        } else if (data.type === 'transcription') {
            handleTranscriptionPreview(data.content);
        }
    } else {
        // Handle binary audio response from backend
        playAudio(event.data);
    }
};

function handleTranscriptionPreview(content) {
    let preview = chatLog.querySelector('.transcription-preview');
    if (!preview) {
        preview = document.createElement('div');
        preview.className = 'transcription-preview';
        chatLog.appendChild(preview);
    }
    preview.textContent = `You: ${content}`;
    chatLog.scrollTop = chatLog.scrollHeight;
}

function addMessage(content, sender) {
    // Remove transcription preview if exists
    const preview = chatLog.querySelector('.transcription-preview');
    if (preview) preview.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-message`;
    msgDiv.textContent = content;
    chatLog.appendChild(msgDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function sendMessage() {
    const content = chatInput.value.trim();
    if (!content) return;

    ws.send(content);
    addMessage(content, 'user');
    chatInput.value = '';
}

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function toggleMic() {
    if (!isRecording) {
        try {
            // Check for mediaDevices support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("Browser does not support microphone access.");
            }

            // Always request fresh stream to ensure permissions are checked
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Initialize or resume AudioContext
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
            }

            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }

            input = audioContext.createMediaStreamSource(stream);

            // Using AudioWorklet would be better, but ScriptProcessor is used here for simplicity as requested
            processor = audioContext.createScriptProcessor(4096, 1, 1);

            processor.onaudioprocess = (e) => {
                if (!isRecording) return;
                const pcmFloat32 = e.inputBuffer.getChannelData(0);
                const pcmInt16 = new Int16Array(pcmFloat32.length);
                for (let i = 0; i < pcmFloat32.length; i++) {
                    pcmInt16[i] = Math.max(-1, Math.min(1, pcmFloat32[i])) * 0x7FFF;
                }
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(pcmInt16.buffer);
                }
            };

            input.connect(processor);
            processor.connect(audioContext.destination);

            isRecording = true;
            micBtn.classList.add('active');
            micBtn.textContent = '⏹️';
            micBtn.title = 'Stop Recording';

            logger("Microphone access granted and recording started.");
        } catch (err) {
            console.error("Error accessing microphone:", err);
            let msg = `Could not access microphone: ${err.message || err.name || "Unknown error"}`;

            if (!window.isSecureContext) {
                msg = "Microphone access requires a secure context (HTTPS or localhost). " +
                    "Please ensure you are accessing this page via http://localhost:8001 " +
                    "or use an HTTPS connection.";
            } else if (err.name === 'NotAllowedError') {
                msg = "Microphone permission denied. Please enable it in your browser settings.";
            } else if (err.name === 'NotFoundError') {
                msg = "No microphone found on this device.";
            } else if (err.name === 'NotReadableError') {
                msg = "Microphone is already in use by another application.";
            } else if (err.name === 'SecurityError') {
                msg = "Security error: Microphone access is blocked by your browser's security policy.";
            }

            alert(msg);
            stopRecording();
        }
    } else {
        stopRecording();
    }
}

function stopRecording() {
    isRecording = false;
    micBtn.classList.remove('active');
    micBtn.textContent = '🎤';
    micBtn.title = 'Start Recording';

    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (input) {
        // Stop all tracks in the stream
        const stream = input.mediaStream;
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        input.disconnect();
        input = null;
    }

    // Attempt to send end signal if websocket is open
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "end_audio" }));
    }
}

function logger(msg) {
    console.log(`[HMS] ${msg}`);
}

let audioQueue = [];
let isPlaying = false;

async function playAudio(buffer) {
    const context = new (window.AudioContext || window.webkitAudioContext)();
    const audioBuffer = await context.decodeAudioData(buffer);
    const source = context.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(context.destination);
    source.start();
}
