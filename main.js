// Mobile nav toggle
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');

if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', navLinks.classList.contains('open'));
  });

  // Close on link click
  navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => navLinks.classList.remove('open'));
  });
}

// Portfolio filter (portfolio page)
const filterBtns   = document.querySelectorAll('.filter-btn');
const portfolioGrid = document.getElementById('portfolioGrid');

if (filterBtns.length && portfolioGrid) {
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;
      portfolioGrid.querySelectorAll('.portfolio-item').forEach(item => {
        if (filter === 'all' || item.dataset.cat === filter) {
          item.style.display = '';
        } else {
          item.style.display = 'none';
        }
      });
    });
  });
}

// Contact form — basic client-side feedback
const contactForm = document.getElementById('contactForm');
if (contactForm) {
  contactForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const btn = this.querySelector('[type="submit"]');
    btn.textContent = 'Message Sent! We\'ll be in touch within 1 business day.';
    btn.disabled = true;
    btn.style.background = 'var(--brown-light)';
  });
}

// Sticky header shadow on scroll
const header = document.querySelector('.site-header');
if (header) {
  window.addEventListener('scroll', () => {
    header.style.boxShadow = window.scrollY > 10
      ? '0 4px 24px rgba(107,63,42,0.12)'
      : '0 2px 16px rgba(107,63,42,0.05)';
  }, { passive: true });
}

// Intersection Observer — fade-in on scroll
const fadeEls = document.querySelectorAll('.pillar-card, .service-card, .testimonial-card, .seo-stat-card, .niche-tag, .portfolio-item, .pricing-card');

if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity   = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  fadeEls.forEach((el, i) => {
    el.style.opacity    = '0';
    el.style.transform  = 'translateY(20px)';
    el.style.transition = `opacity 0.55s ease ${(i % 6) * 0.08}s, transform 0.55s ease ${(i % 6) * 0.08}s`;
    observer.observe(el);
  });
}
