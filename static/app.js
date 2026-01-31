// State
let currentClips = [];
let currentJobId = null;
let pollInterval = null;
let globalStyle = '';
let clipDuration = 4;
let maxClips = 5;

// Update cost estimate
function updateCostEstimate() {
    const duration = parseInt(document.getElementById('clip-duration').value);
    const clips = parseInt(document.getElementById('max-clips').value);
    const cost = (duration * clips * 0.10).toFixed(2);
    document.getElementById('cost-estimate').textContent = `~$${cost}`;
}

// Add event listeners for settings
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('clip-duration').addEventListener('change', updateCostEstimate);
    document.getElementById('max-clips').addEventListener('change', updateCostEstimate);
    updateCostEstimate();
});

// DOM Elements
const stepInput = document.getElementById('step-input');
const stepClips = document.getElementById('step-clips');
const stepProgress = document.getElementById('step-progress');
const stepResult = document.getElementById('step-result');
const errorSection = document.getElementById('error-section');

const scriptInput = document.getElementById('script-input');
const processBtn = document.getElementById('process-btn');
const clipsContainer = document.getElementById('clips-container');
const clipsCount = document.getElementById('clips-count');
const estimatedDuration = document.getElementById('estimated-duration');
const backBtn = document.getElementById('back-btn');
const generateBtn = document.getElementById('generate-btn');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const previewVideo = document.getElementById('preview-video');
const downloadBtn = document.getElementById('download-btn');
const newVideoBtn = document.getElementById('new-video-btn');
const errorMessage = document.getElementById('error-message');
const retryBtn = document.getElementById('retry-btn');

// Show specific step
function showStep(stepElement) {
    [stepInput, stepClips, stepProgress, stepResult, errorSection].forEach(el => {
        el.classList.remove('active');
    });
    stepElement.classList.add('active');
}

// Show error
function showError(message) {
    errorMessage.textContent = message;
    showStep(errorSection);
}

// Process text into clips
async function processText() {
    const text = scriptInput.value.trim();
    if (!text) {
        alert('Please enter some text');
        return;
    }

    globalStyle = document.getElementById('global-style').value.trim();
    clipDuration = parseInt(document.getElementById('clip-duration').value);
    maxClips = parseInt(document.getElementById('max-clips').value);

    processBtn.disabled = true;
    processBtn.textContent = 'Processing...';

    try {
        const response = await fetch('/api/process-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                style: globalStyle,
                clip_duration: clipDuration,
                max_clips: maxClips
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to process text');
        }

        currentClips = data.clips;
        renderClips(data);
        showStep(stepClips);
    } catch (error) {
        showError(error.message);
    } finally {
        processBtn.disabled = false;
        processBtn.textContent = 'Process Text';
    }
}

// Render clips in editor
function renderClips(data) {
    clipsCount.textContent = `${data.total_clips} clips`;
    estimatedDuration.textContent = `~${data.estimated_duration} seconds`;

    // Show global style if set
    const stylePreview = document.getElementById('style-preview');
    const styleText = document.getElementById('style-text');
    if (globalStyle) {
        styleText.textContent = globalStyle;
        stylePreview.classList.remove('hidden');
    } else {
        stylePreview.classList.add('hidden');
    }

    clipsContainer.innerHTML = '';

    data.clips.forEach((clip, index) => {
        const card = document.createElement('div');
        card.className = 'clip-card';
        card.innerHTML = `
            <div class="clip-header">
                <span class="clip-number">Clip ${clip.id}</span>
                <span class="clip-duration">${data.clip_duration}s</span>
            </div>
            <div class="clip-field">
                <label>Scene Description</label>
                <textarea data-clip-id="${clip.id}" data-field="visual_prompt">${clip.visual_prompt}</textarea>
            </div>
        `;
        clipsContainer.appendChild(card);
    });
}

// Get updated clips from editor
function getUpdatedClips() {
    const updated = [...currentClips];

    document.querySelectorAll('.clip-card textarea').forEach(textarea => {
        const clipId = parseInt(textarea.dataset.clipId);
        const field = textarea.dataset.field;
        const clip = updated.find(c => c.id === clipId);
        if (clip) {
            clip[field] = textarea.value;
        }
    });

    return updated;
}

// Start video generation
async function startGeneration() {
    const clips = getUpdatedClips();

    generateBtn.disabled = true;
    generateBtn.textContent = 'Starting...';

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                clips,
                clip_duration: clipDuration,
                global_style: globalStyle
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start generation');
        }

        currentJobId = data.job_id;
        showStep(stepProgress);
        startPolling();
    } catch (error) {
        showError(error.message);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Video';
    }
}

// Poll for job status
function startPolling() {
    progressFill.style.width = '0%';
    progressText.textContent = 'Starting generation...';

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentJobId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get status');
            }

            updateProgress(data);

            if (data.status === 'completed') {
                stopPolling();
                showResult();
            } else if (data.status === 'failed') {
                stopPolling();
                showError(data.error || 'Generation failed');
            }
        } catch (error) {
            stopPolling();
            showError(error.message);
        }
    }, 2000);
}

// Stop polling
function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Update progress display
function updateProgress(data) {
    progressFill.style.width = `${data.progress}%`;

    let statusText = '';
    switch (data.status) {
        case 'queued':
            statusText = 'Waiting in queue...';
            break;
        case 'processing':
            if (data.progress < 10) {
                statusText = 'Analyzing story for consistency...';
            } else {
                statusText = 'Stitching clips together...';
            }
            break;
        case 'generating':
            statusText = `Generating clip ${data.current_clip} of ${data.total_clips}...`;
            break;
        default:
            statusText = 'Working...';
    }
    progressText.textContent = statusText;
}

// Show result
function showResult() {
    previewVideo.src = `/api/preview/${currentJobId}`;
    showStep(stepResult);
}

// Download video
function downloadVideo() {
    window.location.href = `/api/download/${currentJobId}`;
}

// Reset to start
function resetApp() {
    currentClips = [];
    currentJobId = null;
    globalStyle = '';
    scriptInput.value = '';
    document.getElementById('global-style').value = '';
    previewVideo.src = '';
    showStep(stepInput);
}

// Event listeners
processBtn.addEventListener('click', processText);
backBtn.addEventListener('click', () => showStep(stepInput));
generateBtn.addEventListener('click', startGeneration);
downloadBtn.addEventListener('click', downloadVideo);
newVideoBtn.addEventListener('click', resetApp);
retryBtn.addEventListener('click', resetApp);

// Keyboard shortcut: Ctrl+Enter to process/generate
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        if (stepInput.classList.contains('active')) {
            processText();
        } else if (stepClips.classList.contains('active')) {
            startGeneration();
        }
    }
});
