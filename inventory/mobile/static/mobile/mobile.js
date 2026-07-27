(() => {
  'use strict';

  const ready = (fn) => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn, { once: true });
    } else {
      fn();
    }
  };

  const normalizePath = (value) => {
    try {
      const url = new URL(value, window.location.origin);
      return url.pathname.replace(/\/$/, '') || '/';
    } catch (_) {
      return String(value || '').split(/[?#]/)[0].replace(/\/$/, '') || '/';
    }
  };

  const setActiveNavigation = () => {
    const currentPath = normalizePath(window.location.href);
    document.querySelectorAll('.bottom-nav .nav-item[href]').forEach((item) => {
      const itemPath = normalizePath(item.getAttribute('href'));
      const isActive = itemPath === '/' ? currentPath === '/' : currentPath === itemPath || currentPath.startsWith(`${itemPath}/`);
      item.classList.toggle('active', isActive);
      if (isActive) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
  };

  const setupPageTransitions = () => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const root = document.querySelector('.page-transition') || document.querySelector('main') || document.querySelector('.content');
    if (!root || reduceMotion) return;

    root.classList.add('page-transition', 'is-entering');
    window.setTimeout(() => root.classList.remove('is-entering'), 260);

    document.addEventListener('click', (event) => {
      const link = event.target.closest('a[href]');
      if (!link || event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (link.target && link.target !== '_self') return;
      if (link.hasAttribute('download')) return;

      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || url.pathname === window.location.pathname && url.search === window.location.search) return;

      event.preventDefault();
      root.classList.add('is-leaving');
      window.setTimeout(() => { window.location.href = url.href; }, 160);
    });
  };

  const setupPullToRefresh = () => {
    const container = document.querySelector('.pull-to-refresh');
    if (!container) return;

    let startY = 0;
    let distance = 0;
    let tracking = false;
    let refreshing = false;
    const threshold = Number(container.dataset.refreshThreshold || 72);
    let indicator = container.querySelector('.pull-indicator');

    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'pull-indicator';
      indicator.textContent = 'Pull to refresh';
      container.prepend(indicator);
    }

    const reset = () => {
      tracking = false;
      distance = 0;
      container.classList.remove('is-pulling');
      if (!refreshing) indicator.textContent = 'Pull to refresh';
    };

    container.addEventListener('touchstart', (event) => {
      if (window.scrollY !== 0 || refreshing || event.touches.length !== 1) return;
      tracking = true;
      startY = event.touches[0].clientY;
    }, { passive: true });

    container.addEventListener('touchmove', (event) => {
      if (!tracking || refreshing) return;
      distance = Math.max(0, event.touches[0].clientY - startY);
      if (distance > 12) {
        container.classList.add('is-pulling');
        indicator.textContent = distance >= threshold ? 'Release to refresh' : 'Pull to refresh';
      }
    }, { passive: true });

    container.addEventListener('touchend', () => {
      if (!tracking || refreshing) return;
      if (distance >= threshold) {
        refreshing = true;
        container.classList.remove('is-pulling');
        container.classList.add('is-refreshing');
        indicator.textContent = 'Refreshing…';
        window.location.reload();
      } else {
        reset();
      }
    }, { passive: true });

    container.addEventListener('touchcancel', reset, { passive: true });
  };

  const setupLiveSearch = () => {
    const inputs = document.querySelectorAll('[data-search], .search-bar input, input[type="search"]');
    inputs.forEach((input) => {
      if (input.matches('[data-mobile-search]')) return;

      const targetSelector = input.dataset.searchTarget || input.dataset.target || '[data-filter-item], .search-filter-item, .list-item, .card';
      const scope = input.closest('[data-search-scope]') || document;
      const emptySelector = input.dataset.emptyTarget;
      const emptyEl = emptySelector ? document.querySelector(emptySelector) : null;

      const filter = () => {
        const query = input.value.trim().toLowerCase();
        const items = Array.from(scope.querySelectorAll(targetSelector)).filter((item) => item !== input && !item.contains(input));
        let visibleCount = 0;

        items.forEach((item) => {
          const haystack = (item.dataset.searchText || item.textContent || '').toLowerCase();
          const visible = !query || haystack.includes(query);
          item.classList.toggle('is-hidden', !visible);
          item.hidden = !visible;
          if (visible) visibleCount += 1;
        });

        if (emptyEl) emptyEl.hidden = visibleCount !== 0;
      };

      input.addEventListener('input', filter);
      filter();
    });
  };

  const setupViewToggle = () => {
    const viewBtns = document.querySelectorAll('.view-btn');
    if (!viewBtns.length) return;

    const savedView = localStorage.getItem('item-view') || 'list';
    document.body.setAttribute('data-view', savedView);

    viewBtns.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.view === savedView);
      btn.addEventListener('click', () => {
        const view = btn.dataset.view || 'list';
        document.body.setAttribute('data-view', view);
        localStorage.setItem('item-view', view);
        viewBtns.forEach((otherBtn) => otherBtn.classList.toggle('active', otherBtn.dataset.view === view));
      });
    });
  };

  const setupLiveItemFilter = () => {
    const searchInput = document.querySelector('[data-mobile-search]');
    if (!searchInput) return;

    const scope = searchInput.closest('main') || document;
    const items = Array.from(scope.querySelectorAll('.list-view .list-item, .item-grid .item-card'));
    let debounceTimer;

    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        const query = searchInput.value.trim().toLowerCase();
        items.forEach((item) => {
          const text = (item.textContent || '').toLowerCase();
          const hidden = query ? !text.includes(query) : false;
          item.hidden = hidden;
          item.style.display = hidden ? 'none' : '';
        });
      }, 300);
    });
  };

  const setupSwipeActions = () => {
    const cards = document.querySelectorAll('.list-view .list-item, .item-card');

    cards.forEach((card) => {
      let startX = 0;
      let currentX = 0;
      let tracking = false;
      const threshold = 70;

      const findAdjustButton = (delta) => {
        const forms = Array.from(card.querySelectorAll('form[action*="adjust-quantity"]'));
        const form = forms.find((candidate) => {
          const input = candidate.querySelector('input[name="delta"], input[name="change"]');
          return input && Number(input.value) === delta;
        });

        return form ? form.querySelector('button[type="submit"], button') : null;
      };

      card.addEventListener('touchstart', (event) => {
        if (event.touches.length !== 1) return;
        startX = event.touches[0].clientX;
        currentX = 0;
        tracking = true;
      }, { passive: true });

      card.addEventListener('touchmove', (event) => {
        if (!tracking) return;
        currentX = event.touches[0].clientX - startX;
        card.style.transform = `translateX(${Math.max(-100, Math.min(100, currentX))}px)`;
        card.style.transition = 'none';
      }, { passive: true });

      card.addEventListener('touchend', () => {
        if (!tracking) return;
        tracking = false;
        card.style.transition = 'transform 0.2s ease';
        card.style.transform = '';

        const delta = currentX > threshold ? 1 : currentX < -threshold ? -1 : 0;
        if (delta !== 0) {
          const btn = findAdjustButton(delta);
          if (btn) btn.click();
        }
      }, { passive: true });

      card.addEventListener('touchcancel', () => {
        tracking = false;
        card.style.transition = 'transform 0.2s ease';
        card.style.transform = '';
      }, { passive: true });
    });
  };

  ready(() => {
    setActiveNavigation();
    setupPageTransitions();
    setupPullToRefresh();
    setupLiveSearch();
    setupViewToggle();
    setupLiveItemFilter();
    setupSwipeActions();
  });
})();
