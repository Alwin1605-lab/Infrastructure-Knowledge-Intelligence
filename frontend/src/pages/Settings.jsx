import React from 'react';
import { useSettingsStore } from '../store/useSettingsStore';
import { Card } from '../components/ui';
import { Settings2, Bell, Moon, Sun, Globe, Scale } from 'lucide-react';

export function Settings() {
  const settings = useSettingsStore();

  return (
    <div className="p-8 max-w-4xl mx-auto w-full">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Platform Settings</h1>
        <p className="text-slate-500 mt-1 text-lg">Manage your engineering preferences and application behavior.</p>
      </div>

      <div className="space-y-6">
        <Card className="p-6">
          <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
            <Scale className="w-5 h-5 text-blue-600" />
            Engineering Preferences
          </h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Unit System</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input type="radio" name="units" checked={settings.engineeringUnits === 'metric'} onChange={() => settings.setEngineeringUnits('metric')} className="text-blue-600 focus:ring-blue-500" />
                  <span className="text-slate-700 font-medium">Metric (SI)</span>
                </label>
                <label className="flex items-center gap-2">
                  <input type="radio" name="units" checked={settings.engineeringUnits === 'imperial'} onChange={() => settings.setEngineeringUnits('imperial')} className="text-blue-600 focus:ring-blue-500" />
                  <span className="text-slate-700 font-medium">Imperial (US)</span>
                </label>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Language</label>
              <select 
                value={settings.language} 
                onChange={(e) => settings.setLanguage(e.target.value)}
                className="w-full max-w-xs bg-white border border-slate-200 text-slate-900 py-2.5 px-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              >
                <option value="en">English (US)</option>
                <option value="en-gb">English (UK)</option>
                <option value="es">Español</option>
              </select>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
            <Settings2 className="w-5 h-5 text-blue-600" />
            Application Appearance
          </h2>
          
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-800">Interface Theme</h3>
              <p className="text-sm text-slate-500">Select your preferred visual style.</p>
            </div>
            <div className="flex bg-slate-100 p-1 rounded-xl">
              <button 
                className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 ${settings.theme === 'light' ? 'bg-white text-blue-700 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:text-slate-700'}`}
                onClick={() => settings.setTheme('light')}
              >
                <Sun className="w-4 h-4" /> Light
              </button>
              <button 
                className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 ${settings.theme === 'dark' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                onClick={() => settings.setTheme('dark')}
              >
                <Moon className="w-4 h-4" /> Dark
              </button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
