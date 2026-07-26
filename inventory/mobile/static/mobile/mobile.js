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

  ready(() => {
    setActiveNavigation();
    setupPageTransitions();
    setupPullToRefresh();
    setupLiveSearch();
  });
})();
