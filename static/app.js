// State
const COST_PER_SECOND = 0.10;
let clips = []; // { prompt, duration, clipId, status, pollInterval, referenceImage }

// API Key helpers
function getApiKey() {
    return localStorage.getItem('openai_api_key') || '';
}

function setApiKey(key) {
    localStorage.setItem('openai_api_key', key);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('clip-count').addEventListener('change', (e) => {
        updateStoryboard(parseInt(e.target.value));
    });
    updateStoryboard(1);

    // Load saved API key
    const apiKeyInput = document.getElementById('api-key-input');
    apiKeyInput.value = getApiKey();
    apiKeyInput.addEventListener('input', (e) => {
        setApiKey(e.target.value);
    });

    // Show/hide toggle
    const toggleBtn = document.getElementById('api-key-toggle');
    toggleBtn.addEventListener('click', () => {
        const isPassword = apiKeyInput.type === 'password';
        apiKeyInput.type = isPassword ? 'text' : 'password';
        toggleBtn.querySelector('.eye-icon').style.display = isPassword ? 'none' : '';
        toggleBtn.querySelector('.eye-off-icon').style.display = isPassword ? '' : 'none';
    });
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
            clips.push({ prompt: '', duration: 4, clipId: null, status: 'idle', pollInterval: null, referenceImage: null });
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
            <div class="reference-image-area" data-index="${index}">
                <label class="reference-upload-label">
                    <input type="file" class="reference-input" data-index="${index}" accept="image/jpeg,image/png,image/webp" hidden>
                    <span class="reference-upload-btn">+ Reference Image</span>
                </label>
                ${clip.referenceImage ? `
                    <div class="reference-preview">
                        <img class="reference-thumb" data-index="${index}" />
                        <button class="reference-remove" data-index="${index}" title="Remove reference image">&times;</button>
                    </div>
                ` : ''}
            </div>
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

    // Reference image inputs
    document.querySelectorAll('.reference-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const idx = parseInt(e.target.dataset.index);
            const file = e.target.files[0];
            if (file) {
                clips[idx].referenceImage = file;
                showReferencePreview(idx, file);
            }
        });
    });

    // Reference remove buttons
    document.querySelectorAll('.reference-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const idx = parseInt(e.target.dataset.index);
            clips[idx].referenceImage = null;
            refreshClipBox(idx);
        });
    });

    // Load existing reference image thumbnails
    document.querySelectorAll('.reference-thumb').forEach(img => {
        const idx = parseInt(img.dataset.index);
        if (clips[idx].referenceImage) {
            img.src = URL.createObjectURL(clips[idx].referenceImage);
        }
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

// Show a reference image preview thumbnail for a clip
function showReferencePreview(index, file) {
    const box = document.querySelectorAll('.clip-box')[index];
    if (!box) return;
    const area = box.querySelector('.reference-image-area');

    // Remove existing preview if any
    const existing = area.querySelector('.reference-preview');
    if (existing) existing.remove();

    const preview = document.createElement('div');
    preview.className = 'reference-preview';

    const img = document.createElement('img');
    img.className = 'reference-thumb';
    img.src = URL.createObjectURL(file);

    const removeBtn = document.createElement('button');
    removeBtn.className = 'reference-remove';
    removeBtn.title = 'Remove reference image';
    removeBtn.textContent = '\u00d7';
    removeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        clips[index].referenceImage = null;
        preview.remove();
        // Reset file input
        const input = area.querySelector('.reference-input');
        if (input) input.value = '';
    });

    preview.appendChild(img);
    preview.appendChild(removeBtn);
    area.appendChild(preview);
}

// Generate a single clip
async function generateClip(index) {
    const clip = clips[index];
    const prompt = clip.prompt.trim();

    if (!prompt) {
        alert('Please enter a prompt for this clip');
        return;
    }

    const apiKey = getApiKey();
    if (!apiKey) {
        if (!confirm('No API key entered. The server will fall back to the .env key (if configured). Continue?')) {
            return;
        }
    }

    clip.status = 'generating';
    clip.error = null;
    clip.clipId = null;
    refreshClipBox(index);

    try {
        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('duration', clip.duration);
        if (apiKey) {
            formData.append('api_key', apiKey);
        }
        if (clip.referenceImage) {
            formData.append('reference_image', clip.referenceImage);
        }

        const response = await fetch('/api/generate-clip', {
            method: 'POST',
            body: formData,
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

    // Update reference image area
    const refArea = box.querySelector('.reference-image-area');
    const existingPreview = refArea ? refArea.querySelector('.reference-preview') : null;
    if (clip.referenceImage && refArea && !existingPreview) {
        showReferencePreview(index, clip.referenceImage);
    } else if (!clip.referenceImage && existingPreview) {
        existingPreview.remove();
        const input = refArea.querySelector('.reference-input');
        if (input) input.value = '';
    }

    // Update status area
    const statusArea = box.querySelector('.clip-status-area');
    statusArea.innerHTML = renderStatusArea(clip);
}
