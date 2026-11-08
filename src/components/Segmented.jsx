import { useId } from 'react';
import { motion } from 'motion/react';
import { spring } from '../motion.js';

/**
 * A row of mutually exclusive options with a sliding pill.
 *   <Segmented value={fmt} onChange={setFmt} label="Format"
 *     options={[{ value: 'mp4', label: 'Video', icon: Film }, …]} />
 */
export function Segmented({ value, onChange, options, label, size }) {
  const id = useId();
  return (
    <div className="nk-seg" role="group" aria-label={label} data-size={size}>
      {options.map((o) => {
        const on = o.value === value;
        const Icon = o.icon;
        return (
          <button key={o.value} type="button" aria-pressed={on} onClick={() => onChange(o.value)} title={o.title}>
            {on && <motion.span layoutId={`seg-${id}`} className="nk-seg-pill" transition={spring.snappy} />}
            {Icon && <Icon aria-hidden="true" />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
