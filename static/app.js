// State
const COST_PER_SECOND = 0.10;
let clips = []; // { prompt, duration, clipId, status, pollInterval }

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('clip-count').addEventListener('change', (e) => {
        updateStoryboard(parseInt(e.target.value));
    });
    updateStoryboard(1);
});

// Render clip boxes into #storyboard, preserving existing prompts
function updateStoryboard(count) {
    const storyboard = document.getElementById('storyboard');

    // Preserve existing clip data
    const oldClips = [...clips];

    // Build new clips array
    clips = [];
    for (let i = 0; i < count; i++) {
        if (i < oldClips.length) {
            clips.push(oldClips[i]);
        } else {
            clips.push({ prompt: '', duration: 4, clipId: null, status: 'idle', pollInterval: null });
        }
    }

    // Clear old poll intervals for removed clips
    for (let i = count; i < oldClips.length; i++) {
        if (oldClips[i].pollInterval) {
            clearInterval(oldClips[i].pollInterval);
        }
    }

    // Render
    storyboard.innerHTML = '';
    clips.forEach((clip, index) => {
        const box = document.createElement('div');
        box.className = 'clip-box';
        if (clip.status === 'completed') box.classList.add('completed');
        if (clip.status === 'failed') box.classList.add('failed');
        if (clip.status === 'generating') box.classList.add('generating');

        const cost = (clip.duration * COST_PER_SECOND).toFixed(2);

        box.innerHTML = `
            <div class="clip-header">
                <span class="clip-number">Clip ${index + 1}</span>
                <div class="clip-controls">
                    <select class="clip-duration" data-index="${index}">
                        <option value="4"${clip.duration === 4 ? ' selected' : ''}>4s</option>
                        <option value="8"${clip.duration === 8 ? ' selected' : ''}>8s</option>
                        <option value="12"${clip.duration === 12 ? ' selected' : ''}>12s</option>
                    </select>
                    <span class="clip-cost">$${cost}</span>
                </div>
            </div>
            <textarea class="clip-prompt" data-index="${index}" placeholder="Describe this clip...">${clip.prompt}</textarea>
            <div class="clip-actions">
                <button class="primary-btn generate-clip-btn" data-index="${index}"${clip.status === 'generating' ? ' disabled' : ''}>
                    ${clip.status === 'generating' ? 'Generating...' : 'Generate'}
                </button>
                ${clip.status === 'completed' && clip.clipId ? `<a href="/api/download-clip/${clip.clipId}" class="secondary-btn download-link">Download</a>` : ''}
            </div>
            <div class="clip-status-area" data-index="${index}">
                ${renderStatusArea(clip)}
            </div>
        `;

        storyboard.appendChild(box);
    });

    // Attach event listeners
    document.querySelectorAll('.clip-duration').forEach(select => {
        select.addEventListener('change', (e) => {
            const idx = parseInt(e.target.dataset.index);
            clips[idx].duration = parseInt(e.target.value);
            updateClipCost(idx);
        });
    });

    document.querySelectorAll('.clip-prompt').forEach(textarea => {
        textarea.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.index);
            clips[idx].prompt = e.target.value;
        });
    });

    document.querySelectorAll('.generate-clip-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.index);
            generateClip(idx);
        });
    });
}

// Render the status area content for a clip
function renderStatusArea(clip) {
    switch (clip.status) {
        case 'generating':
            return '<div class="spinner"></div><p class="status-text">Generating video...</p>';
        case 'completed':
            return `<video controls src="/api/preview-clip/${clip.clipId}"></video>`;
        case 'failed':
            return `<p class="error-text">Error: ${clip.error || 'Generation failed'}</p>`;
        default:
            return '';
    }
}

// Update the cost display for a clip
function updateClipCost(index) {
    const box = document.querySelectorAll('.clip-box')[index];
    if (!box) return;
    const cost = (clips[index].duration * COST_PER_SECOND).toFixed(2);
    box.querySelector('.clip-cost').textContent = `$${cost}`;
}

// Generate a single clip
async function generateClip(index) {
    const clip = clips[index];
    const prompt = clip.prompt.trim();

    if (!prompt) {
        alert('Please enter a prompt for this clip');
        return;
    }

    clip.status = 'generating';
    clip.error = null;
    clip.clipId = null;
    refreshClipBox(index);

    try {
        const response = await fetch('/api/generate-clip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, duration: clip.duration }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start generation');
        }

        clip.clipId = data.clip_id;
        startClipPolling(index);
    } catch (error) {
        clip.status = 'failed';
        clip.error = error.message;
        refreshClipBox(index);
    }
}

// Poll for a single clip's status
function startClipPolling(index) {
    const clip = clips[index];

    clip.pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/clip-status/${clip.clipId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get status');
            }

            if (data.status === 'completed') {
                clearInterval(clip.pollInterval);
                clip.pollInterval = null;
                clip.status = 'completed';
                refreshClipBox(index);
            } else if (data.status === 'failed') {
                clearInterval(clip.pollInterval);
                clip.pollInterval = null;
                clip.status = 'failed';
                clip.error = data.error || 'Generation failed';
                refreshClipBox(index);
            }
        } catch (error) {
            clearInterval(clip.pollInterval);
            clip.pollInterval = null;
            clip.status = 'failed';
            clip.error = error.message;
            refreshClipBox(index);
        }
    }, 3000);
}

// Refresh a single clip box in place without re-rendering the whole storyboard
function refreshClipBox(index) {
    const box = document.querySelectorAll('.clip-box')[index];
    if (!box) return;

    const clip = clips[index];

    // Update classes
    box.classList.toggle('completed', clip.status === 'completed');
    box.classList.toggle('failed', clip.status === 'failed');
    box.classList.toggle('generating', clip.status === 'generating');

    // Update button
    const btn = box.querySelector('.generate-clip-btn');
    btn.disabled = clip.status === 'generating';
    btn.textContent = clip.status === 'generating' ? 'Generating...' : 'Generate';

    // Update download link
    const actions = box.querySelector('.clip-actions');
    const existingLink = actions.querySelector('.download-link');
    if (clip.status === 'completed' && clip.clipId) {
        if (!existingLink) {
            const link = document.createElement('a');
            link.href = `/api/download-clip/${clip.clipId}`;
            link.className = 'secondary-btn download-link';
            link.textContent = 'Download';
            actions.appendChild(link);
        }
    } else if (existingLink) {
        existingLink.remove();
    }

    // Update status area
    const statusArea = box.querySelector('.clip-status-area');
    statusArea.innerHTML = renderStatusArea(clip);
}
