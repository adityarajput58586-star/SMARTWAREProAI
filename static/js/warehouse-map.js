/**
 * Warehouse Map Visualization
 * Displays warehouse sections dynamically based on database configuration
 */

function initializeWarehouseMap() {
    const mapContainer = document.getElementById('warehouse-map');
    if (!mapContainer) return;
    
    // Fetch warehouse data
    fetch('/api/warehouse_map')
        .then(response => response.json())
        .then(data => {
            renderWarehouseMap(data);
        })
        .catch(error => {
            console.error('Error loading warehouse map:', error);
            mapContainer.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#999">Error loading warehouse map</text>';
        });
}

function renderWarehouseMap(data) {
    const mapContainer = document.getElementById('warehouse-map');
    if (!mapContainer) return;
    
    const sections = data.sections;
    const config = data.config;
    
    // Clear existing content
    mapContainer.innerHTML = '';
    
    // Calculate map dimensions
    let maxX = 0, maxY = 0;
    sections.forEach(section => {
        const rightEdge = section.x + section.width;
        const bottomEdge = section.y + section.height;
        if (rightEdge > maxX) maxX = rightEdge;
        if (bottomEdge > maxY) maxY = bottomEdge;
    });
    
    // Add padding
    const padding = 50;
    const mapWidth = maxX + padding * 2;
    const mapHeight = maxY + padding * 2;
    
    // Set viewBox
    mapContainer.setAttribute('viewBox', `0 0 ${mapWidth} ${mapHeight}`);
    
    // Add background
    const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    background.setAttribute('width', mapWidth);
    background.setAttribute('height', mapHeight);
    background.setAttribute('fill', '#f8f9fa');
    mapContainer.appendChild(background);
    
    // Add grid pattern
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const pattern = document.createElementNS('http://www.w3.org/2000/svg', 'pattern');
    pattern.setAttribute('id', 'grid');
    pattern.setAttribute('width', '20');
    pattern.setAttribute('height', '20');
    pattern.setAttribute('patternUnits', 'userSpaceOnUse');
    
    const gridPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    gridPath.setAttribute('d', 'M 20 0 L 0 0 0 20');
    gridPath.setAttribute('fill', 'none');
    gridPath.setAttribute('stroke', '#e0e0e0');
    gridPath.setAttribute('stroke-width', '0.5');
    pattern.appendChild(gridPath);
    defs.appendChild(pattern);
    mapContainer.appendChild(defs);
    
    const gridRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    gridRect.setAttribute('width', mapWidth);
    gridRect.setAttribute('height', mapHeight);
    gridRect.setAttribute('fill', 'url(#grid)');
    mapContainer.appendChild(gridRect);
    
    // Add title
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    title.setAttribute('x', padding);
    title.setAttribute('y', padding - 20);
    title.setAttribute('font-size', '18');
    title.setAttribute('font-weight', 'bold');
    title.setAttribute('fill', '#333');
    title.textContent = config.warehouse_name;
    mapContainer.appendChild(title);
    
    // Render each section
    sections.forEach(section => {
        renderSection(mapContainer, section, padding);
    });
}

