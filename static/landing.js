// Landing page interactions
(function () {
    const landing = document.getElementById('landing');
    const app = document.getElementById('app');
    const body = document.body;

    // Show the app (hide landing)
    function showApp() {
        landing.classList.add('fade-out');
        setTimeout(() => {
            body.classList.add('app-mode');
        }, 300);
    }

    // Show the landing (hide app)
    function showLanding() {
        body.classList.remove('app-mode');
        landing.classList.remove('fade-out');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // "Get Started" buttons (nav + CTA)
    document.querySelectorAll('[data-action="get-started"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            showApp();
        });
    });

    // "Home" nav link
    document.querySelectorAll('[data-action="home"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            if (body.classList.contains('app-mode')) {
                showLanding();
            } else {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });

    // "Examples" nav link
    document.querySelectorAll('[data-action="examples"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            if (body.classList.contains('app-mode')) {
                showLanding();
                setTimeout(() => {
                    document.getElementById('examples').scrollIntoView({ behavior: 'smooth' });
                }, 100);
            } else {
                document.getElementById('examples').scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Brand click = Home
    document.querySelectorAll('.nav-brand').forEach(brand => {
        brand.addEventListener('click', (e) => {
            e.preventDefault();
            if (body.classList.contains('app-mode')) {
                showLanding();
            } else {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });

    // Email copy-to-clipboard
    document.querySelectorAll('[data-action="copy-email"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const email = link.getAttribute('data-email');
            navigator.clipboard.writeText(email).then(() => {
                const tooltip = document.createElement('div');
                tooltip.className = 'copy-tooltip';
                tooltip.textContent = 'Email copied!';
                tooltip.style.left = e.clientX + 'px';
                tooltip.style.top = e.clientY + 'px';
                document.body.appendChild(tooltip);
                requestAnimationFrame(() => { tooltip.style.opacity = '1'; });
                setTimeout(() => {
                    tooltip.style.opacity = '0';
                    setTimeout(() => tooltip.remove(), 300);
                }, 1500);
            });
        });
    });

    // Video rotation on ended
    document.querySelectorAll('.example-video').forEach(video => {
        video.addEventListener('ended', () => {
            const videos = JSON.parse(video.getAttribute('data-videos'));
            let index = parseInt(video.getAttribute('data-video-index'), 10);
            index = (index + 1) % videos.length;
            video.setAttribute('data-video-index', index);
            video.src = videos[index];
            video.play();
        });
    });
})();
