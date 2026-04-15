import { useState, useEffect } from 'react';

interface MultiSelectPageProps {
  question: { id: string; question: string };
  options: string[][]; // 2D array for column layout
  maxSelections: number;
  customCount: number;
  initialValue?: string; // Comma-separated from answers
  onChange: (value: string) => void; // Returns comma-separated string
}

export function MultiSelectPage({
  question,
  options,
  maxSelections,
  customCount,
  initialValue,
  onChange,
}: MultiSelectPageProps) {
  // Flatten all options for easy checking
  const allOptions = options.flat();
  
  // Parse initial value
  const parseInitial = () => {
    if (!initialValue) return { selected: [], customs: [] };
    const parts = initialValue.split(',').map(s => s.trim()).filter(Boolean);
    const selected = parts.filter(p => allOptions.includes(p));
    const customs = parts.filter(p => !allOptions.includes(p));
    return { selected, customs };
  };
  
  const initial = parseInitial();
  
  const [selectedItems, setSelectedItems] = useState<string[]>(initial.selected);
  const [customValues, setCustomValues] = useState<string[]>(
    Array(customCount).fill('').map((_, i) => initial.customs[i] || '')
  );
  
  // Sync with parent when values change
  useEffect(() => {
    const all = [...selectedItems, ...customValues.filter(Boolean)];
    onChange(all.join(','));
  }, [selectedItems, customValues, onChange]);
  
  const handleToggle = (item: string) => {
    setSelectedItems(prev => {
      if (prev.includes(item)) {
        return prev.filter(i => i !== item);
      } else {
        if (prev.length >= maxSelections) return prev;
        return [...prev, item];
      }
    });
  };
  
  const handleCustomChange = (index: number, value: string) => {
    setCustomValues(prev => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };
  
  const getCustomLabel = (index: number) => {
    if (customCount === 1) return 'Other';
    return index === 0 ? 'Other' : `Other ${index + 1}`;
  };
  
  return (
    <div>
      <p className="font-body font-bold text-[20px] leading-[30px] text-brand-charcoal mb-6">
        {question.question}
      </p>
      
      {/* Selection counter */}
      <p className="font-body text-base text-brand-gray-med mb-4">
        Selected {selectedItems.length} of {maxSelections}
      </p>

      <hr className="border-brand-gray-light mb-6" />

      {/* 3-column checkbox grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-8">
        {options.map((col, colIdx) => (
          <div key={colIdx}>
            {col.map((item) => {
              const checked = selectedItems.includes(item);
              const disabled = !checked && selectedItems.length >= maxSelections;
              return (
                <label
                  key={item}
                  className={`flex items-center gap-3 cursor-pointer leading-[50px] ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <button
                    type="button"
                    onClick={() => !disabled && handleToggle(item)}
                    disabled={disabled}
                    className={`w-6 h-6 rounded-[2px] flex items-center justify-center shrink-0 transition-colors ${
                      checked ? 'bg-brand-gold' : 'bg-brand-gray-light'
                    }`}
                  >
                    {checked && (
                      <svg className="w-4 h-4 text-white" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8l3.5 3.5L13 5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </button>
                  <span className="font-body font-bold text-[20px] text-brand-charcoal">
                    {item}
                  </span>
                </label>
              );
            })}
          </div>
        ))}
      </div>

      {/* Custom "Other" inputs, placed below the full grid for visual consistency */}
      {customCount > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-x-8 mt-4">
          {Array.from({ length: customCount }).map((_, idx) => (
            <div key={idx} className="mt-1 mb-2">
              <label className="flex items-center gap-3 leading-[50px]">
                <div className="w-6 h-6 shrink-0" />
                <span className="font-body font-bold text-[20px] text-brand-charcoal">
                  {getCustomLabel(idx)}
                </span>
              </label>
              <input
                type="text"
                value={customValues[idx]}
                onChange={(e) => handleCustomChange(idx, e.target.value)}
                className="w-[301px] h-[34px] bg-brand-gray-lightest border border-brand-gray-light rounded px-2 font-body text-base text-brand-charcoal focus:outline-none focus:border-brand-teal ml-9"
                placeholder=""
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
