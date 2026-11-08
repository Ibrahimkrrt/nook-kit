import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';
import { spring } from '../motion.js';
import { Button, IconButton } from './Button.jsx';

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Modal sheet: a centred dialog on desktop, a bottom sheet on phones.
 *   <Sheet open={open} onClose={…} title="Edit" description="…" footer={<Button…/>}>…</Sheet>
 * Esc and backdrop clicks close it; focus is trapped inside and restored afterwards.
 */
export function Sheet({ open, onClose, title, description, footer, width, children }) {
  const panel = useRef(null);
  const titleId = useId();
  const close = useRef(onClose);
  close.current = onClose; // a ref, so an inline onClose doesn't re-run the effect (and steal focus) on every render

  useEffect(() => {
    if (!open) return;
    const before = document.activeElement;
    const onKey = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); close.current?.(); }
      if (e.key === 'Tab' && panel.current) {
        const els = [...panel.current.querySelectorAll(FOCUSABLE)];
        if (!els.length) return;
        const first = els[0], last = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', onKey);
    const t = setTimeout(() => {
      const target = panel.current?.querySelector('[data-autofocus]') || panel.current?.querySelector(FOCUSABLE);
      target?.focus();
    }, 30);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      clearTimeout(t);
      document.body.style.overflow = overflow;
      before?.focus?.();
    };
  }, [open]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="nk-backdrop"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}
          onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}
        >
          <motion.div
            ref={panel}
            className="nk-sheet"
            style={width ? { '--sheet-w': `${width}px` } : undefined}
            role="dialog" aria-modal="true" aria-labelledby={title ? titleId : undefined}
            initial={{ opacity: 0, y: 40, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1, transition: spring.smooth }}
            exit={{ opacity: 0, y: 24, scale: 0.98, transition: { duration: 0.15 } }}
          >
            {(title || onClose) && (
              <div className="nk-sheet-head">
                <div>
                  {title && <h2 id={titleId}>{title}</h2>}
                  {description && <p>{description}</p>}
                </div>
                {onClose && <IconButton icon={X} label="Close" variant="ghost" size="sm" onClick={onClose} />}
              </div>
            )}
            {children}
            {footer && <div className="nk-sheet-foot">{footer}</div>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

// ---------- confirm(): a promise-based yes/no dialog ----------
const ConfirmCtx = createContext(null);

export function ConfirmProvider({ children }) {
  const [ask, setAsk] = useState(null);
  const confirm = useCallback((opts) => new Promise((resolve) => setAsk({ ...opts, resolve })), []);
  const answer = (v) => { ask?.resolve(v); setAsk(null); };
  return (
    <ConfirmCtx.Provider value={confirm}>
      {children}
      <Sheet
        open={!!ask} onClose={() => answer(false)} title={ask?.title} description={ask?.description} width={400}
        footer={
          <>
            <Button variant="ghost" onClick={() => answer(false)}>{ask?.cancel || 'Cancel'}</Button>
            <Button variant={ask?.danger ? 'danger' : 'primary'} onClick={() => answer(true)} data-autofocus>
              {ask?.confirm || 'OK'}
            </Button>
          </>
        }
      >
        {ask?.body}
      </Sheet>
    </ConfirmCtx.Provider>
  );
}

/** const confirm = useConfirm(); if (await confirm({ title: 'Delete?', danger: true })) … */
export function useConfirm() {
  const c = useContext(ConfirmCtx);
  if (!c) throw new Error('useConfirm needs <NookProvider>');
  return c;
}
