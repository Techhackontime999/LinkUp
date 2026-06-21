(function() {
  'use strict';

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  function initScrollReveal() {
    const elements = document.querySelectorAll('.scroll-reveal');
    if (!elements.length) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    elements.forEach(el => observer.observe(el));
  }

  function initStaggerReveal() {
    const containers = document.querySelectorAll('.stagger-container');
    containers.forEach(container => {
      const items = container.querySelectorAll('.stagger-item');
      if (!items.length) return;
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            items.forEach((item, i) => {
              setTimeout(() => { item.classList.add('visible'); }, i * 80);
            });
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });
      observer.observe(container);
    });
  }

  function initMagneticButtons() {
    document.querySelectorAll('.btn-magnetic').forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = 'translate(' + (x * 0.3) + 'px, ' + (y * 0.3) + 'px)';
      });
      btn.addEventListener('mouseleave', () => { btn.style.transform = ''; });
    });
  }

  function initParallaxTilt() {
    document.querySelectorAll('.tilt-card').forEach(function(card) {
      var isTouching = false;
      card.addEventListener('touchstart', function() { isTouching = true; }, { passive: true });
      card.addEventListener('touchend', function() { isTouching = false; this.style.transform = ''; this.style.setProperty('--mx', '50%'); this.style.setProperty('--my', '50%'); }, { passive: true });
      card.addEventListener('mousemove', function(e) {
        if (isTouching) return;
        var rect = this.getBoundingClientRect();
        var x = (e.clientX - rect.left) / rect.width - 0.5;
        var y = (e.clientY - rect.top) / rect.height - 0.5;
        this.style.transform = 'perspective(600px) rotateY(' + (x * 6) + 'deg) rotateX(' + (-y * 6) + 'deg)';
        this.style.setProperty('--mx', (x * 50 + 50) + '%');
        this.style.setProperty('--my', (y * 50 + 50) + '%');
      });
      card.addEventListener('mouseleave', function() { if (!isTouching) { this.style.transform = ''; this.style.setProperty('--mx', '50%'); this.style.setProperty('--my', '50%'); } });
    });
  }

  function initRippleEffect() {
    document.querySelectorAll('.btn-primary, .btn-magnetic, .btn-follow-ajax, .btn-connect-ajax, .premium-follow-btn').forEach(btn => {
      if (btn.classList.contains('btn-ripple')) return;
      btn.classList.add('btn-ripple');
      btn.addEventListener('click', function(e) {
        var rect = this.getBoundingClientRect();
        var ripple = document.createElement('span');
        ripple.className = 'ripple-effect';
        var size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
        ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
        this.appendChild(ripple);
        ripple.addEventListener('animationend', function() { ripple.remove(); });
      });
    });
  }

  function initAnimatedCounters() {
    document.querySelectorAll('.stat-counter[data-target]').forEach(function(el) {
      var target = parseInt(el.getAttribute('data-target'), 10);
      if (isNaN(target)) return;
      var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (!entry.isIntersecting) return;
          observer.unobserve(el);
          var current = 0;
          var step = Math.max(1, Math.floor(target / 30));
          var timer = setInterval(function() {
            current += step;
            if (current >= target) { current = target; clearInterval(timer); }
            el.textContent = current;
          }, 40);
        });
      }, { threshold: 0.3 });
      observer.observe(el);
    });
  }

  function initLiveDots() {
    document.querySelectorAll('.live-dot').forEach(function(dot) {
      dot.style.animationPlayState = 'running';
    });
  }

  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', (e) => {
        var href = anchor.getAttribute('href');
        if (href === '#') return;
        var target = document.querySelector(href);
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    });
  }

  function init() {
    initScrollReveal();
    initStaggerReveal();
    initMagneticButtons();
    initParallaxTilt();
    initRippleEffect();
    initAnimatedCounters();
    initLiveDots();
    initSmoothScroll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.__animations = {
    initScrollReveal,
    initStaggerReveal,
    initMagneticButtons,
    initParallaxTilt,
    initRippleEffect,
    initAnimatedCounters,
    initLiveDots,
    reinit: init
  };
})();
