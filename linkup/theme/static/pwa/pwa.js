if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).then((reg) => {
      console.debug('[PWA] SW registered:', reg.scope);

      reg.addEventListener('updatefound', () => {
        const sw = reg.installing;
        sw.addEventListener('statechange', () => {
          if (sw.state === 'installed' && navigator.serviceWorker.controller) {
            showUpdateToast();
          }
        });
      });
    }).catch((err) => {
      console.debug('[PWA] SW registration failed:', err);
    });
  });
}

function showUpdateToast() {
  var toast = document.createElement('div');
  toast.id = 'pwa-update-toast';
  toast.setAttribute('role', 'alert');
  toast.style.cssText =
    'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:9999;' +
    'background:#18181b;color:#fafafa;padding:12px 20px;border-radius:12px;' +
    'box-shadow:0 8px 32px rgba(0,0,0,0.25);display:flex;align-items:center;gap:12px;' +
    'font-size:14px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;' +
    'animation:ptoast-in 0.35s ease both;max-width:90vw;';
  toast.innerHTML =
    '<span>An update is available.</span>' +
    '<button onclick="applyUpdate()" style="background:#7c3aed;color:#fff;border:none;' +
    'padding:6px 16px;border-radius:8px;font-weight:600;font-size:13px;cursor:pointer;' +
    'white-space:nowrap">Update</button>';

  var style = document.createElement('style');
  style.textContent =
    '@keyframes ptoast-in{from{opacity:0;transform:translateX(-50%) translateY(16px)}' +
    'to{opacity:1;transform:translateX(-50%) translateY(0)}}';
  document.head.appendChild(style);
  document.body.appendChild(toast);
}

window.applyUpdate = function () {
  if (navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
  }
  window.location.reload();
};

let swRegForPush = null;
navigator.serviceWorker.ready.then((reg) => {
  swRegForPush = reg;
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    window.location.reload();
  });
}
