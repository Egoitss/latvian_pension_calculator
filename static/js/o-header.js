/* o-header.js — drives the shared OATS header's drawer.
   Byte-identical on oats.lv, pension.oats.lv and bmx.oats.lv. The
   estimator is React and reimplements this behaviour in App.tsx;
   tests/test_shell.py guards the two from drifting apart.

   No inline handlers anywhere: bmx and pension both serve
   script-src 'self', so an inline onclick would be blocked. */
(function () {
  var burger = document.querySelector('.o-hdr-burger');
  var drawer = document.getElementById('o-drawer');
  var backdrop = document.querySelector('.o-drawer-backdrop');
  if (!burger || !drawer || !backdrop) return;

  var body = document.body;
  var scrollY = 0;
  var hideTimer = null;

  /* Tabbable children, recomputed per open: the language pill's
     active side renders as a non-focusable span on some properties
     and as a disabled button on others. offsetParent filters out
     anything a media query has hidden. */
  function focusables() {
    var all = drawer.querySelectorAll('a[href], button:not([disabled])');
    return Array.prototype.filter.call(all, function (el) {
      return el.offsetParent !== null;
    });
  }

  function isOpen() {
    return body.classList.contains('o-drawer-open');
  }

  /* Freeze the page behind the drawer. position:fixed is the only
     lock iOS Safari honours, so the offset is saved and restored by
     hand: without that the page snaps to the top on close. */
  function lockScroll() {
    scrollY = window.scrollY;
    body.style.position = 'fixed';
    body.style.top = -scrollY + 'px';
    body.style.width = '100%';
  }

  function unlockScroll() {
    body.style.position = '';
    body.style.top = '';
    body.style.width = '';
    window.scrollTo(0, scrollY);
  }

  function open() {
    if (isOpen()) return;
    clearTimeout(hideTimer);
    drawer.hidden = false;
    backdrop.hidden = false;
    /* Force a reflow while the panel is still translated off-screen.
       Without it the browser coalesces "unhide" and "add class" into
       one style pass and the drawer appears already open. */
    void drawer.offsetWidth;
    body.classList.add('o-drawer-open');
    burger.setAttribute('aria-expanded', 'true');
    drawer.setAttribute('aria-hidden', 'false');
    lockScroll();
    var first = focusables()[0];
    if (first) first.focus();
  }

  /* restoreFocus is false when the drawer closes because the user is
     navigating away or the viewport crossed the breakpoint. Pulling
     focus back to a burger that is about to vanish is worse than
     leaving it where the browser put it. */
  function close(restoreFocus) {
    if (!isOpen()) return;
    body.classList.remove('o-drawer-open');
    burger.setAttribute('aria-expanded', 'false');
    drawer.setAttribute('aria-hidden', 'true');
    unlockScroll();
    if (restoreFocus !== false) burger.focus();
    /* Hide only after the slide-out has played, so the panel does not
       vanish mid-transition. Re-checked on fire in case it was
       reopened in the meantime. */
    hideTimer = setTimeout(function () {
      if (!isOpen()) {
        drawer.hidden = true;
        backdrop.hidden = true;
      }
    }, 220);
  }

  /* Keeps Tab inside the panel while it is open: the page behind it
     is inert to the eye but not to the keyboard. */
  function trap(e) {
    var items = focusables();
    if (!items.length) return;
    var first = items[0];
    var last = items[items.length - 1];
    if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    } else if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  }

  burger.addEventListener('click', function () {
    if (isOpen()) close();
    else open();
  });

  backdrop.addEventListener('click', function () { close(); });

  drawer.addEventListener('click', function (e) {
    if (e.target.closest('a[href]')) close(false);
  });

  document.addEventListener('keydown', function (e) {
    if (!isOpen()) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'Tab') trap(e);
  });

  /* Above the breakpoint the links are inline and the burger is gone,
     so a drawer left open would strand the scroll lock. */
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 768) close(false);
  });
})();
