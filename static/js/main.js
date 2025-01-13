let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let localStream;
let translationVolume = 1.0;

const socket = io();

async function startCall() {
    try {
        // Get user media
        localStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });
        
        // Show local video
        document.getElementById('localVideo').srcObject = localStream;
        
        // Setup audio recording
        const audioStream = new MediaStream([localStream.getAudioTracks()[0]]);
        mediaRecorder = new MediaRecorder(audioStream);
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            // Only process audio when explicitly stopped (not recording)
            if (!isRecording) {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64Audio = reader.result.split(',')[1];
                    socket.emit('translate_audio', {
                        audio: base64Audio,
                        target_lang: document.getElementById('targetLanguage').value
                    });
                };
                reader.readAsDataURL(audioBlob);
            }
            audioChunks = [];
        };
        
        // Enable controls
        document.getElementById('startButton').disabled = true;
        document.getElementById('toggleMic').disabled = false;
        document.getElementById('endButton').disabled = false;
        document.getElementById('volume').disabled = false;
        
        console.log("Call started successfully");
        
    } catch (error) {
        console.error('Error:', error);
    }
}

function toggleMicrophone() {
    if (!isRecording) {
        // Start new recording
        startRecording();
        document.getElementById('toggleMic').textContent = 'Stop Speaking';
        document.getElementById('toggleMic').style.backgroundColor = '#ff4444';
        isRecording = true;
    } else {
        // Stop recording and process translation
        stopRecording();
        document.getElementById('toggleMic').textContent = 'Start Speaking';
        document.getElementById('toggleMic').style.backgroundColor = '#007bff';
        isRecording = false;
    }
}

function startRecording() {
    audioChunks = [];
    mediaRecorder.start();
    console.log("Started recording");
}

function stopRecording() {
    if (mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
    console.log("Stopped recording");
}

// Handle volume change
document.getElementById('volume').addEventListener('input', (e) => {
    translationVolume = parseFloat(e.target.value);
});

socket.on('translation_result', (data) => {
    console.log("Received translation:", data);
    document.getElementById('localSubtitle').textContent = data.original;
    document.getElementById('remoteSubtitle').textContent = data.translated;
    
    // Play the translated audio with volume control
    if (data.audio_data) {
        const audio = new Audio(`data:audio/wav;base64,${data.audio_data}`);
        audio.volume = translationVolume;
        
        // Add loading indicator
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (loadingIndicator) loadingIndicator.style.display = 'block';
        
        audio.oncanplaythrough = () => {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            showAudioPlayingIndicator(true);
        };
        
        audio.onended = () => {
            showAudioPlayingIndicator(false);
        };
        
        audio.onerror = (error) => {
            console.error('Error loading audio:', error);
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            showAudioPlayingIndicator(false);
        };
        
        audio.play().catch(error => {
            console.error('Error playing audio:', error);
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            showAudioPlayingIndicator(false);
            handleAudioError(error);
        });
    }
});

socket.on('translation_error', (data) => {
    console.error("Translation error:", data.error);
    document.getElementById('remoteSubtitle').textContent = 'Translation error occurred';
});

function endCall() {
    if (isRecording) {
        stopRecording();
    }
    
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
    }
    
    document.getElementById('localVideo').srcObject = null;
    document.getElementById('remoteVideo').srcObject = null;
    document.getElementById('localSubtitle').textContent = 'Your speech will appear here';
    document.getElementById('remoteSubtitle').textContent = 'Translation will appear here';
    document.getElementById('startButton').disabled = false;
    document.getElementById('toggleMic').disabled = true;
    document.getElementById('endButton').disabled = true;
    document.getElementById('volume').disabled = true;
    
    isRecording = false;
}

// Add visual feedback for audio playing
function showAudioPlayingIndicator(show) {
    const indicator = document.getElementById('audioPlayingIndicator');
    if (indicator) {
        indicator.style.display = show ? 'block' : 'none';
    }
}

// Add error handling for audio context
function handleAudioError(error) {
    console.error('Audio error:', error);
    document.getElementById('remoteSubtitle').textContent = 'Audio playback error occurred';
}

// Initialize volume control
document.addEventListener('DOMContentLoaded', () => {
    const volumeControl = document.getElementById('volume');
    if (volumeControl) {
        volumeControl.value = translationVolume;
        volumeControl.disabled = true;
    }
});

// Add loading state handling
function setLoadingState(isLoading) {
    const toggleMicButton = document.getElementById('toggleMic');
    const loadingIndicator = document.getElementById('loadingIndicator');
    
    if (isLoading) {
        toggleMicButton.disabled = true;
        if (loadingIndicator) loadingIndicator.style.display = 'block';
    } else {
        toggleMicButton.disabled = false;
        if (loadingIndicator) loadingIndicator.style.display = 'none';
    }
}

// Add socket connection status handling
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

socket.on('connection_status', (data) => {
    console.log('Connection status:', data.status);
});