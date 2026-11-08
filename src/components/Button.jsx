import { forwardRef } from 'react';
import { LoaderCircle } from 'lucide-react';

/**
 * <Button variant="primary|secondary|ghost|danger" size="sm|md|lg" icon={Icon} loading block>
 * Pass `href` to render a link that looks like a button.
 */
export const Button = forwardRef(function Button(
  { variant = 'secondary', size = 'md', icon: Icon, iconEnd: IconEnd, loading, block, href, children, disabled, ...rest },
  ref,
) {
  const props = {
    ref,
    className: `nk-btn ${rest.className || ''}`,
    'data-variant': variant,
    'data-size': size,
    'data-block': block ? '' : undefined,
    'data-icon': !children ? '' : undefined,
    'aria-busy': loading || undefined,
  };
  const inner = (
    <>
      {loading ? <LoaderCircle className="nk-spin" aria-hidden="true" /> : Icon && <Icon aria-hidden="true" />}
      {children}
      {IconEnd && !loading && <IconEnd aria-hidden="true" />}
    </>
  );
  if (href) return <a {...rest} {...props} href={href}>{inner}</a>;
  return <button type="button" {...rest} {...props} disabled={disabled || loading}>{inner}</button>;
});

/** Square button with just an icon. `label` is required (it's what screen readers say). */
export const IconButton = forwardRef(function IconButton({ icon, label, ...rest }, ref) {
  return <Button ref={ref} icon={icon} aria-label={label} title={label} {...rest} />;
});
