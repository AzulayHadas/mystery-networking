// Theme Management System
class TrendyThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('mystery-theme') || 'dark';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.createThemeSwitcher();
        this.addThemeTransitions();
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        localStorage.setItem('mystery-theme', theme);
        
        // Update theme switcher buttons if they exist
        this.updateSwitcherUI();
        
        // Trigger custom event for theme change
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        
        // Add a subtle animation effect
        document.body.style.transition = 'all 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }

    createThemeSwitcher() {
        // Check if switcher already exists
        if (document.querySelector('.theme-switcher')) return;

        const switcher = document.createElement('div');
        switcher.className = 'theme-switcher fade-in';
        switcher.innerHTML = `
            <button class="theme-toggle" data-theme="light" title="Light Theme">
                ☀️<span> Light</span>
            </button>
            <button class="theme-toggle" data-theme="dark" title="Dark Theme">
                🌙<span> Dark</span>
            </button>
        `;

        // Add to body
        document.body.appendChild(switcher);

        // Add event listeners
        switcher.addEventListener('click', (e) => {
            if (e.target.classList.contains('theme-toggle')) {
                const theme = e.target.getAttribute('data-theme');
                this.applyTheme(theme);
                
                // Add click effect
                e.target.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    e.target.style.transform = '';
                }, 150);
            }
        });

        this.updateSwitcherUI();
    }

    updateSwitcherUI() {
        const toggles = document.querySelectorAll('.theme-toggle');
        toggles.forEach(toggle => {
            const isActive = toggle.getAttribute('data-theme') === this.currentTheme;
            toggle.classList.toggle('active', isActive);
        });
    }

    addThemeTransitions() {
        // Add smooth transitions for theme changes
        const style = document.createElement('style');
        style.textContent = `
            * {
                transition: background-color 0.3s ease, 
                           color 0.3s ease, 
                           border-color 0.3s ease,
                           box-shadow 0.3s ease !important;
            }
        `;
        document.head.appendChild(style);
    }

    // Method to programmatically set theme
    setTheme(theme) {
        if (['light', 'dark'].includes(theme)) {
            this.applyTheme(theme);
        }
    }

    // Get current theme
    getTheme() {
        return this.currentTheme;
    }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.trendyTheme = new TrendyThemeManager();
    
    // Add some trendy loading effects
    addTrendyAnimations();
});

// Add trendy animations to elements
function addTrendyAnimations() {
    // Animate cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('slide-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe all cards and major elements
    setTimeout(() => {
        document.querySelectorAll('.trendy-card, .mission-item, .stat-card, .leaderboard-item')
                .forEach(el => observer.observe(el));
    }, 100);
}

// Utility function to create floating particles effect
function createFloatingParticles() {
    const particleContainer = document.createElement('div');
    particleContainer.className = 'floating-particles';
    particleContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
    `;

    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.style.cssText = `
            position: absolute;
            width: 4px;
            height: 4px;
            background: rgba(102, 126, 234, 0.3);
            border-radius: 50%;
            animation: float ${5 + Math.random() * 10}s infinite ease-in-out;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation-delay: ${Math.random() * 5}s;
        `;
        particleContainer.appendChild(particle);
    }

    document.body.appendChild(particleContainer);

    // Add floating animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0.3; }
            50% { transform: translateY(-20px) rotate(180deg); opacity: 0.8; }
        }
    `;
    document.head.appendChild(style);
}

// Enhanced button ripple effect
function addRippleEffect() {
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('trendy-btn')) {
            const button = e.target;
            const rect = button.getBoundingClientRect();
            const ripple = document.createElement('span');
            const size = Math.max(rect.width, rect.height);
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${e.clientX - rect.left - size/2}px;
                top: ${e.clientY - rect.top - size/2}px;
                background: rgba(255,255,255,0.4);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;
            
            button.style.position = 'relative';
            button.appendChild(ripple);
            
            // Add ripple animation
            if (!document.getElementById('ripple-style')) {
                const rippleStyle = document.createElement('style');
                rippleStyle.id = 'ripple-style';
                rippleStyle.textContent = `
                    @keyframes ripple {
                        to {
                            transform: scale(2);
                            opacity: 0;
                        }
                    }
                `;
                document.head.appendChild(rippleStyle);
            }
            
            setTimeout(() => ripple.remove(), 600);
        }
    });
}

// Initialize enhanced effects
document.addEventListener('DOMContentLoaded', function() {
    addRippleEffect();
    
    // Add particles after a short delay for better performance
    setTimeout(createFloatingParticles, 1000);
});

// Export for use in other files
window.TrendyThemeManager = TrendyThemeManager;