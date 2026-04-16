import React from 'react';
import { useNavigate } from 'react-router-dom';
import largeMomo from '../assets/large_momo.png';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="living-bg" style={{ minHeight: '100vh', position: 'relative', display: 'flex', flexDirection: 'column' }}>

      {/* Decorative Overlays 
      <div className="deco-circle deco-1"></div>
      <div className="deco-line"></div>*/}

      {/* Abstract Shapes 
      <div className="deco-shape deco-square" style={{ bottom: '25vh', right: '35vw', transform: 'rotate(15deg) scale(0.6)' }}></div>
      <div className="deco-shape deco-cross" style={{ top: '38vh', left: '42vw' }}></div>
      <div className="deco-shape deco-cross" style={{ bottom: '45vh', right: '10vw', transform: 'scale(1.5)' }}></div>
      <div className="deco-shape deco-dot" style={{ top: '25vh', right: '22vw' }}></div>
      <div className="deco-shape deco-dot" style={{ bottom: '30vh', left: '20vw' }}></div>*/}
      
      <div style={{ position: 'absolute', top: '40px', right: '40px', zIndex: 10 }}>
        <button
          onClick={() => navigate('/login')}
          className="action-btn"
          style={{ padding: '10px 40px', borderRadius: '30px', border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-primary)', fontWeight: 'bold', cursor: 'pointer', fontSize: '1rem' }}
        >
          LOGIN
        </button>
      </div>

      <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center', flex: '1 1 0%', padding: '0 clamp(20px, 10vw, 150px)', zIndex: 2 }}>
        <h1 style={{ position: 'relative', fontSize: 'clamp(3.5rem, 10vw, 9rem)', fontWeight: 'normal', margin: '0px 0px 10px', letterSpacing: '2px', fontFamily: '"Migra", "Cinzel", serif', textShadow: '0 4px 20px rgba(56, 53, 38, 0.1)', lineHeight: 1 }}>
          <div className="deco-shape deco-square" style={{ width: '0.9em', height: '0.9em', top: '-10%', left: '-3%', zIndex: -1 }}></div>
          MOMOTOPSY
        </h1>
        <div style={{ maxWidth: '600px' }}>
          <p style={{ fontSize: 'clamp(1.2rem, 3vw, 2rem)', margin: '0px 0px 15px', color: 'var(--text-secondary)' }}>
            Mapping the Rotten Filling in the Fine Print
          </p>
          <p style={{ fontSize: 'clamp(1rem, 2vw, 1.2rem)', color: 'var(--text-secondary)', lineHeight: '1.6', opacity: 0.85 }}>
            Automated legal contract analysis. Discover hidden predatory clauses, understand interconnected risk networks, and obtain plain-language explanations before you sign.
          </p>
        </div>
      </div>

      {/* Hero Momo pushed to the right */}
      <img
        alt="Momo Illustration"
        src={largeMomo}
        style={{ position: 'absolute', top: '6vh', right: '5vw', width: 'clamp(250px, 40vw, 600px)', transform: 'rotate(16deg)', zIndex: 1, opacity: 0.9 }}
      />

      <div className="glass-panel" style={{ padding: 'clamp(30px, 5vw, 50px) clamp(20px, 10vw, 150px)', borderTop: '1px solid var(--border-light)', zIndex: 2 }}>
        <p style={{ lineHeight: '1.6', fontSize: 'clamp(1rem, 2vw, 1.3rem)', margin: '0', maxWidth: '45em', color: 'var(--text-secondary)' }}>
          Today, legal agreements are complex, expensive to review, and easy to misuse. Most people accept terms without fully understanding the risks involved. We saw this gap and set out to solve it using technology. Our platform breaks contracts into individual clauses and analyzes each one. It maps how clauses connect, revealing hidden patterns and risk networks. We flag dangerous terms, explain them in simple language, and suggest safer alternatives. This goes beyond summaries—it shows how a contract actually works. Our goal is to make legal understanding accessible to everyone.<br /><br />
          Because signing should feel like a choice, not a trap.
        </p>
      </div>
    </div>
  );
}
