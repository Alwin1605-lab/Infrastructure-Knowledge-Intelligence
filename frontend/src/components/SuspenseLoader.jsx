import React from 'react';
import { Loader2 } from 'lucide-react';

export const SuspenseLoader = () => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-[50vh]">
      <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-4" />
      <p className="text-slate-500 font-medium">Loading module...</p>
    </div>
  );
};
