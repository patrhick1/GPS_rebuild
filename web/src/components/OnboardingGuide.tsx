import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface OnboardingGuideProps {
  firstName: string;
  onDismiss: () => void;
}

const STEPS = [
  {
    title: 'Discover Your Spiritual Gifts',
    description:
      'The GPS Assessment helps you identify your God-given spiritual gifts and passions. You\'ll answer questions across several categories and receive a personalized profile of your top gifts and passions.',
    cta: 'Start GPS Assessment',
    route: '/assessment',
    accent: 'bg-brand-teal',
    icon: (
      <svg viewBox="0 0 48 48" fill="none" className="w-12 h-12">
        <circle cx="24" cy="24" r="22" stroke="#0B6C80" strokeWidth="2.5" fill="#0B6C80" fillOpacity="0.08" />
        <path d="M24 12v12l8 5" stroke="#0B6C80" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M15 32l3-8 8 3" stroke="#F7A824" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    title: 'Measure Your Impact',
    description:
      'The MyImpact Assessment measures your character and calling on a 0–10 scale. It gives you a clear picture of where you are today and a baseline to track your growth over time.',
    cta: 'Start MyImpact Assessment',
    route: '/myimpact',
    accent: 'bg-brand-gold',
    icon: (
      <svg viewBox="0 0 48 48" fill="none" className="w-12 h-12">
        <circle cx="24" cy="24" r="22" stroke="#F7A824" strokeWidth="2.5" fill="#F7A824" fillOpacity="0.08" />
        <path d="M16 28l5-10 5 6 6-12" stroke="#F7A824" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M16 34h16" stroke="#0B6C80" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    title: 'Connect with Your Church',
    description:
      'Link your results to your church so your pastor or leader can help guide your growth. Search for your church, send a request, and you\'re connected once approved.',
    cta: 'Find My Church',
    route: '/account#church-linking',
    accent: 'bg-brand-teal-light',
    icon: (
      <svg viewBox="0 0 48 48" fill="none" className="w-12 h-12">
        <circle cx="24" cy="24" r="22" stroke="#88C0C3" strokeWidth="2.5" fill="#88C0C3" fillOpacity="0.08" />
        <path d="M24 14v6M20 20h8v12H20V20z" stroke="#0B6C80" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M24 14l-6 6h12l-6-6z" stroke="#0B6C80" strokeWidth="2" strokeLinejoin="round" />
        <rect x="22" y="26" width="4" height="6" rx="0.5" stroke="#0B6C80" strokeWidth="1.5" />
      </svg>
    ),
  },
];

export function OnboardingGuide({ firstName, onDismiss }: OnboardingGuideProps) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);

  const step = STEPS[currentStep];
  const isLast = currentStep === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onDismiss}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-[560px] w-full overflow-hidden">
        {/* Progress bar */}
        <div className="flex gap-1.5 px-6 pt-5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                i <= currentStep ? 'bg-brand-teal' : 'bg-brand-gray-light'
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <div className="px-6 pt-6 pb-2">
          {currentStep === 0 && (
            <p className="font-heading font-medium text-base text-brand-gray-med mb-1">
              Welcome, {firstName}!
            </p>
          )}

          <div className="flex items-start gap-4">
            <div className="shrink-0 mt-1">{step.icon}</div>
            <div>
              <h2 className="font-heading font-black text-xl md:text-2xl text-brand-charcoal">
                {step.title}
              </h2>
              <p className="font-body text-base text-brand-gray-med mt-2 leading-relaxed">
                {step.description}
              </p>
            </div>
          </div>
        </div>

        {/* Step indicator */}
        <p className="px-6 font-body text-sm text-brand-gray-med">
          Step {currentStep + 1} of {STEPS.length}
        </p>

        {/* Actions */}
        <div className="flex items-center justify-between px-6 py-5">
          <button
            onClick={onDismiss}
            className="font-body font-bold text-sm text-brand-gray-med hover:text-brand-charcoal transition-colors"
          >
            Skip guide
          </button>

          <div className="flex gap-3">
            {currentStep > 0 && (
              <button
                onClick={() => setCurrentStep(currentStep - 1)}
                className="h-[42px] px-5 border border-brand-gray-light rounded-xl font-body font-bold text-sm text-brand-charcoal hover:bg-brand-gray-lightest transition-colors"
              >
                Back
              </button>
            )}

            {isLast ? (
              <button
                onClick={onDismiss}
                className="h-[42px] px-6 bg-brand-teal text-white rounded-xl font-body font-bold text-sm hover:bg-brand-teal/90 transition-colors"
              >
                Get Started
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    onDismiss();
                    navigate(step.route);
                  }}
                  className="h-[42px] px-5 border border-brand-teal text-brand-teal rounded-xl font-body font-bold text-sm hover:bg-brand-teal/5 transition-colors"
                >
                  {step.cta}
                </button>
                <button
                  onClick={() => setCurrentStep(currentStep + 1)}
                  className="h-[42px] px-6 bg-brand-teal text-white rounded-xl font-body font-bold text-sm hover:bg-brand-teal/90 transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
