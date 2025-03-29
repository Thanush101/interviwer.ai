document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('interviewForm');
    const startButton = document.getElementById('startButton');
    const cancelButton = document.getElementById('cancelButton');
    const statusDiv = document.getElementById('status');
    const avatar = document.getElementById('interviewer-avatar');
    let conversationId = null;

    // Disable cancel button initially
    cancelButton.disabled = true;

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
            showStatus('Starting interview...');
            startButton.disabled = true;
            cancelButton.disabled = false;
            
            // Start speaking animation
            avatar.classList.add('speaking');

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

            const data = await response.json();
            
            if (response.ok) {
                showStatus('Interview started successfully');
                conversationId = data.conversationId;
            } else {
                throw new Error(data.error || 'Failed to start interview');
            }
        } catch (error) {
            showError(error.message);
            startButton.disabled = false;
            cancelButton.disabled = true;
            avatar.classList.remove('speaking');
        }
    });

    cancelButton.addEventListener('click', async () => {
        try {
            showStatus('Canceling interview...');
            
            const agentId = document.getElementById('agentId').value;
            
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
