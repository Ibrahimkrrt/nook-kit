import { createContext, useCallback, useContext, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Check, Info, TriangleAlert } from 'lucide-react';
import { spring } from '../motion.js';

const ToastCtx = createContext(null);
const ICONS = { ok: Check, danger: TriangleAlert, info: Info };

export function ToastProvider({ children }) {
  const [list, setList] = useState([]);
  const n = useRef(0);
  const dismiss = useCallback((id) => setList((l) => l.filter((t) => t.id !== id)), []);
  const toast = useCallback((t) => {
    const id = ++n.current;
    const item = typeof t === 'string' ? { title: t } : t;
    setList((l) => [...l.slice(-2), { id, tone: 'ok', ...item }]);
    setTimeout(() => dismiss(id), item.duration || 3200);
    return id;
  }, [dismiss]);

  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className="nk-toasts" aria-live="polite">
        <AnimatePresence initial={false}>
          {list.map((t) => {
            const Icon = t.icon || ICONS[t.tone] || Info;
            return (
              <motion.div
                key={t.id} layout className="nk-toast" data-tone={t.tone} role={t.tone === 'danger' ? 'alert' : 'status'}
                initial={{ opacity: 0, y: 24, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1, transition: spring.snappy }}
                exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.15 } }}
                onClick={() => dismiss(t.id)}
              >
                <span className="nk-toast-ico">{t.art || <Icon aria-hidden="true" />}</span>
                <div>{t.title}{t.description && <small>{t.description}</small>}</div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}

/** const toast = useToast(); toast({ title: 'Saved', description: '…', tone: 'ok' | 'danger' | 'info' }) */
export function useToast() {
  const t = useContext(ToastCtx);
  if (!t) throw new Error('useToast needs <NookProvider>');
  return t;
}
