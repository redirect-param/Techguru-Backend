function switchTab(type) {
    const emailTabBtn = document.getElementById('tab-btn-email');
    const voucherTabBtn = document.getElementById('tab-btn-voucher');
    const emailForm = document.getElementById('form-email');
    const voucherForm = document.getElementById('form-voucher');

    if (type === 'email') {
        emailTabBtn.classList.add('active');
        voucherTabBtn.classList.remove('active');
        emailForm.classList.add('active');
        voucherForm.classList.remove('active');
    } else {
        voucherTabBtn.classList.add('active');
        emailTabBtn.classList.remove('active');
        voucherForm.classList.add('active');
        emailForm.classList.remove('active');
    }
}

async function checkVoucher() {
    const voucherInput = document.getElementById('voucher_code');
    const statusMsg = document.getElementById('voucher-status-msg');
    const code = voucherInput.value.trim();

    if (!code) {
        statusMsg.style.color = '#ef4444';
        statusMsg.innerText = 'Please enter a voucher code.';
        return;
    }

    statusMsg.style.color = '#64748b';
    statusMsg.innerText = 'Validating code...';

    try {
        const response = await fetch(`/api/validate-voucher/${encodeURIComponent(code)}`);
        const data = await response.json();

        if (data.valid) {
            statusMsg.style.color = '#10b981';
            statusMsg.innerText = data.message;
        } else {
            statusMsg.style.color = '#ef4444';
            statusMsg.innerText = data.message;
        }
    } catch (err) {
        statusMsg.style.color = '#ef4444';
        statusMsg.innerText = 'Error validating voucher code.';
    }
}