document.addEventListener('DOMContentLoaded', () => {
    const extractForm = document.getElementById('extractForm');
    const videoUrlInput = document.getElementById('videoUrl');
    const btnSubmit = document.getElementById('btnSubmit');
    const loadingState = document.getElementById('loadingState');
    const resultCard = document.getElementById('resultCard');
    
    const videoThumb = document.getElementById('videoThumb');
    const videoTitle = document.getElementById('videoTitle');
    const videoDuration = document.getElementById('videoDuration');
    const videoUploader = document.getElementById('videoUploader');
    const formatList = document.getElementById('formatList');
    const historyList = document.getElementById('historyList');
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');

    // Health Check Initialization
    checkHealth();
    loadHistory();

    extractForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = videoUrlInput.value.trim();
        if (!url) return;

        showLoading(true);
        resultCard.classList.add('hidden');

        try {
            const res = await fetch('/api/extract-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            if (!res.ok) throw new Error('Failed to extract video details');

            const data = await res.json();
            displayVideoResult(data);
            loadHistory();
        } catch (err) {
            alert('Error extracting video: ' + err.message);
        } finally {
            showLoading(false);
        }
    });

    refreshHistoryBtn.addEventListener('click', loadHistory);

    function displayVideoResult(data) {
        videoThumb.src = data.thumbnail || 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=600&q=80';
        videoTitle.textContent = data.title;
        videoDuration.textContent = data.duration;
        videoUploader.textContent = data.uploader || 'Facebook User';

        formatList.innerHTML = '';
        data.formats.forEach((fmt) => {
            const formatDiv = document.createElement('div');
            formatDiv.className = 'flex items-center justify-between p-3 bg-slate-800/80 hover:bg-slate-800 rounded-xl border border-slate-700 transition-all';
            
            const encodedStreamUrl = encodeURIComponent(fmt.url);
            const downloadApiUrl = `/api/download-stream?url=${encodedStreamUrl}&filename=${encodeURIComponent(data.title.replace(/[^a-zA-Z0-9]/g, '_') + '.mp4')}`;

            formatDiv.innerHTML = `
                <div class="flex items-center space-x-3">
                    <span class="px-2.5 py-1 text-xs font-bold rounded-lg bg-brand-500/20 text-brand-400 border border-brand-500/30">
                        ${fmt.quality.toUpperCase()}
                    </span>
                    <span class="text-xs text-slate-400">${fmt.ext.toUpperCase()}</span>
                </div>
                <a href="${downloadApiUrl}" target="_blank" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1 transition-colors">
                    <i class="fa-solid fa-download"></i>
                    <span>Download</span>
                </a>
            `;
            formatList.appendChild(formatDiv);
        });

        resultCard.classList.remove('hidden');
    }

    async function loadHistory() {
        try {
            const res = await fetch('/api/user/history');
            const data = await res.json();
            
            historyList.innerHTML = '';
            if (data.length === 0) {
                historyList.innerHTML = `<p class="text-slate-500 text-sm col-span-2">No history recorded yet.</p>`;
                return;
            }

            data.forEach(item => {
                const card = document.createElement('div');
                card.className = 'flex items-center space-x-4 p-3 bg-slate-900 border border-slate-800 rounded-2xl relative group';
                card.innerHTML = `
                    <img src="${item.thumbnail}" class="w-16 h-16 object-cover rounded-xl bg-slate-950 flex-shrink-0">
                    <div class="flex-grow min-w-0">
                        <h4 class="text-sm font-semibold text-slate-200 truncate">${item.title}</h4>
                        <p class="text-xs text-slate-400 mt-1">${item.quality} &bull; ${item.created_at}</p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button onclick="deleteHistoryItem(${item.id})" class="p-2 text-slate-500 hover:text-red-400 transition-colors">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                `;
                historyList.appendChild(card);
            });
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    }

    async function checkHealth() {
        try {
            const res = await fetch('/api/health');
            const data = await res.json();
            const healthText = document.getElementById('healthText');
            if (data.status === 'healthy') {
                healthText.textContent = 'System Online';
            } else {
                healthText.textContent = 'Degraded';
            }
        } catch (e) {
            const healthText = document.getElementById('healthText');
            if(healthText) healthText.textContent = 'Offline';
        }
    }

    function showLoading(show) {
        if (show) {
            loadingState.classList.remove('hidden');
            loadingState.classList.add('flex');
            btnSubmit.disabled = true;
            btnSubmit.classList.add('opacity-50');
        } else {
            loadingState.classList.add('hidden');
            loadingState.classList.remove('flex');
            btnSubmit.disabled = false;
            btnSubmit.classList.remove('opacity-50');
        }
    }

    window.deleteHistoryItem = async function(id) {
        try {
            await fetch(`/api/user/history/${id}`, { method: 'DELETE' });
            loadHistory();
        } catch (err) {
            console.error('Failed to delete history item:', err);
        }
    };
});