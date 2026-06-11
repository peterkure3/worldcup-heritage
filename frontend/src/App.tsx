import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { GroupsPage } from './pages/Groups';
import { KnockoutPage } from './pages/Knockout';
import { PredictionsPage } from './pages/Predictions';
import './App.css';

function NavBar() {
  return (
    <nav className="navbar">
      <a href="/" className="nav-brand">
        <img src="/tournaments_fifa-world-cup-2026--white.football-logos.cc.svg" alt="World Cup" className="brand-icon" width="28" height="28" />
        <span className="brand-text">World Cup Heritage</span>
      </a>
      <div className="nav-links">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Groups
        </NavLink>
        <NavLink to="/knockout" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Knockout
        </NavLink>
        <NavLink to="/predictions" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Predictions
        </NavLink>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <NavBar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<GroupsPage />} />
            <Route path="/knockout" element={<KnockoutPage />} />
            <Route path="/predictions" element={<PredictionsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
