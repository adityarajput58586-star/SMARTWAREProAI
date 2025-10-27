/**
 * QR/Barcode Scanner using getUserMedia API
 * SmartWare Pro - Warehouse Management System
 */

class QRScanner {
    constructor() {
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanning = false;
        this.stream = null;
        this.scanInterval = null;
    }

    async startScanner() {
        try {
            this.video = document.getElementById('scanner-video');
            if (!this.video) {
                console.error('Scanner video element not found');
                return;
            }

            // Create canvas for image capture
            this.canvas = document.createElement('canvas');
            this.context = this.canvas.getContext('2d');

            // Get camera stream
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment', // Use back camera on mobile
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            });

            this.video.srcObject = this.stream;
            this.video.play();

            this.scanning = true;
            this.startScanLoop();

            console.log('QR Scanner started successfully');
        } catch (error) {
            console.error('Error starting QR scanner:', error);
            this.showError('Camera access denied or not available. Please check your camera permissions.');
        }
    }

    stopScanner() {
        this.scanning = false;

        if (this.scanInterval) {
            clearInterval(this.scanInterval);
            this.scanInterval = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.video) {
            this.video.srcObject = null;
        }

        console.log('QR Scanner stopped');
    }

    startScanLoop() {
        // Scan every 500ms
        this.scanInterval = setInterval(() => {
            if (this.scanning && this.video && this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                this.captureAndScan();
            }
        }, 500);
    }

    captureAndScan() {
        if (!this.video || !this.canvas || !this.context) return;

        try {
            // Set canvas size to video dimensions
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;

            // Draw video frame to canvas
            this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

            // Get image data for scanning
            const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Try to decode QR/barcode from image data
            const code = this.decodeFromImageData(imageData);
            
            if (code) {
                this.onScanSuccess(code);
            }
        } catch (error) {
            console.error('Error during scan:', error);
        }
    }

    decodeFromImageData(imageData) {
        // This is a simplified decoder for demonstration
        // In a real implementation, you would use libraries like:
        // - jsQR for QR codes
        // - QuaggaJS for barcodes
        // - ZXing-js for multiple formats
        
        // For demo purposes, we'll simulate scanning by looking for patterns
        // and return mock data when certain conditions are met
        
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        
        // Simple pattern detection (mock implementation)
        let darkPixels = 0;
        let totalPixels = width * height;
        
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];
            const brightness = (r + g + b) / 3;
            
            if (brightness < 128) {
                darkPixels++;
            }
        }
        
        const darkRatio = darkPixels / totalPixels;
        
        // If there's a good contrast ratio, simulate a successful scan
        if (darkRatio > 0.1 && darkRatio < 0.9) {
            // Generate a mock scan result for demo
            const mockCodes = [
                'LAPTOP123',
                'MOUSE456',
                'KEYBOARD789',
                'MONITOR001',
                'PRINTER002',
                'TABLET003',
                'PHONE004',
                'HEADSET005'
            ];
            
            // Return a random mock code occasionally
            if (Math.random() < 0.3) { // 30% chance of "successful" scan
                return mockCodes[Math.floor(Math.random() * mockCodes.length)];
            }
        }
        
        return null;
    }

    onScanSuccess(code) {
        console.log('QR/Barcode scanned:', code);
        
        // Stop scanning temporarily
        this.scanning = false;
        clearInterval(this.scanInterval);
        
        // Update the result field
        const resultField = document.getElementById('scannedResult');
        if (resultField) {
            resultField.value = code;
        }
        
        // Show success feedback
        this.showSuccess(`Successfully scanned: ${code}`);
        
        // Resume scanning after 2 seconds
        setTimeout(() => {
            this.scanning = true;
            this.startScanLoop();
        }, 2000);
    }

    showSuccess(message) {
        // Create temporary success notification
        this.showNotification(message, 'success');
    }

    showError(message) {
        // Create temporary error notification
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Global scanner instance
let qrScanner = null;

// Global functions for modal integration
function startScanner() {
    if (!qrScanner) {
        qrScanner = new QRScanner();
    }
    qrScanner.startScanner();
}

function stopScanner() {
    if (qrScanner) {
        qrScanner.stopScanner();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('QR Scanner module loaded');
    
    // Check for camera support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('Camera API not supported in this browser');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (qrScanner) {
        qrScanner.stopScanner();
    }
});
