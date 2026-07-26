(function () {
  'use strict';

  var SWIPE_THRESHOLD = 72;
  var SWIPE_RESTRAINT = 80;
  var DOUBLE_TAP_DELAY = 300;
  var SEARCH_DELAY = 300;
  var PULL_DISTANCE = 82;
  var MAX_PULL = 120;

  function debounce(fn, delay) {
    var timer;
    return function debounced() {
      var context = this;
      var args = arguments;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { fn.apply(context, args); }, delay);
    };
  }

  function getActionUrl(card, action) {
    var explicit = card.getAttribute('data-' + action + '-url');
    if (explicit) return explicit;
    var selector = action === 'edit'
      ? 'a[href*="edit"], a[data-mobile-action="edit"]'
      : 'a[href*="adjust"], button[data-mobile-action="quick-adjust"], a[data-mobile-action="quick-adjust"]';
    var target = card.querySelector(selector);
    if (!target) return null;
    return target.href || target.getAttribute('formaction') || target.getAttribute('data-url');
  }

  function dispatchMobileAction(card, action) {
    var event = new CustomEvent('mobile:swipe', { bubbles: true, cancelable: true, detail: { action: action, card: card } });
    card.dispatchEvent(event);
    if (event.defaultPrevented) return;
    var actionButton = card.querySelector('[data-mobile-action="' + action + '"]');
    if (actionButton) { actionButton.click(); return; }
    var url = getActionUrl(card, action);
    if (url) window.location.href = url;
  }

  function resetCard(card) {
    card.classList.remove('is-swiping', 'swipe-left', 'swipe-right');
    card.style.transform = '';
  }

  function initSwipeDetection() {
    document.querySelectorAll('.card-mobile').forEach(function (card) {
      var startX = 0, startY = 0, deltaX = 0, deltaY = 0, tracking = false;
      card.addEventListener('touchstart', function (event) {
        if (event.touches.length !== 1) return;
        startX = event.touches[0].clientX;
        startY = event.touches[0].clientY;
        deltaX = 0;
        deltaY = 0;
        tracking = true;
        card.classList.add('is-swiping');
      }, { passive: true });
      card.addEventListener('touchmove', function (event) {
        if (!tracking || event.touches.length !== 1) return;
        deltaX = event.touches[0].clientX - startX;
        deltaY = event.touches[0].clientY - startY;
        if (Math.abs(deltaY) > Math.abs(deltaX) || Math.abs(deltaY) > SWIPE_RESTRAINT) return;
        var clamped = Math.max(-MAX_PULL, Math.min(MAX_PULL, deltaX));
        card.style.transform = 'translateX(' + clamped + 'px)';
        card.classList.toggle('swipe-left', clamped < -SWIPE_THRESHOLD / 2);
        card.classList.toggle('swipe-right', clamped > SWIPE_THRESHOLD / 2);
      }, { passive: true });
      card.addEventListener('touchend', function () {
        if (!tracking) return;
        tracking = false;
        card.classList.remove('is-swiping');
        if (Math.abs(deltaX) >= SWIPE_THRESHOLD && Math.abs(deltaY) <= SWIPE_RESTRAINT) {
          var action = deltaX < 0 ? 'quick-adjust' : 'edit';
          card.style.transform = 'translateX(' + (deltaX < 0 ? '-100%' : '100%') + ')';
          window.setTimeout(function () { dispatchMobileAction(card, action); resetCard(card); }, 120);
          return;
        }
        resetCard(card);
      }, { passive: true });
      card.addEventListener('touchcancel', function () { tracking = false; resetCard(card); }, { passive: true });
    });
  }

  function ensurePullIndicator() {
    var indicator = document.querySelector('.pull-to-refresh-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'pull-to-refresh-indicator';
      indicator.setAttribute('aria-hidden', 'true');
      document.body.appendChild(indicator);
    }
    return indicator;
  }

  function isDashboardPage() {
    return document.body.matches('[data-page="dashboard"], .dashboard-page') ||
      document.querySelector('[data-mobile-pull-refresh], .dashboard-page, .dashboard-mobile') !== null ||
      /(^|\/)dashboards?(\/|$)/.test(window.location.pathname);
  }

  function initPullToRefresh() {
    if (!isDashboardPage()) return;
    var indicator = ensurePullIndicator();
    var startY = 0, pulling = false, distance = 0;
    document.addEventListener('touchstart', function (event) {
      if (window.scrollY !== 0 || event.touches.length !== 1) return;
      startY = event.touches[0].clientY;
      distance = 0;
      pulling = true;
    }, { passive: true });
    document.addEventListener('touchmove', function (event) {
      if (!pulling || event.touches.length !== 1) return;
      distance = event.touches[0].clientY - startY;
      if (distance <= 0) return;
      var visualDistance = Math.min(distance * 0.55, MAX_PULL);
      indicator.classList.add('visible');
      indicator.classList.toggle('ready', distance >= PULL_DISTANCE);
      indicator.style.transform = 'translateY(' + visualDistance + 'px) scale(' + Math.min(1, 0.75 + visualDistance / 160) + ')';
    }, { passive: true });
    document.addEventListener('touchend', function () {
      if (!pulling) return;
      pulling = false;
      if (distance >= PULL_DISTANCE) {
        indicator.classList.add('visible', 'refreshing');
        window.dispatchEvent(new CustomEvent('mobile:pull-to-refresh'));
        window.setTimeout(function () { window.location.reload(); }, 150);
      } else {
        indicator.classList.remove('visible', 'ready', 'refreshing');
        indicator.style.transform = '';
      }
    }, { passive: true });
    document.addEventListener('touchcancel', function () {
      pulling = false;
      indicator.classList.remove('visible', 'ready', 'refreshing');
      indicator.style.transform = '';
    }, { passive: true });
  }

  function initActiveNavTracking() {
    var path = window.location.pathname.replace(/\/$/, '') || '/';
    var bestMatch = null, bestLength = -1;
    document.querySelectorAll('.bottom-nav .nav-item[href], .bottom-nav a[href]').forEach(function (item) {
      var itemPath = new URL(item.getAttribute('href'), window.location.origin).pathname.replace(/\/$/, '') || '/';
      var isMatch = itemPath === '/' ? path === '/' : (path === itemPath || path.indexOf(itemPath + '/') === 0);
      item.classList.remove('active');
      item.removeAttribute('aria-current');
      if (isMatch && itemPath.length > bestLength) { bestMatch = item; bestLength = itemPath.length; }
    });
    if (bestMatch) { bestMatch.classList.add('active'); bestMatch.setAttribute('aria-current', 'page'); }
  }

  function initDoubleTapPrevention() {
    var lastTap = 0;
    document.addEventListener('click', function (event) {
      var target = event.target.closest('button, .btn, .btn-accent, .btn-outline, [role="button"], input[type="submit"], input[type="button"]');
      if (!target) return;
      var now = Date.now();
      if (now - lastTap < DOUBLE_TAP_DELAY) {
        event.preventDefault();
        event.stopPropagation();
        return false;
      }
      lastTap = now;
      return true;
    }, true);
  }

  function initPageTransitions() {
    document.body.classList.add('page-transition-in');
    window.setTimeout(function () { document.body.classList.remove('page-transition-in'); }, 220);
    document.addEventListener('click', function (event) {
      var link = event.target.closest('a[href]');
      if (!link || link.target || link.hasAttribute('download') || event.defaultPrevented) return;
      var url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || (url.pathname === window.location.pathname && url.hash)) return;
      document.body.classList.add('page-transition-out');
    }, true);
  }

  function initSearchDebounce() {
    document.querySelectorAll('.search-bar, input[type="search"][data-mobile-search], input[data-search]').forEach(function (input) {
      var form = input.form;
      var dispatchSearch = debounce(function () {
        input.dispatchEvent(new CustomEvent('mobile:search', { bubbles: true, detail: { query: input.value } }));
        if (input.hasAttribute('data-auto-submit') && form) {
          if (form.requestSubmit) form.requestSubmit();
          else form.submit();
        }
      }, SEARCH_DELAY);
      input.addEventListener('input', dispatchSearch);
    });
  }

  function initMobileUI() {
    initSwipeDetection();
    initPullToRefresh();
    initActiveNavTracking();
    initDoubleTapPrevention();
    initPageTransitions();
    initSearchDebounce();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initMobileUI);
  else initMobileUI();

  window.MobileInventory = { init: initMobileUI, debounce: debounce };
}());
