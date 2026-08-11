document.addEventListener('DOMContentLoaded', () => {
  const banner = document.getElementById('cookie-consent');
  if (!banner) return;

  const consent = localStorage.getItem('cookie_consent');
  if (!consent) {
    banner.hidden = false;
  }

  banner.querySelectorAll('[data-cookie-action]').forEach((button) => {
    button.addEventListener('click', () => {
      const action = button.dataset.cookieAction;
      localStorage.setItem('cookie_consent', action === 'accept' ? 'accepted' : 'rejected');
      banner.hidden = true;
    });
  });
});
