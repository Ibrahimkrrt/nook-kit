import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { spring } from '../motion.js';

/**
 * Context menus: right click on desktop, long-press on touch, Shift+F10 / Menu key on the keyboard.
 *
 *   const menu = useContextMenu();
 *   <li {...menu.bind(() => [
 *     { label: 'Open', icon: Eye, onSelect: open, hint: 'Enter' },
 *     '-',                                         // separator
 *     { heading: 'Move to' },                      // small label
 *     { label: 'Delete', icon: Trash2, danger: true, onSelect: remove },
 *   ])}>
 *   <IconButton icon={Ellipsis} label="More" onClick={(e) => menu.openAt(e.currentTarget, items)} />
 *
 * Items are computed when the menu opens (pass a function), so they always see fresh state.
 * Always offer the same actions somewhere visible too (a "More" button): a menu is a shortcut.
 */
const MenuCtx = createContext(null);

// Leave the browser's own menu alone where it's useful: text fields (paste, spellcheck), selected text
// (copy), and Shift+Alt+right-click as an escape hatch.
function native(e) {
  if (e.shiftKey && e.altKey) return true;
  if (e.target.closest?.('input, textarea, select, [contenteditable=""], [contenteditable="true"]')) return true;
  const sel = window.getSelection?.();
  return !!(sel && !sel.isCollapsed && e.currentTarget.contains(sel.anchorNode) && e.type === 'contextmenu');
}
const LONG_PRESS = 480;
let swallowUntil = 0; // a long-press opened a menu: swallow the click that follows the finger lifting

export function MenuProvider({ children }) {
  const [menu, setMenu] = useState(null); // { x, y, items, from }
  const close = useCallback(() => setMenu(null), []);

  const open = useCallback((x, y, items, from) => {
    const list = (typeof items === 'function' ? items() : items)?.filter(Boolean);
    if (!list?.length) return;
    setMenu({ x, y, items: list, from: from || document.activeElement, key: Date.now() });
  }, []);

  const api = useMemo(() => {
    const openAt = (el, items, from = el) => {
      const r = el.getBoundingClientRect();
      open(r.left, r.bottom + 6, items, from);
    };
    // what gets focus back when the menu closes: the focusable thing that was clicked, or the row itself
    const origin = (e) => e.target.closest?.('button, a[href], input, select, textarea, [tabindex]') || e.currentTarget;
    const bind = (items) => {
      let timer = null;
      let start = null;
      const cancel = () => { clearTimeout(timer); timer = null; };
      return {
        onContextMenu: (e) => {
          if (e.nativeEvent.nkMenu || native(e)) return; // an inner element already handled it / text editing
          e.nativeEvent.nkMenu = true;
          e.preventDefault();
          cancel();
          // keyboard-triggered contextmenu events come with (0,0): place it on the element instead
          if (e.clientX === 0 && e.clientY === 0) openAt(e.currentTarget, items, origin(e));
          else open(e.clientX, e.clientY, items, origin(e));
        },
        onKeyDown: (e) => {
          if (e.nativeEvent.nkMenu || native(e)) return;
          if ((e.key === 'F10' && e.shiftKey) || e.key === 'ContextMenu') {
            e.nativeEvent.nkMenu = true;
            e.preventDefault();
            openAt(e.currentTarget, items, origin(e));
          }
        },
        // iOS has no contextmenu event: long-press opens the menu (Android fires contextmenu itself)
        onTouchStart: (e) => {
          if (e.nativeEvent.nkMenu || e.touches.length > 1 || native(e)) return;
          e.nativeEvent.nkMenu = true; // nested bound elements: the innermost one wins
          const t = e.touches[0];
          start = { x: t.clientX, y: t.clientY };
          const target = origin(e);
          cancel();
          timer = setTimeout(() => {
            timer = null;
            swallowUntil = Date.now() + 800;
            navigator.vibrate?.(8);
            open(start.x, start.y, items, target);
          }, LONG_PRESS);
        },
        onTouchMove: (e) => {
          const t = e.touches[0];
          if (start && Math.hypot(t.clientX - start.x, t.clientY - start.y) > 10) cancel();
        },
        onTouchEnd: cancel,
        onClickCapture: (e) => {
          if (Date.now() > swallowUntil) return;
          swallowUntil = 0;
          e.preventDefault();
          e.stopPropagation();
        },
        onTouchCancel: cancel,
      };
    };
    return { open, openAt, bind, close };
  }, [open, close]);

  return (
    <MenuCtx.Provider value={api}>
      {children}
      {createPortal(
        <AnimatePresence>{menu && <MenuPanel key={menu.key} menu={menu} onClose={close} />}</AnimatePresence>,
        document.body,
      )}
    </MenuCtx.Provider>
  );
}

