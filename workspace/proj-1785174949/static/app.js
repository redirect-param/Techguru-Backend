document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileGrid = document.getElementById('file-grid');
    const emptyState = document.getElementById('empty-state');
    const storageStats = document.getElementById('storage-stats');
    const refreshBtn = document.getElementById('refresh-btn');
    
    const progressContainer = document.getElementById('upload-progress-container');
    const progressBar = document.getElementById('upload-progress-bar');
    const uploadFilename = document.getElementById('upload-filename');
    const uploadPercentage = document.getElementById('upload-percentage');

    // Load initial files
    loadFiles();

    // Event Listeners for Upload Area
    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    ['dragleave', 'dragend'].forEach(type => {
        dropZone.addEventListener(type, () => {
            dropZone.classList.remove('drag-over');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });

    refreshBtn.addEventListener('click', () => loadFiles());

    // Upload Files Batch Queue
    async function handleFiles(files) {
        for (let i = 0; i < files.length; i++) {
            await uploadFile(files[i]);
        }
        loadFiles();
    }

    function uploadFile(file) {
        return new Promise((resolve) => {
            const formData = new FormData();
            formData.append('file', file);

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/upload', true);

            progressContainer.classList.remove('hidden');
            uploadFilename.textContent = file.name;
            uploadPercentage.textContent = '0%';
            progressBar.style.width = '0%';

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    uploadPercentage.textContent = percent + '%';
                }
            };

            xhr.onload = () => {
                progressContainer.classList.add('hidden');
                if (xhr.status === 201) {
                    showToast(`Uploaded ${file.name}`);
                } else {
                    showToast('Upload failed', true);
                }
                resolve();
            };

            xhr.onerror = () => {
                progressContainer.classList.add('hidden');
                showToast('Network error during upload', true);
                resolve();
            };

            xhr.send(formData);
        });
    }

    // Fetch and render files
    async function loadFiles() {
        try {
            const res = await fetch('/api/files');
            const data = await res.json();

            storageStats.innerHTML = `<i class="fa-solid fa-hard-drive"></i> ${data.file_count} files (${data.total_storage})`;

            if (data.files.length === 0) {
                fileGrid.innerHTML = '';
                emptyState.classList.remove('hidden');
                return;
            }

            emptyState.classList.add('hidden');
            fileGrid.innerHTML = data.files.map(file => createFileCard(file)).join('');
        } catch (err) {
            console.error(err);
            showToast('Failed to load files', true);
        }
    }

    // Generate File Card Element
    function createFileCard(file) {
        const fileIcon = getFileIcon(file.mime_type, file.original_name);
        const shareUrl = `${window.location.origin}/s/${file.share_token}`;

        return `
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition-all duration-200 shadow-md">
                <div class="flex items-start gap-3">
                    <div class="p-3 bg-slate-800 rounded-lg text-indigo-400 text-xl flex-shrink-0">
                        <i class="${fileIcon}"></i>
                    </div>
                    <div class="overflow-hidden flex-1">
                        <h4 class="text-sm font-medium text-slate-200 truncate" title="${escapeHtml(file.original_name)}">
                            ${escapeHtml(file.original_name)}
                        </h4>
                        <p class="text-xs text-slate-500 mt-0.5">${file.file_size}</p>
                    </div>
                </div>

                <div class="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                    <!-- Mobile Direct Phone Download Link -->
                    <a href="/api/download/${file.id}" 
                       download="${escapeHtml(file.original_name)}"
                       class="flex-1 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-xs font-medium py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-all">
                        <i class="fa-solid fa-download"></i> Save to Storage
                    </a>
                    
                    <!-- Copy Share Link Button -->
                    <button onclick="copyShareLink('${shareUrl}')" title="Copy share link" 
                        class="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors">
                        <i class="fa-solid fa-link text-xs"></i>
                    </button>

                    <!-- Delete Button -->
                    <button onclick="deleteFile(${file.id})" title="Delete file" 
                        class="p-2 text-slate-500 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors">
                        <i class="fa-solid fa-trash text-xs"></i>
                    </button>
                </div>
            </div>
        `;
    }

    // Helper functions
    window.copyShareLink = (url) => {
        navigator.clipboard.writeText(url).then(() => {
            showToast('Share link copied to clipboard!');
        }).catch(() => {
            showToast('Failed to copy link', true);
        });
    };

    window.deleteFile = async (id) => {
        if (!confirm('Are you sure you want to delete this file?')) return;
        try {
            const res = await fetch(`/api/files/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast('File deleted');
                loadFiles();
            } else {
                showToast('Failed to delete file', true);
            }
        } catch (err) {
            showToast('Error deleting file', true);
        }
    };

    function getFileIcon(mimeType, filename) {
        const ext = filename.split('.').pop().toLowerCase();
        if (mimeType.startsWith('image/')) return 'fa-solid fa-image text-emerald-400';
        if (mimeType.startsWith('video/')) return 'fa-solid fa-video text-purple-400';
        if (mimeType.startsWith('audio/')) return 'fa-solid fa-music text-pink-400';
        if (mimeType.includes('pdf')) return 'fa-solid fa-file-pdf text-rose-400';
        if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return 'fa-solid fa-file-zipper text-amber-400';
        if (['js', 'py', 'html', 'css', 'json'].includes(ext)) return 'fa-solid fa-file-code text-cyan-400';
        return 'fa-solid fa-file text-slate-400';
    }

    function showToast(message, isError = false) {
        const toast = document.getElementById('toast');
        const toastMsg = document.getElementById('toast-message');
        
        toastMsg.textContent = message;
        toast.className = `fixed bottom-5 right-5 transform transition-all duration-300 px-4 py-3 rounded-xl shadow-xl flex items-center gap-3 z-50 text-white ${isError ? 'bg-rose-600' : 'bg-indigo-600'}`;
        
        toast.classList.remove('translate-y-20', 'opacity-0');
        
        setTimeout(() => {
            toast.classList.add('translate-y-20', 'opacity-0');
        }, 3000);
    }

    function escapeHtml(str) {
        return str.replace(/[&<>"']/g, (m) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m]));
    }
});