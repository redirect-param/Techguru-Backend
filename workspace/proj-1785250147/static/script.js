let globalProducts = [];
let globalCategories = [];
let globalSuppliers = [];

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadCategoriesAndSuppliers();
});

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    document.getElementById(`nav-${tabName}`).classList.add('active');

    if (tabName === 'dashboard') loadDashboard();
    if (tabName === 'products') loadProducts();
    if (tabName === 'categories') loadCategoriesAndSuppliers();
    if (tabName === 'logs') loadLogs();
}

async function loadDashboard() {
    const res = await fetch('/api/stats');
    const stats = await res.json();
    
    document.getElementById('stat-products').innerText = stats.total_products;
    document.getElementById('stat-lowstock').innerText = stats.low_stock_count;
    document.getElementById('stat-value').innerText = `$${stats.total_value.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
    document.getElementById('stat-movements').innerText = stats.total_movements;

    // Load low stock alerts
    const lowRes = await fetch('/api/notifications/low-stock');
    const lowItems = await lowRes.json();
    
    const alertBanner = document.getElementById('low-stock-alert');
    if (lowItems.length > 0) {
        alertBanner.classList.remove('hidden');
        document.getElementById('low-stock-msg').innerText = `${lowItems.length} product(s) are currently at or below minimum stock threshold.`;
    } else {
        alertBanner.classList.add('hidden');
    }

    const lowTable = document.getElementById('dash-low-stock-table');
    if (lowItems.length === 0) {
        lowTable.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-emerald-400 font-medium">All stock levels healthy!</td></tr>`;
    } else {
        lowTable.innerHTML = lowItems.map(item => `
            <tr>
                <td class="p-3 font-medium text-slate-200">${item.name} <span class="text-xs text-slate-500">(${item.sku})</span></td>
                <td class="p-3"><span class="px-2 py-0.5 rounded text-xs bg-rose-950 text-rose-300 border border-rose-800 font-bold">${item.quantity}</span></td>
                <td class="p-3 text-slate-400">${item.min_stock_level}</td>
                <td class="p-3 text-right">
                    <button onclick="openAdjustModal(${item.id}, '${item.name}')" class="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 rounded">Adjust</button>
                </td>
            </tr>
        `).join('');
    }

    // Load recent movements
    const moveRes = await fetch('/api/movements');
    const movements = await moveRes.json();
    const recentTable = document.getElementById('dash-recent-movements');
    
    recentTable.innerHTML = movements.slice(0, 5).map(m => `
        <tr>
            <td class="p-3 font-medium">${m.product_name}</td>
            <td class="p-3">${getTypeBadge(m.movement_type)}</td>
            <td class="p-3 font-semibold">${m.quantity}</td>
            <td class="p-3 text-xs text-slate-400">${new Date(m.timestamp).toLocaleDateString()}</td>
        </tr>
    `).join('');
}

async function loadProducts() {
    const res = await fetch('/api/products');
    globalProducts = await res.json();
    renderProductsTable(globalProducts);
}

