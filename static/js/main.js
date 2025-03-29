document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('interviewForm');
    const startButton = document.getElementById('startButton');
    const cancelButton = document.getElementById('cancelButton');
    const statusDiv = document.getElementById('status');
    const avatar = document.getElementById('interviewer-avatar');
    let conversationId = null;
    let ws = null;
    let audioContext = null;
    let audioQueue = [];
    let isPlaying = false;
    let wsConnected = false;
    let connectionPromise = null;

    // Disable cancel button initially
    cancelButton.disabled = true;

    // Initialize audio context
    function initAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    // Play audio from base64 data
    async function playAudio(base64Data) {
        if (!audioContext) {
            initAudioContext();
        }

        const audioData = atob(base64Data);
        const arrayBuffer = new ArrayBuffer(audioData.length);
        const view = new Uint8Array(arrayBuffer);
        for (let i = 0; i < audioData.length; i++) {
            view[i] = audioData.charCodeAt(i);
        }

        try {
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContext.destination);
            source.start(0);
            return new Promise(resolve => {
                source.onended = resolve;
            });
        } catch (error) {
            console.error('Error playing audio:', error);
        }
    }

    // Process audio queue
    async function processAudioQueue() {
        if (isPlaying || audioQueue.length === 0) return;
        
        isPlaying = true;
        const audioData = audioQueue.shift();
        await playAudio(audioData);
        isPlaying = false;
        processAudioQueue();
    }

    // Initialize WebSocket connection
    function initWebSocket(agentId) {
        return new Promise((resolve, reject) => {
            if (ws) {
                console.log('Closing existing WebSocket connection');
                ws.close();
            }

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/${agentId}`;
            console.log('Attempting to connect to WebSocket:', wsUrl);
            
            ws = new WebSocket(wsUrl);
            
            // Set a connection timeout
            const timeout = setTimeout(() => {
                if (!wsConnected) {
                    console.log('WebSocket connection timeout');
                    ws.close();
                    reject(new Error('WebSocket connection timeout'));
                }
            }, 10000); // Increased timeout to 10 seconds
            
            ws.onopen = () => {
                console.log('WebSocket connection opened');
                clearTimeout(timeout);
                wsConnected = true;
                resolve();
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('Received WebSocket message:', data);
                    if (data.type === 'connection' && data.status === 'established') {
                        console.log('WebSocket connection confirmed by server');
                        wsConnected = true;
                    } else if (data.type === 'audio') {
                        console.log('Received audio data');
                        audioQueue.push(data.data);
                        processAudioQueue();
                    }
                } catch (error) {
                    console.error('Error processing message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                clearTimeout(timeout);
                wsConnected = false;
                reject(error);
            };

            ws.onclose = (event) => {
                console.log('WebSocket connection closed:', event.code, event.reason);
                clearTimeout(timeout);
                wsConnected = false;
                avatar.classList.remove('speaking');
                startButton.disabled = false;
                cancelButton.disabled = true;
            };
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const agentId = document.getElementById('agentId').value;
        const apiKey = document.getElementById('apiKey').value;
        const resume = document.getElementById('resume').value;
        const jobDescription = document.getElementById('jobDescription').value;
        
        if (!agentId || !apiKey || !resume || !jobDescription) {
            showError('Please fill in all fields');
            return;
        }

        try {
            showStatus('Establishing connection...');
            console.log('Starting connection process...');
            
            // Initialize WebSocket connection first
            await initWebSocket(agentId);
            
            if (!wsConnected) {
                throw new Error('Failed to establish WebSocket connection');
            }

            console.log('WebSocket connected, waiting for confirmation...');
            // Wait a moment to ensure connection is fully established
            await new Promise(resolve => setTimeout(resolve, 2000));

            showStatus('Starting interview...');
            startButton.disabled = true;
            cancelButton.disabled = false;
            avatar.classList.add('speaking');

            console.log('Sending offer request...');
            const response = await fetch('/offer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agentId: agentId,
                    apiKey: apiKey,
                    resume: resume,
                    jobDescription: jobDescription,
                    sdp: 'offer'
                })
            });

            console.log('Received response:', response.status);
            const data = await response.json();
            console.log('Response data:', data);
            
            if (response.ok) {
                showStatus('Interview started successfully');
                conversationId = data.conversationId;
            } else {
                throw new Error(data.error || 'Failed to start interview');
            }
        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
            startButton.disabled = false;
            cancelButton.disabled = true;
            avatar.classList.remove('speaking');
            if (ws) {
                ws.close();
                ws = null;
            }
        }
    });

    cancelButton.addEventListener('click', async () => {
        try {
            showStatus('Canceling interview...');
            
            const agentId = document.getElementById('agentId').value;
            
            if (ws) {
                ws.close();
                ws = null;
            }

            if (audioContext) {
                await audioContext.close();
                audioContext = null;
            }

            audioQueue = [];
            isPlaying = false;
            
            const response = await fetch('/cancel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agentId: agentId
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                form.reset();
                startButton.disabled = false;
                cancelButton.disabled = true;
                avatar.classList.remove('speaking');
                showStatus('Interview canceled');
            } else {
                throw new Error(data.error || 'Failed to cancel interview');
            }
        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
        }
    });

    function showStatus(message) {
        statusDiv.textContent = message;
        statusDiv.classList.remove('error');
        statusDiv.classList.add('active');
        statusDiv.style.display = 'block';
    }

    function showError(message) {
        statusDiv.textContent = message;
        statusDiv.classList.remove('active');
        statusDiv.classList.add('error');
        statusDiv.style.display = 'block';
    }
}); 