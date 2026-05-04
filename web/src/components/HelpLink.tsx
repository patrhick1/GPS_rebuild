/**
 * "Help" link in the platform navigation. Opens a pre-addressed email; no
 * backend, no auth required. Visible to all roles per the v2.1 addendum.
 *
 * Why a constant subject: per the addendum spec, the receiving inbox
 * (info@disciplesmade.com) wants to filter / route incoming help requests
 * by subject prefix.
 */
const HELP_MAILTO =
  'mailto:info@disciplesmade.com?subject=GPS%20Platform%20Help%20Request';

interface HelpLinkProps {
  /** Tailwind classes overriding the default styling. Lets the Navbar render
   * it as an inline link and the mobile menu render it as a stacked button. */
  className?: string;
  label?: string;
}

export function HelpLink({ className, label = 'Help' }: HelpLinkProps) {
  return (
    <a
      href={HELP_MAILTO}
      className={
        className ??
        'font-body font-bold text-sm text-brand-charcoal/80 hover:text-brand-teal transition-colors'
      }
    >
      {label}
    </a>
  );
}
