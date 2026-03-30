import churchIcon from '../../Graphics for Dev/Icons/Church Icon.svg';

export function UpgradeBanner() {
  return (
    <section className="w-full bg-brand-gray-lightest">
      <div className="max-w-6xl mx-auto px-6 py-10 lg:py-12 flex flex-col md:flex-row items-center gap-6 md:gap-8">
        {/* Church icon */}
        <img src={churchIcon} alt="" className="w-16 h-16 shrink-0" />

        {/* Text */}
        <div className="flex-1 text-center md:text-left">
          <h2 className="font-heading font-bold text-xl lg:text-2xl text-brand-charcoal leading-snug">
            Want to track and manage your church's assessment results?
          </h2>
          <p className="font-body text-base text-brand-gray-med mt-1">
            Upgrade to a Church Administrator account.
          </p>
        </div>

        {/* CTA button */}
        <a
          href="/upgrade"
          className="shrink-0 bg-brand-teal text-white font-body font-semibold text-sm rounded-full py-3 px-7 hover:bg-brand-teal/90 transition-colors"
        >
          Upgrade to Church Admin
        </a>
      </div>
    </section>
  );
}
