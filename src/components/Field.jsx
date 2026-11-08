import { cloneElement, forwardRef, isValidElement, useId } from 'react';

/**
 * Label + control + hint/error, wired for accessibility.
 *   <Field label="Username" hint="3–24 letters"><Input /></Field>
 */
export function Field({ label, aside, hint, error, children, className = '' }) {
  const id = useId();
  const hintId = hint || error ? `${id}-hint` : undefined;
  const control = isValidElement(children)
    ? cloneElement(children, { id: children.props.id || id, 'aria-describedby': hintId, 'aria-invalid': error ? true : undefined })
    : children;
  return (
    <div className={`nk-field ${className}`}>
      {label && <label className="nk-label" htmlFor={children?.props?.id || id}>{label}{aside && <small>{aside}</small>}</label>}
      {control}
      {error ? <span className="nk-error" id={hintId} role="alert">{error}</span> : hint && <span className="nk-hint" id={hintId}>{hint}</span>}
    </div>
  );
}

/** Text input. `icon` puts a leading icon inside it. */
export const Input = forwardRef(function Input({ icon: Icon, className = '', ...rest }, ref) {
  const input = <input ref={ref} className={`nk-input ${className}`} {...rest} />;
  if (!Icon) return input;
  return <div className="nk-input-wrap"><Icon aria-hidden="true" />{input}</div>;
});

export const Select = forwardRef(function Select({ className = '', children, ...rest }, ref) {
  return <select ref={ref} className={`nk-select ${className}`} {...rest}>{children}</select>;
});
