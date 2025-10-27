/**
 * Warehouse Map Visualization
 * SmartWare Pro - Warehouse Management System
 */

class WarehouseMap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.svg = null;
        this.products = [];
        this.tooltip = null;
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return;

        try {
            // Create SVG if it doesn't exist
            this.svg = document.getElementById('warehouse-map');
            if (!this.svg) {
                console.error('Warehouse map SVG not found');
                return;
            }

            // Create tooltip
            this.createTooltip();

            // Load warehouse layout
            this.createWarehouseLayout();

            // Load products and place markers
            await this.loadProducts();

            this.initialized = true;
            console.log('Warehouse map initialized successfully');
        } catch (error) {
            console.error('Error initializing warehouse map:', error);
        }
    }

    createWarehouseLayout() {
        // Clear existing content
        this.svg.innerHTML = '';

        // Create warehouse structure
        const layout = this.createLayoutSVG();
        this.svg.innerHTML = layout;
    }

    createLayoutSVG() {
        return `
            <!-- Warehouse outer walls -->
            <rect x="50" y="50" width="800" height="600" 
                  fill="none" stroke="#333" stroke-width="4"/>
            
            <!-- Storage areas -->
            <g class="storage-areas">
                <!-- Area A -->
                <rect x="100" y="100" width="150" height="200" 
                      fill="#e3f2fd" stroke="#1976d2" stroke-width="2"/>
                <text x="175" y="120" text-anchor="middle" font-size="14" font-weight="bold">Area A</text>
                
                <!-- Area B -->
                <rect x="300" y="100" width="150" height="200" 
                      fill="#f3e5f5" stroke="#7b1fa2" stroke-width="2"/>
                <text x="375" y="120" text-anchor="middle" font-size="14" font-weight="bold">Area B</text>
                
                <!-- Area C -->
                <rect x="500" y="100" width="150" height="200" 
                      fill="#e8f5e8" stroke="#388e3c" stroke-width="2"/>
                <text x="575" y="120" text-anchor="middle" font-size="14" font-weight="bold">Area C</text>
                
                <!-- Area D -->
                <rect x="700" y="100" width="100" height="200" 
                      fill="#fff3e0" stroke="#f57c00" stroke-width="2"/>
                <text x="750" y="120" text-anchor="middle" font-size="14" font-weight="bold">Area D</text>
                
                <!-- Area E -->
                <rect x="100" y="350" width="200" height="150" 
                      fill="#fce4ec" stroke="#c2185b" stroke-width="2"/>
                <text x="200" y="370" text-anchor="middle" font-size="14" font-weight="bold">Area E</text>
                
                <!-- Area F -->
                <rect x="350" y="350" width="200" height="150" 
                      fill="#f1f8e9" stroke="#689f38" stroke-width="2"/>
                <text x="450" y="370" text-anchor="middle" font-size="14" font-weight="bold">Area F</text>
                
                <!-- Area G -->
                <rect x="600" y="350" width="200" height="150" 
                      fill="#e0f2f1" stroke="#00796b" stroke-width="2"/>
                <text x="700" y="370" text-anchor="middle" font-size="14" font-weight="bold">Area G</text>
            </g>
            
            <!-- Aisles -->
            <g class="aisles">
                <line x1="50" y1="325" x2="850" y2="325" stroke="#ccc" stroke-width="20"/>
                <line x1="275" y1="50" x2="275" y2="650" stroke="#ccc" stroke-width="15"/>
                <line x1="475" y1="50" x2="475" y2="650" stroke="#ccc" stroke-width="15"/>
                <line x1="675" y1="50" x2="675" y2="650" stroke="#ccc" stroke-width="15"/>
            </g>
            
            <!-- Dock doors -->
            <g class="dock-doors">
                <rect x="30" y="200" width="20" height="60" fill="#ff5722"/>
                <text x="25" y="240" font-size="10" fill="#333">Dock 1</text>
                
                <rect x="30" y="300" width="20" height="60" fill="#ff5722"/>
                <text x="25" y="340" font-size="10" fill="#333">Dock 2</text>
                
                <rect x="30" y="400" width="20" height="60" fill="#ff5722"/>
                <text x="25" y="440" font-size="10" fill="#333">Dock 3</text>
            </g>
            
            <!-- Office area -->
            <rect x="700" y="550" width="150" height="100" 
                  fill="#f5f5f5" stroke="#666" stroke-width="2"/>
            <text x="775" y="570" text-anchor="middle" font-size="12" font-weight="bold">Office</text>
            
            <!-- Legend -->
            <g class="legend" transform="translate(50, 550)">
                <rect x="0" y="0" width="200" height="80" fill="white" stroke="#ccc" stroke-width="1"/>
                <text x="10" y="20" font-size="12" font-weight="bold">Legend:</text>
                <circle cx="20" cy="35" r="4" fill="#28a745"/>
                <text x="35" y="40" font-size="10">Normal Stock</text>
                <circle cx="20" cy="50" r="4" fill="#ffc107"/>
                <text x="35" y="55" font-size="10">Low Stock (≤5)</text>
                <circle cx="20" cy="65" r="4" fill="#dc3545"/>
                <text x="35" y="70" font-size="10">Out of Stock</text>
                <circle cx="120" cy="35" r="4" fill="#007bff"/>
                <text x="135" y="40" font-size="10">Selected</text>
            </g>
        `;
    }

    async loadProducts() {
        try {
            const response = await fetch('/api/products_map');
            if (!response.ok) {
                throw new Error('Failed to load products');
            }
            
            this.products = await response.json();
            this.placeProductMarkers();
        } catch (error) {
            console.error('Error loading products:', error);
            // Show error in map
            this.showMapError('Failed to load product locations');
        }
    }

    placeProductMarkers() {
        // Remove existing markers
        const existingMarkers = this.svg.querySelectorAll('.product-marker');
        existingMarkers.forEach(marker => marker.remove());

        // Add new markers
        this.products.forEach(product => {
            this.addProductMarker(product);
        });
    }

    addProductMarker(product) {
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        marker.classList.add('product-marker');
        marker.classList.add('map-marker');
        
        // Determine marker color based on stock level
        let color = '#28a745'; // Green for normal stock
        if (product.quantity === 0) {
            color = '#dc3545'; // Red for out of stock
        } else if (product.low_stock) {
            color = '#ffc107'; // Yellow for low stock
        }

        // Create marker elements
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', product.x);
        circle.setAttribute('cy', product.y);
        circle.setAttribute('r', '8');
        circle.setAttribute('fill', color);
        circle.setAttribute('stroke', '#fff');
        circle.setAttribute('stroke-width', '2');

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', product.x);
        text.setAttribute('y', product.y + 3);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '10');
        text.setAttribute('font-weight', 'bold');
        text.setAttribute('fill', '#fff');
        text.textContent = product.id;

        marker.appendChild(circle);
        marker.appendChild(text);

        // Add event listeners
        marker.addEventListener('mouseenter', (e) => {
            this.showTooltip(e, product);
            marker.style.transform = 'scale(1.2)';
            marker.style.transformOrigin = `${product.x}px ${product.y}px`;
        });

        marker.addEventListener('mouseleave', () => {
            this.hideTooltip();
            marker.style.transform = 'scale(1)';
        });

        marker.addEventListener('click', () => {
            this.selectProduct(product);
        });

        this.svg.appendChild(marker);
    }

    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'map-tooltip';
        document.body.appendChild(this.tooltip);
    }

    showTooltip(event, product) {
        if (!this.tooltip) return;

        const stockStatus = product.quantity === 0 ? 'Out of Stock' : 
                           product.low_stock ? 'Low Stock' : 'In Stock';
        
        this.tooltip.innerHTML = `
            <div><strong>${product.name}</strong></div>
            <div>Quantity: ${product.quantity}</div>
            <div>Location: ${product.location}</div>
            <div>Status: <span style="color: ${this.getStatusColor(product)}">${stockStatus}</span></div>
        `;

        // Position tooltip
        const rect = this.container.getBoundingClientRect();
        const tooltipX = event.clientX - rect.left + 10;
        const tooltipY = event.clientY - rect.top - 10;

        this.tooltip.style.left = tooltipX + 'px';
        this.tooltip.style.top = tooltipY + 'px';
        this.tooltip.classList.add('show');
    }

    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.classList.remove('show');
        }
    }

    getStatusColor(product) {
        if (product.quantity === 0) return '#dc3545';
        if (product.low_stock) return '#ffc107';
        return '#28a745';
    }

    selectProduct(product) {
        // Redirect to product detail page
        window.location.href = `/product/${product.id}`;
    }

    showMapError(message) {
        const errorText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        errorText.setAttribute('x', '450');
        errorText.setAttribute('y', '350');
        errorText.setAttribute('text-anchor', 'middle');
        errorText.setAttribute('font-size', '16');
        errorText.setAttribute('fill', '#dc3545');
        errorText.textContent = message;
        
        this.svg.appendChild(errorText);
    }

    refresh() {
        this.loadProducts();
    }
}

// Global map instance
let warehouseMap = null;

// Initialize warehouse map
function initializeWarehouseMap() {
    if (!warehouseMap) {
        warehouseMap = new WarehouseMap('warehouse-map-container');
    }
    warehouseMap.initialize();
}

// Refresh map data
function refreshWarehouseMap() {
    if (warehouseMap) {
        warehouseMap.refresh();
    }
}

// Export for global use
window.warehouseMap = {
    initialize: initializeWarehouseMap,
    refresh: refreshWarehouseMap
};