function renderSection(container, section, padding) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'warehouse-section');
    group.setAttribute('data-section-id', section.id);
    
    // Calculate color intensity based on usage
    const usagePercent = section.usage_percentage;
    let strokeColor = '#4caf50'; // Green
    let strokeWidth = 2;
    
    if (usagePercent >= 90) {
        strokeColor = '#f44336'; // Red
        strokeWidth = 3;
    } else if (usagePercent >= 70) {
        strokeColor = '#ff9800'; // Orange
        strokeWidth = 2.5;
    }
    
    // Section rectangle
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', section.x + padding);
    rect.setAttribute('y', section.y + padding);
    rect.setAttribute('width', section.width);
    rect.setAttribute('height', section.height);
    rect.setAttribute('fill', section.color);
    rect.setAttribute('stroke', strokeColor);
    rect.setAttribute('stroke-width', strokeWidth);
    rect.setAttribute('rx', '5');
    rect.setAttribute('class', 'section-rect');
    group.appendChild(rect);
    
    // Section name
    const nameText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    nameText.setAttribute('x', section.x + padding + section.width / 2);
    nameText.setAttribute('y', section.y + padding + 25);
    nameText.setAttribute('text-anchor', 'middle');
    nameText.setAttribute('font-size', '16');
    nameText.setAttribute('font-weight', 'bold');
    nameText.setAttribute('fill', '#333');
    nameText.textContent = section.name;
    group.appendChild(nameText);
    
    // Usage info
    const usageText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    usageText.setAttribute('x', section.x + padding + section.width / 2);
    usageText.setAttribute('y', section.y + padding + 45);
    usageText.setAttribute('text-anchor', 'middle');
    usageText.setAttribute('font-size', '12');
    usageText.setAttribute('fill', '#666');
    usageText.textContent = `${section.current_usage}/${section.capacity} used`;
    group.appendChild(usageText);
    
    // Usage percentage
    const percentText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    percentText.setAttribute('x', section.x + padding + section.width / 2);
    percentText.setAttribute('y', section.y + padding + 65);
    percentText.setAttribute('text-anchor', 'middle');
    percentText.setAttribute('font-size', '14');
    percentText.setAttribute('font-weight', 'bold');
    percentText.setAttribute('fill', strokeColor);
    percentText.textContent = `${section.usage_percentage}%`;
    group.appendChild(percentText);
    
    // Usage bar
    const barY = section.y + padding + section.height - 20;
    const barWidth = section.width - 20;
    const barX = section.x + padding + 10;
    
    // Background bar
    const barBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    barBg.setAttribute('x', barX);
    barBg.setAttribute('y', barY);
    barBg.setAttribute('width', barWidth);
    barBg.setAttribute('height', '10');
    barBg.setAttribute('fill', '#e0e0e0');
    barBg.setAttribute('rx', '5');
    group.appendChild(barBg);
    
    // Usage bar
    const usageBar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    usageBar.setAttribute('x', barX);
    usageBar.setAttribute('y', barY);
    usageBar.setAttribute('width', (barWidth * section.usage_percentage) / 100);
    usageBar.setAttribute('height', '10');
    usageBar.setAttribute('fill', strokeColor);
    usageBar.setAttribute('rx', '5');
    group.appendChild(usageBar);
    
    // Add hover effect
    group.style.cursor = 'pointer';
    group.addEventListener('mouseenter', function() {
        rect.setAttribute('opacity', '0.8');
        showSectionTooltip(section, event);
    });
    
    group.addEventListener('mouseleave', function() {
        rect.setAttribute('opacity', '1');
        hideSectionTooltip();
    });
    
    group.addEventListener('click', function() {
        window.location.href = `/sections`;
    });
    
    container.appendChild(group);
}

function showSectionTooltip(section, event) {
    // Remove existing tooltip
    hideSectionTooltip();
    
    // Create tooltip
    const tooltip = document.createElement('div');
    tooltip.id = 'section-tooltip';
    tooltip.className = 'position-fixed bg-dark text-white p-3 rounded shadow';
    tooltip.style.zIndex = '9999';
    tooltip.style.maxWidth = '300px';
    
    let productsHtml = '';
    if (section.products && section.products.length > 0) {
        productsHtml = '<div class="mt-2"><strong>Products:</strong><ul class="mb-0 mt-1">';
        section.products.forEach(product => {
            productsHtml += `<li>${product.name}: ${product.quantity} ${product.unit}</li>`;
        });
        productsHtml += '</ul></div>';
    } else {
        productsHtml = '<div class="mt-2 text-muted">No products in this section</div>';
    }
    
    tooltip.innerHTML = `
        <div><strong>${section.name}</strong></div>
        <div class="small mt-1">
            Capacity: ${section.capacity} units<br>
            Used: ${section.current_usage} units (${section.usage_percentage}%)<br>
            Available: ${section.available_space} units
        </div>
        ${productsHtml}
        <div class="small text-muted mt-2">Click to manage sections</div>
    `;
    
    document.body.appendChild(tooltip);
    
    // Position tooltip
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = (rect.right + 10) + 'px';
    tooltip.style.top = rect.top + 'px';
}

function hideSectionTooltip() {
    const tooltip = document.getElementById('section-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeWarehouseMap();
});
