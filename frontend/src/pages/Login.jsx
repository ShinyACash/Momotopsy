import React from 'react';
import { useNavigate } from 'react-router-dom';
import momoBasket from '../assets/momo_basket.png';

export default function Login({ isSignup }) {
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate('/upload');
  };

  const inputStyle = {
    width: '100%',
    padding: '10px 0',
    border: 'none',
    borderBottom: '1px solid var(--border-light)',
    background: 'transparent',
    marginBottom: '25px',
    fontSize: '0.9rem',
    color: 'var(--text-primary)',
    outline: 'none',
    fontFamily: 'Georgia, serif',
    letterSpacing: '1px'
  };

  const btnStyle = {
    padding: '12px 40px',
    borderRadius: '30px',
    border: '1px solid var(--border-light)',
    background: 'transparent',
    color: 'var(--text-primary)',
    fontWeight: 'bold',
    cursor: 'pointer',
    fontSize: '0.9rem',
    display: 'block',
    margin: '10px auto'
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', backgroundColor: 'var(--login-bg-color)' }}>
      <div className="deco-circle deco-1"></div>
      <div className="deco-circle deco-2"></div>
      <img src={momoBasket} alt="Momo Basket" className="float-sleek" style={{ position: 'absolute', bottom: '10vh', left: '20vw', width: 'clamp(150px, 30vh, 300px)', transform: 'rotate(345deg)', zIndex: 3 }} />

      <h1 style={{ fontSize: 'clamp(2.5rem, 6vw, 3.5rem)', fontWeight: 'normal', color: '#726741', letterSpacing: '4px', marginBottom: '40px', zIndex: 2, textAlign: 'center' }}>
        {isSignup ? "SIGN UP" : "WELCOME BACK"}
      </h1>

      <div className="glass-panel fade-in" style={{ padding: 'clamp(30px, 5vw, 200px)', width: '1400%', maxWidth: '650px', borderRadius: '16px', zIndex: 2 }}>
        <form onSubmit={handleSubmit}>
          <input type="text" className="smooth-input" placeholder="USERNAME/EMAILID" style={inputStyle} required />
          {isSignup && <input type="email" className="smooth-input" placeholder="EMAIL ID" style={inputStyle} required />}
          <input type="password" className="smooth-input" placeholder="PASSWORD" style={inputStyle} required />
          {isSignup && <input type="password" className="smooth-input" placeholder="CONFIRM PASSWORD" style={inputStyle} required />}

          {!isSignup && (
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '30px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <input type="checkbox" /> Remember Me
            </label>
          )}

          <button type="submit" className="action-btn" style={btnStyle}>{isSignup ? 'SIGN UP' : 'LOG IN'}</button>

          <div style={{ display: 'flex', alignItems: 'center', margin: '30px 0', color: 'var(--border-light)' }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--border-light)' }}></div>
            <span style={{ padding: '0 10px', fontSize: '0.8rem' }}>OR</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--border-light)' }}></div>
          </div>

          <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
            <button type="button" className="action-btn" style={{ ...btnStyle, flex: 1, margin: 0, padding: '12px 10px', fontSize: '0.8rem' }}>{isSignup ? "SIGN UP WITH GOOGLE" : "SIGN IN WITH GOOGLE"}</button>
            {!isSignup && <button type="button" className="action-btn" onClick={() => navigate('/signup')} style={{ ...btnStyle, flex: 1, margin: 0, padding: '12px 10px', fontSize: '0.8rem' }}>SIGN UP</button>}
          </div>

          <button
            type="button"
            className="action-btn"
            onClick={() => navigate('/upload')}
            style={{ position: 'absolute', top: '20px', right: '20px', padding: '8px 15px', borderRadius: '20px', background: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--text-secondary)', cursor: 'pointer', fontSize: '0.8rem' }}
          >
            Hackathon Bypass
          </button>
        </form>
      </div>
    </div>
  );
}
