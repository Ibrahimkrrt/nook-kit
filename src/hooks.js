import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'motion/react';
import { store } from './api.js';

/** Types `text` out letter by letter. Returns [shown, done]. Instant under reduced motion. */
export function useTypewriter(text = '', speed = 22) {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? text.length : 0);
  useEffect(() => {
    if (reduce) { setN(text.length); return; }
    setN(0);
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setN(i);
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed, reduce]);
  return [text.slice(0, n), n >= text.length];
}

/** setInterval that always calls the latest callback; pass null to pause. */
export function useInterval(fn, ms) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    if (ms == null) return;
    const id = setInterval(() => saved.current(), ms);
    return () => clearInterval(id);
  }, [ms]);
}

/** Poll an async function every `ms` while mounted. Errors go to onError, polling continues. */
export function usePoll(fn, ms, deps = []) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    let alive = true, timer;
    const tick = async () => {
      try { await saved.current(); } catch { /* caller handles its own errors */ }
      if (alive) timer = setTimeout(tick, ms);
    };
    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [ms, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps
}

/** useState that survives reloads (per browser), via the safe `store`. */
export function useStoredState(key, initial) {
  const [value, setValue] = useState(() => store.get(key, initial));
  const set = (v) => { setValue(v); store.set(key, v); };
  return [value, set];
}

/** A short-lived value, e.g. a mascot reaction that should wear off. */
export function useFlash(ms = 2400) {
  const [value, setValue] = useState(null);
  const timer = useRef();
  const flash = (v) => {
    clearTimeout(timer.current);
    setValue(v);
    timer.current = setTimeout(() => setValue(null), ms);
  };
  useEffect(() => () => clearTimeout(timer.current), []);
  return [value, flash];
}
