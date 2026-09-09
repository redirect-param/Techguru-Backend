// State Management
let currentUser = null;
let currentCategory = "All";
let activeCheckoutRequestId = null;
let stkPollInterval = null;

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    checkCurrentUser();
    loadProducts();
    updateCart();
});

// Toast Helper
function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.style.display = "block";
    setTimeout(() => {
        toast.style.display = "none";
    }, 3000);
}

// User Authentication API Integration
async function checkCurrentUser() {
    try {
        const res = await fetch("/api/me");
        const data = await res.json();
        if (data.user) {
            currentUser = data.user;
            document.getElementById("navUsername").textContent = currentUser.name;
            document.getElementById("authLinks").style.display = "none";
            document.getElementById("userLinks").style.display = "block";
            
            if (currentUser.role === "admin") {
                document.getElementById("adminTabLink").style.display = "block";
            }
        } else {
            currentUser = null;
            document.getElementById("navUsername").textContent = "Account";
            document.getElementById("authLinks").style.display = "block";
            document.getElementById("userLinks").style.display = "none";
            document.getElementById("adminTabLink").style.display = "none";
        }
    } catch (err) {
        console.error("Auth status check failed", err);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const phone = document.getElementById("loginPhone").value;
    const password = document.getElementById("loginPassword").value;

    try {
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone, password })
        });
        const data = await res.json();

        if (res.ok) {
            showToast("Login successful!");
            closeModal("authModal");
            checkCurrentUser();
            updateCart();
        } else {
            showToast(data.error || "Login failed");
        }
    } catch (err) {
        showToast("Error connecting to server");
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById("regName").value;
    const phone = document.getElementById("regPhone").value;
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;

    try {
        const res = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, phone, email, password })
        });
        const data = await res.json();

        if (res.ok) {
            showToast("Account created successfully!");
            closeModal("authModal");
            checkCurrentUser();
        } else {
            showToast(data.error || "Registration failed");
        }
    } catch (err) {
        showToast("Error creating account");
    }
}

async function logout() {
    await fetch("/api/logout", { method: "POST" });
    currentUser = null;
    checkCurrentUser();
    showSection("shop");
    showToast("Logged out");
}

// UI Navigation and Modals
function toggleUserDropdown() {
    const dropdown = document.getElementById("userDropdown");
    dropdown.style.display = dropdown.style.display === "flex" ? "none" : "flex";
}

function openModal(id) {
    document.getElementById(id).classList.add("open");
}

function closeModal(id) {
    document.getElementById(id).classList.remove("open");
    if (stkPollInterval) clearInterval(stkPollInterval);
}

function switchAuthTab(tab) {
    if (tab === 'login') {
        document.getElementById('loginForm').classList.remove('hidden');
        document.getElementById('registerForm').classList.add('hidden');
        document.getElementById('loginTabBtn').classList.add('active');
        document.getElementById('registerTabBtn').classList.remove('active');
    } else {
        document.getElementById('loginForm').classList.add('hidden');
        document.getElementById('registerForm').classList.remove('hidden');
        document.getElementById('loginTabBtn').classList.remove('active');
        document.getElementById('registerTabBtn').classList.add('active');
    }
}

function showSection(section) {
    document.getElementById("shopSection").className = "hidden-section";
    document.getElementById("ordersSection").className = "hidden-section";
    document.getElementById("adminSection").className = "hidden-section";

    if (section === 'shop') document.getElementById("shopSection").className = "active-section";
    if (section === 'orders') {
        document.getElementById("ordersSection").className = "active-section";
        loadUserOrders();
    }
    if (section === 'admin') {
        document.getElementById("adminSection").className = "active-section";
        loadAdminOrders();
    }
    document.getElementById("userDropdown").style.display = "none";
}

function scrollToCatalog() {
    document.getElementById("catalogHead").scrollIntoView({ behavior: 'smooth' });
}

// Product Management
async function loadProducts() {
    try {
        const res = await fetch(`/api/products?category=${currentCategory}`);
        const data = await res.json();
        renderProducts(data.products);
    } catch (err) {
        console.error("Failed to fetch products", err);
    }
}

