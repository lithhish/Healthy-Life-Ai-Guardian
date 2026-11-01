/**
 * Shared JS utilities and dashboard notification banners
 */

const MainApp = {
    showNotification: function(title, message, type = 'info') {
        // Create dynamic alert toast if needed, or print to console
        console.log(`[Notification - ${type.toUpperCase()}] ${title}: ${message}`);
        
        // Simple elegant toast notification
        const toast = document.createElement('div');
        toast.className = `glass-card border-${type} shadow-${type === 'danger' ? 'red' : 'neon'} p-3 position-fixed`;
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '99999';
        toast.style.maxWidth = '350px';
        toast.style.background = 'rgba(15, 23, 42, 0.95)';
        toast.style.animation = 'slideInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        
        const borderColors = {
            'info': '#00e5ff',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444'
        };
        toast.style.borderColor = borderColors[type] || borderColors['info'];

        toast.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <i class="fas ${type === 'danger' ? 'fa-exclamation-triangle' : 'fa-bell'}" style="color: ${borderColors[type]}"></i>
                <div>
                    <h6 class="mb-0 font-weight-bold" style="color: #fff">${title}</h6>
                    <small style="color: #94a3b8">${message}</small>
                </div>
            </div>
        `;
        
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            toast.style.transition = 'all 0.4s ease';
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    }
};
