/**
 * SmartWare Pro - Main JavaScript Module
 * Warehouse Management System
 */

// Main application object
const SmartWarePro = {
    // Configuration
    config: {
        debounceDelay: 300,
        animationDuration: 300,
        tooltipDelay: 500
    },

    // Initialize the application
    init() {
        this.setupEventListeners();
        this.setupFormValidation();
        this.setupTableEnhancements();
        this.setupSearchFunctionality();
        this.setupAnimations();
        this.setupAccessibility();
        console.log('SmartWare Pro initialized successfully');
    },

    // Setup global event listeners
    setupEventListeners() {
        // Handle form submissions with loading states
        document.addEventListener('submit', this.handleFormSubmit.bind(this));

        // Handle confirmation dialogs
        document.addEventListener('click', this.handleConfirmation.bind(this));

        // Handle responsive table actions
        document.addEventListener('click', this.handleTableActions.bind(this));

        // Handle keyboard navigation
        document.addEventListener('keydown', this.handleKeyboardNavigation.bind(this));

        // Handle window resize for responsive adjustments
        window.addEventListener('resize', this.debounce(this.handleResize.bind(this), 250));
    },

    // Handle form submissions with loading states
    handleFormSubmit(event) {
        const form = event.target;
        if (!form.matches('form')) return;

        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton && !submitButton.classList.contains('loading')) {
            submitButton.classList.add('loading');
            submitButton.disabled = true;

            // Re-enable button if form validation fails
            setTimeout(() => {
                if (submitButton.classList.contains('loading')) {
                    submitButton.classList.remove('loading');
                    submitButton.disabled = false;
                }
            }, 5000);
        }
    },

    // Handle confirmation dialogs
    handleConfirmation(event) {
        const element = event.target.closest('[data-confirm]');
        if (!element) return;

        event.preventDefault();
        const message = element.getAttribute('data-confirm');
        const confirmed = confirm(message);

        if (confirmed) {
            if (element.tagName === 'A') {
                window.location.href = element.href;
            } else if (element.tagName === 'BUTTON' && element.form) {
                element.form.submit();
            }
        }
    },

    // Handle table actions (mobile responsive)
    handleTableActions(event) {
        const actionButton = event.target.closest('.table-action-toggle');
        if (!actionButton) return;

        event.preventDefault();
        const row = actionButton.closest('tr');
        const actionsMenu = row.querySelector('.table-actions-menu');

        if (actionsMenu) {
            actionsMenu.style.display = actionsMenu.style.display === 'block' ? 'none' : 'block';
        }
    },

    // Handle keyboard navigation
    handleKeyboardNavigation(event) {
        // ESC key to close modals and menus
        if (event.key === 'Escape') {
            // Close any open table action menus
            document.querySelectorAll('.table-actions-menu').forEach(menu => {
                menu.style.display = 'none';
            });

            // Close modals (Bootstrap handles this automatically)
        }

        // Enter key on buttons
        if (event.key === 'Enter' && event.target.matches('[role="button"]')) {
            event.target.click();
        }
    },

    // Handle window resize
    handleResize() {
        // Update table responsive behavior
        this.updateTableResponsiveness();
        
        // Update warehouse map if it exists
        if (window.warehouseMap) {
            // Refresh map layout if needed
            this.debounce(() => {
                if (window.warehouseMap.refresh) {
                    window.warehouseMap.refresh();
                }
            }, 500)();
        }
    },

    // Setup form validation enhancements
    setupFormValidation() {
        // Real-time validation feedback
        document.querySelectorAll('input, textarea, select').forEach(input => {
            input.addEventListener('blur', this.validateField.bind(this));
            input.addEventListener('input', this.debounce(this.validateField.bind(this), 500));
        });

        // Custom validation messages
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('invalid', this.handleInvalidForm.bind(this), true);
        });
    },

    // Validate individual field
    validateField(event) {
        const field = event.target;
        const isValid = field.checkValidity();
        
        // Remove existing validation classes
        field.classList.remove('is-valid', 'is-invalid');
        
        // Add appropriate class
        if (field.value.trim() !== '') {
            field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        }

        // Update custom feedback
        this.updateValidationFeedback(field);
    },

    // Update validation feedback
    updateValidationFeedback(field) {
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!feedback) return;

        if (field.validity.valueMissing) {
            feedback.textContent = `${this.getFieldLabel(field)} is required.`;
        } else if (field.validity.typeMismatch) {
            feedback.textContent = `Please enter a valid ${field.type}.`;
        } else if (field.validity.rangeUnderflow) {
            feedback.textContent = `Value must be at least ${field.min}.`;
        } else if (field.validity.rangeOverflow) {
            feedback.textContent = `Value must be no more than ${field.max}.`;
        } else if (field.validity.tooShort) {
            feedback.textContent = `Must be at least ${field.minLength} characters.`;
        } else if (field.validity.tooLong) {
            feedback.textContent = `Must be no more than ${field.maxLength} characters.`;
        }
    },

    // Get field label for validation messages
    getFieldLabel(field) {
        const label = document.querySelector(`label[for="${field.id}"]`);
        return label ? label.textContent.replace(':', '') : 'Field';
    },

    // Handle invalid form submission
    handleInvalidForm(event) {
        event.preventDefault();
        const field = event.target;
        
        // Focus on first invalid field
        if (field === document.querySelector('input:invalid, textarea:invalid, select:invalid')) {
            field.focus();
        }
        
        // Show validation feedback
        field.classList.add('is-invalid');
        this.updateValidationFeedback(field);
    },

    // Setup table enhancements
    setupTableEnhancements() {
        // Sort functionality
        document.querySelectorAll('.sortable').forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', this.handleTableSort.bind(this));
        });

        // Row selection
        document.querySelectorAll('.table input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', this.handleRowSelection.bind(this));
        });

        // Update table responsiveness
        this.updateTableResponsiveness();
    },

    // Handle table sorting
    handleTableSort(event) {
        const header = event.target;
        const table = header.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        const currentSort = header.getAttribute('data-sort') || 'asc';
        const newSort = currentSort === 'asc' ? 'desc' : 'asc';

        // Clear other sort indicators
        table.querySelectorAll('th').forEach(th => {
            th.removeAttribute('data-sort');
            th.classList.remove('sort-asc', 'sort-desc');
        });

        // Set new sort
        header.setAttribute('data-sort', newSort);
        header.classList.add(`sort-${newSort}`);

        // Sort rows
        rows.sort((a, b) => {
            const aVal = a.children[columnIndex].textContent.trim();
            const bVal = b.children[columnIndex].textContent.trim();
            
            // Try to parse as numbers
            const aNum = parseFloat(aVal);
            const bNum = parseFloat(bVal);
            
            let comparison = 0;
            if (!isNaN(aNum) && !isNaN(bNum)) {
                comparison = aNum - bNum;
            } else {
                comparison = aVal.localeCompare(bVal);
            }
            
            return newSort === 'asc' ? comparison : -comparison;
        });

        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));

        // Add sort animation
        rows.forEach((row, index) => {
            row.style.animation = `fadeIn 0.3s ease ${index * 0.02}s both`;
        });
    },

    // Handle row selection
    handleRowSelection(event) {
        const checkbox = event.target;
        const row = checkbox.closest('tr');
        
        if (checkbox.checked) {
            row.classList.add('table-active');
        } else {
            row.classList.remove('table-active');
        }

        // Update bulk action buttons
        this.updateBulkActions();
    },

    // Update bulk action button states
    updateBulkActions() {
        const checkboxes = document.querySelectorAll('.table input[type="checkbox"]:checked');
        const bulkActions = document.querySelectorAll('.bulk-action');
        
        bulkActions.forEach(action => {
            action.disabled = checkboxes.length === 0;
        });
    },

    // Update table responsiveness
    updateTableResponsiveness() {
        const tables = document.querySelectorAll('.table-responsive');
        
        tables.forEach(container => {
            const table = container.querySelector('table');
            if (!table) return;

            if (window.innerWidth < 768) {
                // Mobile: Add action toggles if not present
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const actionsCell = row.querySelector('.table-actions');
                    if (actionsCell && !actionsCell.querySelector('.table-action-toggle')) {
                        const toggle = document.createElement('button');
                        toggle.className = 'btn btn-sm btn-outline-secondary table-action-toggle';
                        toggle.innerHTML = '<i class="fas fa-ellipsis-v"></i>';
                        toggle.setAttribute('aria-label', 'Show actions');
                        
                        const menu = document.createElement('div');
                        menu.className = 'table-actions-menu';
                        menu.style.display = 'none';
                        
                        // Move existing buttons to menu
                        const existingActions = actionsCell.querySelectorAll('.btn');
                        existingActions.forEach(btn => {
                            menu.appendChild(btn.cloneNode(true));
                            btn.style.display = 'none';
                        });
                        
                        actionsCell.appendChild(toggle);
                        actionsCell.appendChild(menu);
                    }
                });
            } else {
                // Desktop: Remove mobile toggles
                const toggles = table.querySelectorAll('.table-action-toggle, .table-actions-menu');
                toggles.forEach(toggle => toggle.remove());
                
                // Show original buttons
                const hiddenButtons = table.querySelectorAll('.table-actions .btn[style*="display: none"]');
                hiddenButtons.forEach(btn => btn.style.display = '');
            }
        });
    },

    // Setup search functionality
    setupSearchFunctionality() {
        const searchInputs = document.querySelectorAll('.search-input, input[name="search"]');
        
        searchInputs.forEach(input => {
            // Add search icon if not present
            if (!input.parentNode.querySelector('.search-icon')) {
                const icon = document.createElement('i');
                icon.className = 'fas fa-search search-icon';
                input.parentNode.appendChild(icon);
            }

            // Add real-time search (debounced)
            input.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
            
            // Add search shortcut (Ctrl/Cmd + F)
            document.addEventListener('keydown', (event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
                    event.preventDefault();
                    input.focus();
                }
            });
        });
    },

    // Handle search input
    handleSearch(event) {
        const input = event.target;
        const searchTerm = input.value.toLowerCase().trim();
        const targetTable = document.querySelector('.table tbody');
        
        if (!targetTable) return;

        const rows = targetTable.querySelectorAll('tr');
        let visibleCount = 0;

        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const isVisible = searchTerm === '' || text.includes(searchTerm);
            
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) visibleCount++;
        });

        // Update search results count
        this.updateSearchResultsCount(visibleCount, rows.length);
    },

    // Update search results count
    updateSearchResultsCount(visible, total) {
        let counter = document.querySelector('.search-results-count');
        
        if (!counter) {
            counter = document.createElement('div');
            counter.className = 'search-results-count text-muted small mt-2';
            const searchInput = document.querySelector('.search-input, input[name="search"]');
            if (searchInput) {
                searchInput.parentNode.appendChild(counter);
            }
        }

        if (visible === total) {
            counter.textContent = '';
        } else {
            counter.textContent = `Showing ${visible} of ${total} items`;
        }
    },

    // Setup animations
    setupAnimations() {
        // Intersection Observer for scroll animations
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver(this.handleIntersection.bind(this), {
                threshold: 0.1,
                rootMargin: '50px'
            });

            // Observe cards and other elements
            document.querySelectorAll('.card, .alert, .table').forEach(el => {
                observer.observe(el);
            });
        }

        // Add loading animations to buttons
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.type === 'submit' && !btn.classList.contains('loading')) {
                    this.addButtonLoading(btn);
                }
            });
        });
    },

    // Handle intersection for scroll animations
    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    },

    // Add loading state to button
    addButtonLoading(button) {
        button.classList.add('loading');
        button.disabled = true;
        
        const originalText = button.textContent;
        button.setAttribute('data-original-text', originalText);
        
        // Remove loading state after timeout (fallback)
        setTimeout(() => {
            this.removeButtonLoading(button);
        }, 5000);
    },

    // Remove loading state from button
    removeButtonLoading(button) {
        button.classList.remove('loading');
        button.disabled = false;
        
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.textContent = originalText;
        }
    },

    // Setup accessibility features
    setupAccessibility() {
        // Add ARIA labels to interactive elements
        document.querySelectorAll('[data-bs-toggle]').forEach(el => {
            if (!el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')) {
                const text = el.textContent.trim() || el.title || 'Interactive element';
                el.setAttribute('aria-label', text);
            }
        });

        // Add focus indicators
        document.querySelectorAll('a, button, input, select, textarea').forEach(el => {
            el.addEventListener('focus', () => el.classList.add('focus-visible'));
            el.addEventListener('blur', () => el.classList.remove('focus-visible'));
        });

        // Skip to main content link
        this.addSkipToMainLink();
    },

    // Add skip to main content link for screen readers
    addSkipToMainLink() {
        const existingLink = document.querySelector('.skip-to-main');
        if (existingLink) return;

        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-to-main sr-only sr-only-focusable';
        skipLink.textContent = 'Skip to main content';
        skipLink.style.cssText = `
            position: absolute;
            top: -40px;
            left: 6px;
            z-index: 1000;
            padding: 8px 16px;
            background: #000;
            color: #fff;
            text-decoration: none;
            border-radius: 4px;
        `;
        
        skipLink.addEventListener('focus', () => {
            skipLink.style.top = '6px';
        });
        
        skipLink.addEventListener('blur', () => {
            skipLink.style.top = '-40px';
        });

        document.body.insertBefore(skipLink, document.body.firstChild);

        // Add main content ID if not present
        const main = document.querySelector('main');
        if (main && !main.id) {
            main.id = 'main-content';
        }
    },

    // Utility: Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Utility: Show toast notification
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        // Create toast container if it doesn't exist
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1080';
            document.body.appendChild(container);
        }

        container.appendChild(toast);

        // Initialize Bootstrap toast
        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();

        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },

    // Utility: Format number with proper separators
    formatNumber(number, options = {}) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
            ...options
        }).format(number);
    },

    // Utility: Format date
    formatDate(date, options = {}) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            ...options
        }).format(new Date(date));
    },

    // Utility: Copy text to clipboard
    async copyToClipboard(text) {
        try {
            if (navigator.clipboard) {
                await navigator.clipboard.writeText(text);
                this.showToast('Copied to clipboard!', 'success', 2000);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                this.showToast('Copied to clipboard!', 'success', 2000);
            }
        } catch (err) {
            console.error('Failed to copy text:', err);
            this.showToast('Failed to copy to clipboard', 'danger', 3000);
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    SmartWarePro.init();
});

// Export for global use
window.SmartWarePro = SmartWarePro;
