// Soft navigation for SPA-like behavior: intercept internal links/forms, swap #content-root, preserve audio
(function(){
  function isSameOrigin(url) {
    try {
      const u = new URL(url, window.location.href);
      return u.origin === window.location.origin;
    } catch (_) { return false; }
  }

  function shouldBypassLink(a) {
    if (a.hasAttribute('data-no-ajax')) return true;
    if (a.target && a.target !== '' && a.target !== '_self') return true;
    const href = a.getAttribute('href') || '';
    if (!href || href.startsWith('#')) return true;
    if (href.startsWith('mailto:') || href.startsWith('tel:')) return true;
    if (!isSameOrigin(href)) return true;
    return false;
  }

  function executeScripts(container) {
    // Execute any scripts inside the new content by recreating them
    const scripts = Array.from(container.querySelectorAll('script'));
    for (const oldScript of scripts) {
      const s = document.createElement('script');
      if (oldScript.src) {
        s.src = oldScript.src;
      } else {
        s.textContent = oldScript.textContent;
      }
      // transfer attributes like type
      if (oldScript.type) s.type = oldScript.type;
      oldScript.replaceWith(s);
    }
  }

  async function loadUrl(url, options) {
    const resp = await fetch(url, Object.assign({
      method: 'GET',
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    }, options || {}));
    const text = await resp.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, 'text/html');
    const newRoot = doc.querySelector('#content-root');
    const oldRoot = document.querySelector('#content-root');
    if (newRoot && oldRoot) {
      oldRoot.replaceWith(newRoot);
      // run inline scripts in the swapped content
      executeScripts(newRoot);
      // notify app scripts to rebind
      window.dispatchEvent(new CustomEvent('content:loaded', { detail: { url } }));
      // scroll to top for new view
      window.scrollTo({ top: 0, behavior: 'instant' });
    } else {
      // Fallback: full navigation
      window.location.href = url;
    }
  }

  function attachLinkInterception() {
    document.addEventListener('click', function(e) {
      const a = e.target.closest('a');
      if (!a) return;
      if (e.defaultPrevented) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (shouldBypassLink(a)) return;
      const href = a.getAttribute('href');
      e.preventDefault();
      const targetUrl = new URL(href, window.location.href).toString();
      history.pushState({ url: targetUrl }, '', targetUrl);
      loadUrl(targetUrl).catch(() => window.location.href = targetUrl);
    });
  }

  function attachFormInterception() {
    document.addEventListener('submit', function(e) {
      const form = e.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (form.hasAttribute('data-no-ajax')) return;
      // Skip file uploads
      if ((form.enctype || '').toLowerCase() === 'multipart/form-data') return;
      // Only same-origin
      const action = form.getAttribute('action') || window.location.href;
      if (!isSameOrigin(action)) return;

      e.preventDefault();
      const method = (form.getAttribute('method') || 'GET').toUpperCase();
      const formData = new FormData(form);
      if (method === 'GET') {
        const url = new URL(action, window.location.href);
        // merge existing params and form params
        formData.forEach((v, k) => url.searchParams.set(k, v));
        const targetUrl = url.toString();
        history.pushState({ url: targetUrl }, '', targetUrl);
        loadUrl(targetUrl).catch(() => window.location.href = targetUrl);
      } else {
        const targetUrl = new URL(action, window.location.href).toString();
        history.pushState({ url: targetUrl }, '', targetUrl);
        loadUrl(targetUrl, { method: method, body: formData }).catch(() => window.location.href = targetUrl);
      }
    });
  }

  function attachPopState() {
    window.addEventListener('popstate', function(e) {
      const url = (e.state && e.state.url) ? e.state.url : window.location.href;
      loadUrl(url).catch(() => {/* ignore, browser URL already set */});
    });
  }

  document.addEventListener('DOMContentLoaded', function() {
    attachLinkInterception();
    attachFormInterception();
    attachPopState();
  });
})();
