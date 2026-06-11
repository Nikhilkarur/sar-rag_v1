
export function RiskGauge({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 34; // 213.6
  const offset = circumference - (score / 100) * circumference;
  
  let color = '#00CC66';
  if (score >= 75) color = '#FF4444';
  else if (score >= 50) color = '#FFBB00';

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-[80px] h-[80px]">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 80 80">
          <circle
            cx="40" cy="40" r="34"
            fill="none"
            stroke="#1E1E1E"
            strokeWidth="6"
          />
          <circle
            cx="40" cy="40" r="34"
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-800 ease-out"
            style={{ animation: 'drawArc 800ms ease-out forwards' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-[18px] font-semibold" style={{ color }}>
            {score}
          </span>
        </div>
      </div>
      <span className="mt-2 text-[9px] font-mono uppercase text-ink-3 tracking-widest">Risk Score</span>
      
      {/* Required style for the draw animation */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes drawArc {
          from { stroke-dashoffset: ${circumference}; }
          to { stroke-dashoffset: ${offset}; }
        }
      `}} />
    </div>
  );
}