function renderProducts(products) {
    const grid = document.getElementById("productGrid");
    grid.innerHTML = "";

    if (products.length === 0) {
        grid.innerHTML = `<p>No products found in this category.</p>`;
        return;
    }

    products.forEach(p => {
        const card = document.createElement("div");
        card.className = "product-card";
        card.innerHTML = `
            <img src="${p.image_url}" class="product-img" alt="${p.name}">
            <div class="product-details">
                <span class="category-tag">${p.category}</span>
                <h3 class="product-title">${p.name}</h3>
                <p class="product-desc">${p.description}</p>
                <div class="product-price-row">
                    <span class="price">KES ${p.price.toLocaleString()}</span>
                    <button class="btn-primary" onclick="addToCart(${p.id})"><i class="fa-solid fa-cart-plus"></i> Add</button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function filterCategory(cat) {
    currentCategory = cat;
    document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
    event.target.classList.add("active");
    loadProducts();
}

function filterProducts() {
    const query = document.getElementById("searchInput").value.toLowerCase();
    const cards = document.querySelectorAll(".product-card");
    cards.forEach(card => {
        const title = card.querySelector(".product-title").textContent.toLowerCase();
        const desc = card.querySelector(".product-desc").textContent.toLowerCase();
        if (title.includes(query) || desc.includes(query)) {
            card.style.display = "flex";
        } else {
            card.style.display = "none";
        }
    });
}

// Shopping Cart Functions
function toggleCartDrawer() {
    document.getElementById("cartDrawer").classList.toggle("open");
    document.getElementById("cartOverlay").classList.toggle("open");
}

async function addToCart(productId) {
    if (!currentUser) {
        openModal("authModal");
        showToast("Please login to add items to cart");
        return;
    }

    try {
        const res = await fetch("/api/cart", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_id: productId, quantity: 1 })
        });
        if (res.ok) {
            showToast("Added to cart");
            updateCart();
        }
    } catch (err) {
        showToast("Failed to add to cart");
    }
}

async function updateCart() {
    if (!currentUser) {
        document.getElementById("cartCount").textContent = "0";
        document.getElementById("cartItemsContainer").innerHTML = "<p>Please login to view cart.</p>";
        document.getElementById("cartTotalAmount").textContent = "KES 0";
        return;
    }

    try {
        const res = await fetch("/api/cart");
        if (!res.ok) return;
        const data = await res.json();
        
        const container = document.getElementById("cartItemsContainer");
        container.innerHTML = "";

        let count = 0;
        data.cart.forEach(item => {
            count += item.quantity;
            const row = document.createElement("div");
            row.className = "cart-item";
            row.innerHTML = `
                <img src="${item.image_url}" alt="${item.name}">
                <div class="cart-item-details">
                    <h4>${item.name}</h4>
                    <p>KES ${item.price.toLocaleString()}</p>
                    <div class="qty-controls">
                        <button onclick="changeQty(${item.cart_id}, ${item.quantity - 1})">-</button>
                        <span>${item.quantity}</span>
                        <button onclick="changeQty(${item.cart_id}, ${item.quantity + 1})">+</button>
                    </div>
                </div>
            `;
            container.appendChild(row);
        });

        document.getElementById("cartCount").textContent = count;
        document.getElementById("cartTotalAmount").textContent = `KES ${data.total.toLocaleString()}`;
    } catch (err) {
        console.error("Cart update failed", err);
    }
}

async function changeQty(cartId, newQty) {
    await fetch("/api/cart", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cart_id: cartId, quantity: newQty })
    });
    updateCart();
}

// Checkout & M-Pesa Express Flow
async function startCheckout() {
    if (!currentUser) {
        openModal("authModal");
        return;
    }

    const res = await fetch("/api/cart");
    const data = await res.json();

    if (!data.cart || data.cart.length === 0) {
        showToast("Your cart is empty!");
        return;
    }

    toggleCartDrawer();
    document.getElementById("mpesaTotalBadge").textContent = `KES ${data.total.toLocaleString()}`;
    document.getElementById("mpesaPhone").value = currentUser.phone;
    
    // Reset Checkout Modal Steps
    document.getElementById("checkoutStep1").classList.remove("hidden");
    document.getElementById("checkoutStep2").classList.add("hidden");
    document.getElementById("checkoutStep3").classList.add("hidden");
    
    openModal("checkoutModal");
}

async function triggerMpesaPush() {
    const phone = document.getElementById("mpesaPhone").value;
    const location = document.getElementById("deliveryLocation").value;

    if (!phone) {
        showToast("Enter a valid M-Pesa phone number");
        return;
    }

    try {
        const res = await fetch("/api/checkout/mpesa", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone, delivery_location: location })
        });
        const data = await res.json();

        if (res.ok) {
            activeCheckoutRequestId = data.checkout_request_id;
            
            // Switch to Step 2 (Processing view)
            document.getElementById("checkoutStep1").classList.add("hidden");
            document.getElementById("checkoutStep2").classList.remove("hidden");

            // Start Polling Payment Status
            startStkPolling(activeCheckoutRequestId);
        } else {
            showToast(data.error || "M-Pesa STK Push failed");
        }
    } catch (err) {
        showToast("Server error during checkout");
    }
}

function startStkPolling(checkoutId) {
    if (stkPollInterval) clearInterval(stkPollInterval);

    stkPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/mpesa/stk_status/${checkoutId}`);
            const data = await res.json();

            if (data.status === "PAID") {
                clearInterval(stkPollInterval);
                document.getElementById("checkoutStep2").classList.add("hidden");
                document.getElementById("checkoutStep3").classList.remove("hidden");
                document.getElementById("receiptCode").textContent = data.receipt;
                updateCart();
            }
        } catch (err) {
            console.error("STK poll error", err);
        }
    }, 3000);
}