function MenuPanel({ menu, onClose }) {
  const panel = useRef(null);
  const [pos, setPos] = useState({ left: menu.x, top: menu.y, origin: 'top left' });
  const enabled = () => [...(panel.current?.querySelectorAll('[role="menuitem"]:not([aria-disabled="true"])') || [])];

  // keep it on screen: flip left/up when there's no room
  useLayoutEffect(() => {
    const el = panel.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const pad = 8;
    let left = menu.x, top = menu.y, ox = 'left', oy = 'top';
    if (left + width > innerWidth - pad) { left = Math.max(pad, menu.x - width); ox = 'right'; }
    if (top + height > innerHeight - pad) { top = Math.max(pad, menu.y - height); oy = 'bottom'; }
    left = Math.min(Math.max(pad, left), innerWidth - width - pad); // never off screen, whatever happens
    top = Math.min(Math.max(pad, top), innerHeight - height - pad);
    setPos({ left, top, origin: `${oy} ${ox}` });
    el.focus({ preventScroll: true });
  }, [menu]);

  useEffect(() => {
    const from = menu.from;
    const away = (e) => { if (!panel.current?.contains(e.target)) onClose(); };
    const quit = () => onClose();
    document.addEventListener('pointerdown', away, true);
    window.addEventListener('blur', quit);
    window.addEventListener('resize', quit);
    window.addEventListener('scroll', quit, true);
    return () => {
      document.removeEventListener('pointerdown', away, true);
      window.removeEventListener('blur', quit);
      window.removeEventListener('resize', quit);
      window.removeEventListener('scroll', quit, true);
      if (from?.isConnected && (!document.activeElement || document.activeElement === document.body)) from.focus?.({ preventScroll: true });
    };
  }, [menu, onClose]);

  const move = (dir) => {
    const els = enabled();
    if (!els.length) return;
    const i = els.indexOf(document.activeElement);
    const next = dir === 'first' ? 0 : dir === 'last' ? els.length - 1 : (i + dir + els.length) % els.length;
    els[i < 0 && dir === -1 ? els.length - 1 : next].focus();
  };

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); move(document.activeElement === panel.current ? 'first' : 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); move(document.activeElement === panel.current ? 'last' : -1); }
    else if (e.key === 'Home') { e.preventDefault(); move('first'); }
    else if (e.key === 'End') { e.preventDefault(); move('last'); }
    else if (e.key === 'Escape' || e.key === 'Tab') { e.preventDefault(); e.stopPropagation(); giveBack(); onClose(); }
    else if (e.key.length === 1 && /\S/.test(e.key)) {
      const hit = enabled().find((el) => el.textContent.trim().toLowerCase().startsWith(e.key.toLowerCase()));
      hit?.focus();
    }
  };

  // focus goes straight back to where the menu came from (not after the exit animation)
  const giveBack = () => { if (menu.from?.isConnected) menu.from.focus?.({ preventScroll: true }); };

  const pick = (item) => {
    if (item.disabled) return;
    giveBack();
    onClose();
    // after the menu is gone, so a sheet opened by the action gets focus
    requestAnimationFrame(() => item.onSelect?.());
  };

  return (
    <motion.div
      ref={panel} className="nk-menu" role="menu" tabIndex={-1} onKeyDown={onKeyDown}
      onContextMenu={(e) => e.preventDefault()}
      style={{ left: pos.left, top: pos.top, transformOrigin: pos.origin }}
      initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1, transition: spring.snappy }}
      exit={{ opacity: 0, scale: 0.97, transition: { duration: 0.1 } }}
    >
      {menu.items.map((item, i) => {
        if (item === '-') return <div key={i} className="nk-menu-sep" role="separator" />;
        if (item.heading) return <div key={i} className="nk-menu-head">{item.heading}</div>;
        const Icon = item.icon;
        return (
          <div
            key={i} role="menuitem" tabIndex={-1} className="nk-menu-item"
            data-danger={item.danger ? '' : undefined} aria-disabled={item.disabled || undefined}
            onClick={() => pick(item)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(item); } }}
            onPointerMove={(e) => !item.disabled && e.currentTarget.focus({ preventScroll: true })}
          >
            {Icon ? <Icon aria-hidden="true" /> : <span className="nk-menu-gap" />}
            <span className="nk-menu-label">{item.label}</span>
            {item.hint && <kbd className="nk-menu-hint">{item.hint}</kbd>}
          </div>
        );
      })}
    </motion.div>
  );
}

/** { bind(items), openAt(element, items), open(x, y, items), close() } */
export function useContextMenu() {
  const c = useContext(MenuCtx);
  if (!c) throw new Error('useContextMenu needs <NookProvider>');
  return c;
}
