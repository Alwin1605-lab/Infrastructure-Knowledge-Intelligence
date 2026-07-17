import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { motion } from 'framer-motion';

function DashboardPage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Ambient glow effects */}
      <div
        style={{
          position: 'absolute',
          top: '-20%',
          left: '-10%',
          width: '500px',
          height: '500px',
          background: 'radial-gradient(circle, rgba(79,70,229,0.15) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: '-20%',
          right: '-10%',
          width: '500px',
          height: '500px',
          background: 'radial-gradient(circle, rgba(6,182,212,0.12) 0%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      {/* Main content */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        style={{
          textAlign: 'center',
          zIndex: 1,
        }}
      >
        {/* Building icon */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          style={{ marginBottom: '2rem' }}
        >
          <svg
            width="80"
            height="80"
            viewBox="0 0 64 64"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#4f46e5" />
                <stop offset="100%" stopColor="#06b6d4" />
              </linearGradient>
            </defs>
            {/* Building outline */}
            <rect x="10" y="14" width="44" height="44" rx="1" stroke="url(#iconGrad)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
            {/* Roof / top accent */}
            <polyline points="6,16 32,4 58,16" stroke="url(#iconGrad)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            {/* Windows — row 1 */}
            <rect x="17" y="22" width="8" height="7" rx="0.5" stroke="url(#iconGrad)" strokeWidth="1.8" fill="none" />
            <rect x="39" y="22" width="8" height="7" rx="0.5" stroke="url(#iconGrad)" strokeWidth="1.8" fill="none" />
            {/* Windows — row 2 */}
            <rect x="17" y="35" width="8" height="7" rx="0.5" stroke="url(#iconGrad)" strokeWidth="1.8" fill="none" />
            <rect x="39" y="35" width="8" height="7" rx="0.5" stroke="url(#iconGrad)" strokeWidth="1.8" fill="none" />
            {/* Door */}
            <rect x="27" y="44" width="10" height="14" rx="0.5" stroke="url(#iconGrad)" strokeWidth="1.8" fill="none" />
          </svg>
        </motion.div>

        {/* Title with gradient */}
        <h1
          style={{
            fontSize: 'clamp(2rem, 5vw, 3.5rem)',
            fontWeight: 800,
            background: 'linear-gradient(135deg, #818cf8 0%, #4f46e5 30%, #06b6d4 70%, #818cf8 100%)',
            backgroundSize: '200% 200%',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            margin: '0 0 1rem 0',
            lineHeight: 1.2,
            letterSpacing: '-0.02em',
            animation: 'gradientShift 6s ease infinite',
          }}
        >
          Building Knowledge
          <br />
          Intelligence
        </h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.6 }}
          style={{
            fontSize: '1.15rem',
            color: '#9b99a9',
            margin: '0 0 1rem 0',
            maxWidth: '560px',
            lineHeight: 1.6,
          }}
        >
          AI-powered decision support for building maintenance and structural assessment
        </motion.p>

        {/* Domain badge */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.65, duration: 0.5 }}
          style={{
            fontSize: '0.85rem',
            color: '#6b6a7a',
            margin: '0 0 2.5rem 0',
            maxWidth: '560px',
            lineHeight: 1.5,
          }}
        >
          Knowledge Graphs · RAG · LLMs · Agentic AI · CPWD Manuals · NBC · BIS Standards
        </motion.p>

        {/* Status badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.7, duration: 0.5 }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.6rem 1.4rem',
            borderRadius: '9999px',
            background: 'rgba(79, 70, 229, 0.1)',
            border: '1px solid rgba(79, 70, 229, 0.25)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#10b981',
              boxShadow: '0 0 8px rgba(16, 185, 129, 0.6)',
              animation: 'pulse 2s ease-in-out infinite',
            }}
          />
          <span
            style={{
              fontSize: '0.875rem',
              fontWeight: 500,
              color: '#e2e0ea',
              letterSpacing: '0.04em',
            }}
          >
            Phase 2 — Building Knowledge System Online
          </span>
        </motion.div>
      </motion.div>

      {/* CSS animations */}
      <style>{`
        @keyframes gradientShift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.85); }
        }
      `}</style>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
