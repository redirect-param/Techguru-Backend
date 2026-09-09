document.addEventListener("DOMContentLoaded", () => {
    fetchSubjects();
    fetchStaff();
    fetchFees();
    fetchNews();
});

// Fetch Subjects
async function fetchSubjects() {
    try {
        const response = await fetch('/api/subjects');
        const subjects = await response.json();
        const grid = document.getElementById('subjects-grid');
        grid.innerHTML = '';

        subjects.forEach(subj => {
            grid.innerHTML += `
                <div class="card">
                    <span class="card-tag">${subj.code} • ${subj.department}</span>
                    <h3>${subj.name}</h3>
                    <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 8px;">${subj.description}</p>
                </div>
            `;
        });
    } catch (err) {
        console.error("Failed loading subjects", err);
    }
}

// Fetch Staff
async function fetchStaff() {
    try {
        const response = await fetch('/api/staff');
        const staff = await response.json();
        const grid = document.getElementById('staff-grid');
        grid.innerHTML = '';

        staff.forEach(person => {
            grid.innerHTML += `
                <div class="card staff-card">
                    <img src="${person.image_url}" alt="${person.name}" class="staff-avatar">
                    <h4>${person.name}</h4>
                    <div class="staff-role">${person.role}</div>
                    <div class="staff-email">${person.department} • ${person.email}</div>
                </div>
            `;
        });
    } catch (err) {
        console.error("Failed loading staff", err);
    }
}

// Fetch Fee Structure
async function fetchFees() {
    try {
        const response = await fetch('/api/fees');
        const fees = await response.json();
        const tbody = document.getElementById('fee-table-body');
        tbody.innerHTML = '';

        fees.forEach(f => {
            tbody.innerHTML += `
                <tr>
                    <td><strong>${f.form_level}</strong></td>
                    <td>KSh ${f.tuition.toLocaleString()}</td>
                    <td>KSh ${f.boarding.toLocaleString()}</td>
                    <td>KSh ${f.activity_fee.toLocaleString()}</td>
                    <td>KSh ${f.development.toLocaleString()}</td>
                    <td><strong>KSh ${f.total.toLocaleString()}</strong></td>
                </tr>
            `;
        });
    } catch (err) {
        console.error("Failed loading fees", err);
    }
}

// Fetch News
async function fetchNews() {
    try {
        const response = await fetch('/api/news');
        const news = await response.json();
        const grid = document.getElementById('news-grid');
        grid.innerHTML = '';

        news.forEach(item => {
            grid.innerHTML += `
                <div class="card">
                    <span class="card-tag">${item.category} • ${item.date}</span>
                    <h3>${item.title}</h3>
                    <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 8px;">${item.content}</p>
                </div>
            `;
        });
    } catch (err) {
        console.error("Failed loading news", err);
    }
}

// Handle Admission Submission
async function handleAdmissionSubmit(e) {
    e.preventDefault();
    const resEl = document.getElementById('admissionResponse');
    resEl.className = 'form-response';
    resEl.style.display = 'none';

    const payload = {
        applicant_name: document.getElementById('applicant_name').value,
        parent_email: document.getElementById('parent_email').value,
        parent_phone: document.getElementById('parent_phone').value,
        target_form: document.getElementById('target_form').value,
        kcpe_marks: parseInt(document.getElementById('kcpe_marks').value)
    };

    try {
        const res = await fetch('/api/admissions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            resEl.textContent = data.message;
            resEl.classList.add('success');
            document.getElementById('admissionForm').reset();
        } else {
            resEl.textContent = data.message || "Failed to submit application.";
            resEl.classList.add('error');
        }
    } catch (err) {
        resEl.textContent = "Server connection error.";
        resEl.classList.add('error');
    }
}

// Student Portal Modal Functions
function openPortalModal() {
    document.getElementById('portalModal').classList.add('active');
}

function closePortalModal() {
    document.getElementById('portalModal').classList.remove('active');
    document.getElementById('portalResult').style.display = 'none';
}

async function handlePortalLookup(e) {
    e.preventDefault();
    const regNo = document.getElementById('portalRegNo').value;
    const resultBox = document.getElementById('portalResult');

    try {
        const res = await fetch('/api/student/portal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reg_no: regNo })
        });
        const data = await res.json();

        resultBox.style.display = 'block';
        if (data.success) {
            const s = data.student;
            resultBox.innerHTML = `
                <div style="color: #10b981; font-weight:700; margin-bottom:8px;">Record Found</div>
                <p><strong>Name:</strong> ${s.full_name}</p>
                <p><strong>Class:</strong> ${s.form} (${s.stream})</p>
                <p><strong>Reg No:</strong> ${s.reg_no}</p>
                <p><strong>Fee Balance:</strong> <span style="color: ${s.fee_balance > 0 ? '#ef4444' : '#10b981'}; font-weight:700;">KSh ${s.fee_balance.toLocaleString()}</span></p>
            `;
        } else {
            resultBox.innerHTML = `<div style="color: #ef4444;">${data.message}</div>`;
        }
    } catch (err) {
        resultBox.style.display = 'block';
        resultBox.innerHTML = `<div style="color: #ef4444;">Network or server error.</div>`;
    }
}