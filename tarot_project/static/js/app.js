/**
 * Tarot Application JavaScript
 * Core functionality for the tarot reading application
 */

(function() {
    'use strict';
    
    // Global app namespace
    window.TarotApp = window.TarotApp || {};
    
    /**
     * Initialize the application
     */
    TarotApp.init = function() {
        this.setupFormEnhancements();
        this.setupLoadingStates();
        this.setupTouchFeedback();
        this.setupAccessibility();
        this.setupPerformanceOptimizations();
    };
    
    /**
     * Enhanced form functionality
     */
    TarotApp.setupFormEnhancements = function() {
        // Auto-resize textareas
        document.querySelectorAll('textarea').forEach(function(textarea) {
            textarea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = this.scrollHeight + 'px';
            });
        });
        
        // Enhanced input styling
        document.querySelectorAll('input, select, textarea').forEach(function(input) {
            if (!input.classList.contains('form-input')) {
                input.classList.add('form-input');
            }
            
            // Focus enhancements
            input.addEventListener('focus', function() {
                this.parentElement.classList.add('ring-2', 'ring-purple-500', 'ring-opacity-50');
            });
            
            input.addEventListener('blur', function() {
                this.parentElement.classList.remove('ring-2', 'ring-purple-500', 'ring-opacity-50');
            });
        });
        
        // Form submission handling
        document.querySelectorAll('form').forEach(function(form) {
            form.addEventListener('submit', function(e) {
                var submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    TarotApp.showLoadingState(submitBtn);
                }
            });
        });
    };
    
    /**
     * Loading states for buttons and forms
     */
    TarotApp.setupLoadingStates = function() {
        // HTMX event listeners for loading states
        document.addEventListener('htmx:beforeRequest', function(evt) {
            var target = evt.target;
            if (target.tagName === 'BUTTON') {
                TarotApp.showLoadingState(target);
            }
        });
        
        document.addEventListener('htmx:afterRequest', function(evt) {
            var target = evt.target;
            if (target.tagName === 'BUTTON') {
                TarotApp.hideLoadingState(target);
            }
        });
    };
    
    /**
     * Show loading state on button
     */
    TarotApp.showLoadingState = function(button) {
        if (button.dataset.originalText) return; // Already in loading state
        
        button.dataset.originalText = button.innerHTML;
        button.disabled = true;
        button.classList.add('opacity-75');
        
        var loadingSpinner = '<span class="loading-spinner mr-2" style="width: 16px; height: 16px;"></span>';
        var loadingText = button.dataset.loadingText || 'Загрузка...';
        button.innerHTML = loadingSpinner + loadingText;
    };
    
    /**
     * Hide loading state on button
     */
    TarotApp.hideLoadingState = function(button) {
        if (!button.dataset.originalText) return;
        
        button.innerHTML = button.dataset.originalText;
        button.disabled = false;
        button.classList.remove('opacity-75');
        delete button.dataset.originalText;
    };
    
    /**
     * Touch feedback for mobile devices
     */
    TarotApp.setupTouchFeedback = function() {
        if (!('ontouchstart' in window)) return;
        
        var touchTargets = 'button, .btn-primary, .btn-secondary, .touch-target';
        
        document.addEventListener('touchstart', function(e) {
            if (e.target.matches(touchTargets)) {
                e.target.style.transform = 'scale(0.98)';
                e.target.style.transition = 'transform 0.1s ease';
            }
        }, { passive: true });
        
        document.addEventListener('touchend', function(e) {
            if (e.target.matches(touchTargets)) {
                e.target.style.transform = 'scale(1)';
            }
        }, { passive: true });
        
        document.addEventListener('touchcancel', function(e) {
            if (e.target.matches(touchTargets)) {
                e.target.style.transform = 'scale(1)';
            }
        }, { passive: true });
    };
    
    /**
     * Accessibility enhancements
     */
    TarotApp.setupAccessibility = function() {
        // Smooth scroll for anchor links
        document.addEventListener('click', function(e) {
            if (e.target.matches('a[href^="#"]')) {
                e.preventDefault();
                var target = document.querySelector(e.target.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
        
        // Skip link for keyboard users
        var skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Перейти к основному содержимому';
        skipLink.className = 'sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 bg-purple-600 text-white p-2 z-50';
        document.body.insertBefore(skipLink, document.body.firstChild);
        
        // Add main content id if not present
        var main = document.querySelector('main');
        if (main && !main.id) {
            main.id = 'main-content';
        }
    };
    
    /**
     * Performance optimizations
     */
    TarotApp.setupPerformanceOptimizations = function() {
        // Lazy load images
        if ('IntersectionObserver' in window) {
            var imageObserver = new IntersectionObserver(function(entries, observer) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        var img = entry.target;
                        img.src = img.dataset.src || img.src;
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }
                });
            });
            
            document.querySelectorAll('img[data-src]').forEach(function(img) {
                imageObserver.observe(img);
            });
        }
        
        // Preload critical resources
        this.preloadCriticalResources();
    };
    
    /**
     * Preload critical resources
     */
    TarotApp.preloadCriticalResources = function() {
        var criticalResources = [
            '/tarot/static/css/app.css',
            '/tarot/static/manifest.json'
        ];
        
        criticalResources.forEach(function(resource) {
            var link = document.createElement('link');
            link.rel = 'preload';
            link.href = resource;
            link.as = resource.endsWith('.css') ? 'style' : 'fetch';
            document.head.appendChild(link);
        });
    };
    
    /**
     * Timer functionality for cooldown
     */
    TarotApp.updateTimer = function(timerId, onExpire) {
        var timerElement = document.getElementById(timerId);
        if (!timerElement) return;
        
        var timeText = timerElement.textContent.trim();
        var timeParts = timeText.split(':');
        if (timeParts.length !== 2) return;
        
        var minutes = parseInt(timeParts[0], 10);
        var seconds = parseInt(timeParts[1], 10);
        
        var updateDisplay = function() {
            if (seconds < 0) {
                minutes -= 1;
                seconds = 59;
            }
            
            if (minutes < 0) {
                if (typeof onExpire === 'function') {
                    onExpire();
                } else {
                    location.reload();
                }
                return;
            }
            
            timerElement.textContent = minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
            seconds -= 1;
        };
        
        updateDisplay();
        setInterval(updateDisplay, 1000);
    };
    
    /**
     * Share functionality
     */
    TarotApp.shareReading = function(title, text, url) {
        title = title || 'Мой расклад Таро';
        text = text || 'Посмотрите на мой расклад Таро';
        url = url || window.location.href;
        
        if (navigator.share) {
            navigator.share({ title: title, text: text, url: url })
                .catch(function(err) {
                    console.log('Error sharing:', err);
                    TarotApp.fallbackShare(url);
                });
        } else {
            TarotApp.fallbackShare(url);
        }
    };
    
    /**
     * Fallback share functionality
     */
    TarotApp.fallbackShare = function(url) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(url).then(function() {
                TarotApp.showToast('Ссылка скопирована в буфер обмена!');
            }).catch(function() {
                TarotApp.showShareDialog(url);
            });
        } else {
            TarotApp.showShareDialog(url);
        }
    };
    
    /**
     * Show share dialog
     */
    TarotApp.showShareDialog = function(url) {
        var textarea = document.createElement('textarea');
        textarea.value = url;
        textarea.style.position = 'fixed';
        textarea.style.left = '-999999px';
        document.body.appendChild(textarea);
        textarea.select();
        textarea.setSelectionRange(0, 99999);
        
        try {
            document.execCommand('copy');
            TarotApp.showToast('Ссылка скопирована!');
        } catch (err) {
            TarotApp.showToast('Не удалось скопировать ссылку');
        }
        
        document.body.removeChild(textarea);
    };
    
    /**
     * Show toast notification
     */
    TarotApp.showToast = function(message, duration) {
        duration = duration || 3000;
        
        var toast = document.createElement('div');
        toast.textContent = message;
        toast.className = 'fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-purple-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300';
        toast.style.opacity = '0';
        
        document.body.appendChild(toast);
        
        // Fade in
        setTimeout(function() {
            toast.style.opacity = '1';
        }, 10);
        
        // Fade out and remove
        setTimeout(function() {
            toast.style.opacity = '0';
            setTimeout(function() {
                if (toast.parentNode) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, duration);
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', TarotApp.init.bind(TarotApp));
    } else {
        TarotApp.init();
    }
    
})();