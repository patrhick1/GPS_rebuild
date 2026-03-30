export function Footer() {
  return (
    <footer className="w-full bg-brand-charcoal h-14 flex items-center justify-center">
      <a
        href="/update-locale?locale=es"
        className="font-body text-sm text-white underline hover:text-brand-teal-light transition-colors"
      >
        ¿En español?
      </a>
    </footer>
  );
}
