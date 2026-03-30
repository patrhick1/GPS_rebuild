import heroImg from '../../Graphics for Dev/Images/Hero.webp';
import downArrow from '../../Graphics for Dev/Icons/White Down Arrow.svg';

export function HeroBanner() {
  return (
    <div className="relative w-full h-[420px] overflow-hidden">
      {/* Background image */}
      <img
        src={heroImg}
        alt=""
        className="absolute inset-0 w-full h-full object-cover object-center"
      />

      {/* Dark overlay */}
      <div className="absolute inset-0 bg-black/30" />

      {/* Centered content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-6">
        <h1 className="font-heading font-bold italic text-4xl lg:text-5xl text-white leading-tight mb-3">
          Grow in Character and Calling
        </h1>
        <p className="font-body text-lg lg:text-xl text-white leading-relaxed max-w-xl">
          Create Your Account. Measure What Matters.<br />
          Multiply Your Impact.
        </p>
        <img src={downArrow} alt="" className="mt-4 w-5 h-5 animate-bounce" />
      </div>
    </div>
  );
}