async function simulatePaymentCompletion() {
    if (!activeCheckoutRequestId) return;

    try {
        const res = await fetch("/api/mpesa/simulate_payment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ checkout_request_id: activeCheckoutRequestId })
        });
        const data = await res.json();

        if (res.ok) {
            showToast("Simulation payment verified!");
        }
    } catch (err) {
        showToast("Simulation failed");
    }
}

function finishCheckout() {
    closeModal("checkoutModal");
    showSection("orders");
}

// User Orders Display
async function loadUserOrders() {
    try {
        const res = await fetch("/api/orders");
        const data = await res.json();
        
        const list = document.getElementById("ordersList");
        list.innerHTML = "";

        if (!data.orders || data.orders.length === 0) {
            list.innerHTML = "<p>No orders found yet.</p>";
            return;
        }

        data.orders.forEach(o => {
            const card = document.createElement("div");
            card.className = "order-card";
            
            let itemsHtml = o.items.map(i => `
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-top:5px;">
                    <span>${i.name} x${i.quantity}</span>
                    <span>KES ${(i.price * i.quantity).toLocaleString()}</span>
                </div>
            `).join('');

            card.innerHTML = `
                <div class="order-header">
                    <div>
                        <strong>Order #${o.id}</strong> - <small>${o.created_at}</small>
                        <br><small>Agent Location: ${o.delivery_location}</small>
                    </div>
                    <div>
                        <span class="order-badge ${o.payment_status}">${o.payment_status}</span>
                    </div>
                </div>
                <div>${itemsHtml}</div>
                <div style="margin-top:10px; font-weight:700; text-align:right;">
                    Total: KES ${o.total_amount.toLocaleString()} 
                    ${o.mpesa_receipt ? `<br><small style="color:var(--mpesa-green); font-weight:400;">Receipt: ${o.mpesa_receipt}</small>` : ''}
                </div>
            `;
            list.appendChild(card);
        });
    } catch (err) {
        console.error("Failed to load orders", err);
    }
}

// Admin Operations
async function handleAddProduct(e) {
    e.preventDefault();
    const productData = {
        name: document.getElementById("prodName").value,
        category: document.getElementById("prodCategory").value,
        price: document.getElementById("prodPrice").value,
        stock: document.getElementById("prodStock").value,
        image_url: document.getElementById("prodImage").value || undefined,
        description: document.getElementById("prodDesc").value
    };

    try {
        const res = await fetch("/api/products", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(productData)
        });

        if (res.ok) {
            showToast("Product created!");
            document.getElementById("addProductForm").reset();
            loadProducts();
        } else {
            showToast("Failed to add product");
        }
    } catch (err) {
        showToast("Error creating product");
    }
}

async function loadAdminOrders() {
    try {
        const res = await fetch("/api/admin/orders");
        const data = await res.json();
        
        const list = document.getElementById("adminOrdersList");
        list.innerHTML = "";

        if (!data.orders || data.orders.length === 0) {
            list.innerHTML = "<p>No customer orders placed yet.</p>";
            return;
        }

        data.orders.forEach(o => {
            const card = document.createElement("div");
            card.style.borderBottom = "1px solid #e2e8f0";
            card.style.padding = "10px 0";
            card.innerHTML = `
                <div><strong>Order #${o.id}</strong> by ${o.customer_name} (${o.phone})</div>
                <div>Amount: KES ${o.total_amount.toLocaleString()} | Status: <strong style="color:var(--primary);">${o.payment_status}</strong></div>
                <small>Location: ${o.delivery_location}</small>
            `;
            list.appendChild(card);
        });
    } catch (err) {
        console.error("Failed to load admin orders", err);
    }
}