(function () {
  'use strict';

  function initAdminFlash() {
    document.querySelectorAll('.admin-main .flash:not([data-flash-init])').forEach((flash) => {
      flash.dataset.flashInit = '1';
      const dismiss = () => {
        flash.style.opacity = '0';
        flash.style.transform = 'translateX(100%)';
        flash.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        setTimeout(() => {
          flash.remove();
          const container = document.getElementById('adminFlashContainer');
          if (container && !container.querySelector('.flash')) container.remove();
        }, 300);
      };
      flash.querySelector('.flash-close')?.addEventListener('click', dismiss);
      setTimeout(dismiss, 4000);
    });
  }

  function prefetchAdminLinks() {
    document.querySelectorAll('.admin-sidebar a[href^="/admin"]').forEach((link) => {
      if (link.dataset.prefetchBound) return;
      link.dataset.prefetchBound = '1';
      link.addEventListener(
        'mouseenter',
        () => {
          if (document.querySelector(`link[rel="prefetch"][href="${link.href}"]`)) return;
          const hint = document.createElement('link');
          hint.rel = 'prefetch';
          hint.href = link.href;
          document.head.appendChild(hint);
        },
        { once: true, passive: true }
      );
    });
  }

  function initMobileSidebar() {
    const body = document.body;
    if (!body.classList.contains('admin-body')) return;

    const menuBtn = document.getElementById('adminMenuBtn');
    const bottomMenuBtn = document.getElementById('adminBottomMenuBtn');
    const overlay = document.getElementById('adminSidebarOverlay');
    const sidebar = document.getElementById('adminSidebar');
    const mq = window.matchMedia('(max-width: 900px)');

    if (!sidebar) return;

    const isMobile = () => mq.matches;

    const setOpen = (open) => {
      body.classList.toggle('sidebar-open', open);
      menuBtn?.setAttribute('aria-expanded', open ? 'true' : 'false');
      overlay?.setAttribute('tabindex', open ? '0' : '-1');
    };

    const toggle = () => setOpen(!body.classList.contains('sidebar-open'));
    const close = () => setOpen(false);

    menuBtn?.addEventListener('click', toggle);
    bottomMenuBtn?.addEventListener('click', toggle);
    overlay?.addEventListener('click', close);

    sidebar.querySelectorAll('nav a[href]').forEach((link) => {
      link.addEventListener('click', () => {
        if (isMobile()) close();
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && body.classList.contains('sidebar-open')) {
        e.preventDefault();
        close();
        menuBtn?.focus();
      }
    });

    mq.addEventListener('change', (e) => {
      if (!e.matches) close();
    });

    window.addEventListener('resize', () => {
      if (!isMobile()) close();
    });
  }

  function onPageReady() {
    initAdminFlash();
    prefetchAdminLinks();
    initMobileSidebar();
  }

  document.addEventListener('DOMContentLoaded', onPageReady);
})();
(function () {
  'use strict';

  function initAdminFlash() {
    document.querySelectorAll('.admin-main .flash:not([data-flash-init])').forEach((flash) => {
      flash.dataset.flashInit = '1';
      const dismiss = () => {
        flash.style.opacity = '0';
        flash.style.transform = 'translateX(100%)';
        flash.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        setTimeout(() => {
          flash.remove();
          const container = document.getElementById('adminFlashContainer');
          if (container && !container.querySelector('.flash')) container.remove();
        }, 300);
      };
      flash.querySelector('.flash-close')?.addEventListener('click', dismiss);
      setTimeout(dismiss, 4000);
    });
  }

  function prefetchAdminLinks() {
    document.querySelectorAll('.admin-sidebar a[href^="/admin"]').forEach((link) => {
      if (link.dataset.prefetchBound) return;
      link.dataset.prefetchBound = '1';
      link.addEventListener(
        'mouseenter',
        () => {
          if (document.querySelector(`link[rel="prefetch"][href="${link.href}"]`)) return;
          const hint = document.createElement('link');
          hint.rel = 'prefetch';
          hint.href = link.href;
          document.head.appendChild(hint);
        },
        { once: true, passive: true }
      );
    });
  }

  function initMobileSidebar() {
    const body = document.body;
    if (!body.classList.contains('admin-body')) return;

    const menuBtn = document.getElementById('adminMenuBtn');
    const bottomMenuBtn = document.getElementById('adminBottomMenuBtn');
    const overlay = document.getElementById('adminSidebarOverlay');
    const sidebar = document.getElementById('adminSidebar');
    const mq = window.matchMedia('(max-width: 900px)');

    if (!sidebar) return;

    const isMobile = () => mq.matches;

    const setOpen = (open) => {
      body.classList.toggle('sidebar-open', open);
      menuBtn?.setAttribute('aria-expanded', open ? 'true' : 'false');
      overlay?.setAttribute('tabindex', open ? '0' : '-1');
    };

    const toggle = () => setOpen(!body.classList.contains('sidebar-open'));
    const close = () => setOpen(false);

    menuBtn?.addEventListener('click', toggle);
    bottomMenuBtn?.addEventListener('click', toggle);
    };

    const toggle = () => setOpen(!body.classList.contains('sidebar-open'));
    const close = () => setOpen(false);
    const open = () => {
      if (isMobile()) setOpen(true);
    };

    menuBtn?.addEventListener('click', toggle);
    bottomMenuBtn?.addEventListener('click', toggle);
    overlay?.addEventListener('click', close);

    sidebar.querySelectorAll('nav a[href]').forEach((link) => {
      link.addEventListener('click', () => {
        if (isMobile()) close();
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && body.classList.contains('sidebar-open')) {
        e.preventDefault();
        close();
        menuBtn?.focus();
      }
    });

    mq.addEventListener('change', (e) => {
      if (!e.matches) close();
    });

    window.addEventListener('resize', () => {
      if (!isMobile()) close();
    });
  }

  function onPageReady() {
    initAdminFlash();
    prefetchAdminLinks();
    initMobileSidebar();
  }

  document.addEventListener('DOMContentLoaded', onPageReady);
    });
  }

  function onPageReady() {
    initAdminFlash();
    prefetchAdminLinks();
  }

  document.addEventListener('DOMContentLoaded', onPageReady);
})();
  document.addEventListener('DOMContentLoaded', onPageReady);
  document.addEventListener('turbo:load', onPageReady);
  document.addEventListener('turbo:render', onPageReady);
})();