function renderProductsTable(products) {
    const tbody = document.getElementById('products-table-body');
    if (products.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-500">No products found.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = products.map(p => {
        const isLow = p.quantity <= p.min_stock_level;
        return `
            <tr class="hover:bg-slate-800/40 transition">
                <td class="p-4 font-mono text-xs text-indigo-300">${p.sku}</td>
                <td class="p-4 font-semibold text-slate-200">${p.name}</td>
                <td class="p-4 text-slate-400">${p.category_name || '-'}</td>
                <td class="p-4 text-slate-400">${p.supplier_name || '-'}</td>
                <td class="p-4">
                    <span class="px-2.5 py-1 rounded-full text-xs font-bold ${isLow ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'bg-slate-700 text-slate-200'}">
                        ${p.quantity} ${isLow ? '⚠️' : ''}
                    </span>
                </td>
                <td class="p-4 font-medium">$${p.unit_price.toFixed(2)}</td>
                <td class="p-4 text-right space-x-2">
                    <button onclick="openAdjustModal(${p.id}, '${p.name}')" class="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded text-slate-200">Stock</button>
                    <button onclick="editProduct(${p.id})" class="text-xs bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 px-2 py-1 rounded">Edit</button>
                    <button onclick="deleteProduct(${p.id})" class="text-xs bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 px-2 py-1 rounded">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

function filterProducts() {
    const q = document.getElementById('product-search').value.toLowerCase();
    const filtered = globalProducts.filter(p => 
        p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
    );
    renderProductsTable(filtered);
}

async function loadCategoriesAndSuppliers() {
    const [cRes, sRes] = await Promise.all([fetch('/api/categories'), fetch('/api/suppliers')]);
    globalCategories = await cRes.json();
    globalSuppliers = await sRes.json();

    document.getElementById('categories-table-body').innerHTML = globalCategories.map(c => `
        <tr>
            <td class="p-3 font-semibold text-slate-200">${c.name}</td>
            <td class="p-3 text-slate-400 text-xs">${c.description || '-'}</td>
            <td class="p-3 text-right">
                <button onclick="deleteCategory(${c.id})" class="text-xs text-rose-400 hover:underline">Delete</button>
            </td>
        </tr>
    `).join('');

    document.getElementById('suppliers-table-body').innerHTML = globalSuppliers.map(s => `
        <tr>
            <td class="p-3 font-semibold text-slate-200">${s.name}</td>
            <td class="p-3 text-slate-400 text-xs">${s.contact_email || '-'}</td>
            <td class="p-3 text-right">
                <button onclick="deleteSupplier(${s.id})" class="text-xs text-rose-400 hover:underline">Delete</button>
            </td>
        </tr>
    `).join('');
}

async function loadLogs() {
    const res = await fetch('/api/movements');
    const logs = await res.json();
    document.getElementById('logs-table-body').innerHTML = logs.map(l => `
        <tr class="hover:bg-slate-800/40">
            <td class="p-4 text-xs text-slate-400">${new Date(l.timestamp).toLocaleString()}</td>
            <td class="p-4 font-semibold text-slate-200">${l.product_name}</td>
            <td class="p-4 font-mono text-xs text-indigo-300">${l.sku}</td>
            <td class="p-4">${getTypeBadge(l.movement_type)}</td>
            <td class="p-4 font-bold text-slate-200">${l.quantity}</td>
            <td class="p-4 text-xs text-slate-400">${l.note || '-'}</td>
        </tr>
    `).join('');
}

function getTypeBadge(type) {
    if (type === 'IN') return `<span class="px-2 py-0.5 rounded text-xs bg-emerald-950 text-emerald-400 border border-emerald-800">IN</span>`;
    if (type === 'OUT') return `<span class="px-2 py-0.5 rounded text-xs bg-rose-950 text-rose-400 border border-rose-800">OUT</span>`;
    return `<span class="px-2 py-0.5 rounded text-xs bg-amber-950 text-amber-400 border border-amber-800">ADJUST</span>`;
}

// Modal Helpers
function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

function openProductModal(isEdit = false) {
    populateDropdowns();
    document.getElementById('product-modal-title').innerText = isEdit ? 'Edit Product' : 'Add Product';
    document.getElementById('product-qty').disabled = isEdit;
    document.getElementById('product-modal').classList.remove('hidden');
}

function populateDropdowns() {
    const cSelect = document.getElementById('product-category');
    const sSelect = document.getElementById('product-supplier');
    
    cSelect.innerHTML = '<option value="">None</option>' + globalCategories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    sSelect.innerHTML = '<option value="">None</option>' + globalSuppliers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
}

async function saveProduct(e) {
    e.preventDefault();
    const id = document.getElementById('product-id').value;
    const data = {
        name: document.getElementById('product-name').value,
        sku: document.getElementById('product-sku').value,
        unit_price: parseFloat(document.getElementById('product-price').value),
        category_id: document.getElementById('product-category').value || null,
        supplier_id: document.getElementById('product-supplier').value || null,
        quantity: parseInt(document.getElementById('product-qty').value || 0),
        min_stock_level: parseInt(document.getElementById('product-min').value || 5)
    };

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/products/${id}` : '/api/products';

    const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (res.ok) {
        closeModal('product-modal');
        document.getElementById('product-form').reset();
        document.getElementById('product-id').value = '';
        loadProducts();
    } else {
        const err = await res.json();
        alert(err.error || 'Failed to save product');
    }
}

async function editProduct(id) {
    const res = await fetch(`/api/products/${id}`);
    const p = await res.json();
    
    openProductModal(true);
    document.getElementById('product-id').value = p.id;
    document.getElementById('product-name').value = p.name;
    document.getElementById('product-sku').value = p.sku;
    document.getElementById('product-price').value = p.unit_price;
    document.getElementById('product-category').value = p.category_id || '';
    document.getElementById('product-supplier').value = p.supplier_id || '';
    document.getElementById('product-qty').value = p.quantity;
    document.getElementById('product-min').value = p.min_stock_level;
}

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;
    await fetch(`/api/products/${id}`, { method: 'DELETE' });
    loadProducts();
}

function openAdjustModal(id, name) {
    document.getElementById('adjust-product-id').value = id;
    document.getElementById('adjust-product-name').innerText = `Adjust stock for: ${name}`;
    document.getElementById('adjust-form').reset();
    document.getElementById('adjust-modal').classList.remove('hidden');
}

async function saveStockAdjustment(e) {
    e.preventDefault();
    const id = document.getElementById('adjust-product-id').value;
    const data = {
        movement_type: document.getElementById('adjust-type').value,
        quantity: parseInt(document.getElementById('adjust-qty').value),
        note: document.getElementById('adjust-note').value
    };

    const res = await fetch(`/api/products/${id}/adjust`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (res.ok) {
        closeModal('adjust-modal');
        loadProducts();
        loadDashboard();
    } else {
        const err = await res.json();
        alert(err.error || 'Adjustment failed');
    }
}

function openCategoryModal() { document.getElementById('category-modal').classList.remove('hidden'); }
function openSupplierModal() { document.getElementById('supplier-modal').classList.remove('hidden'); }

async function saveCategory(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('cat-name').value,
        description: document.getElementById('cat-desc').value
    };
    await fetch('/api/categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    closeModal('category-modal');
    loadCategoriesAndSuppliers();
}

async function deleteCategory(id) {
    if (!confirm('Delete category?')) return;
    await fetch(`/api/categories/${id}`, { method: 'DELETE' });
    loadCategoriesAndSuppliers();
}

async function saveSupplier(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('sup-name').value,
        contact_email: document.getElementById('sup-email').value,
        phone: document.getElementById('sup-phone').value
    };
    await fetch('/api/suppliers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    closeModal('supplier-modal');
    loadCategoriesAndSuppliers();
}

async function deleteSupplier(id) {
    if (!confirm('Delete supplier?')) return;
    await fetch(`/api/suppliers/${id}`, { method: 'DELETE' });
    loadCategoriesAndSuppliers();
}