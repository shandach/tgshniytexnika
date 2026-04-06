import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, Monitor, LogOut } from 'lucide-react';

const Layout = () => {
    const navigate = useNavigate();

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const navLinkClass = ({ isActive }) =>
        `btn btn-outline ${isActive ? 'btn-primary' : ''} glass-panel`;

    return (
        <div className="app-container">
            <nav className="sidebar">
                <div style={{ marginBottom: '40px', padding: '10px' }}>
                    <h1 style={{ fontWeight: 700, fontSize: '1.4rem', color: 'var(--primary)' }}>TgTexnika</h1>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Admin Dashboard</p>
                </div>

                <NavLink to="/" className={navLinkClass} end style={{ justifyContent: 'flex-start' }}>
                    <LayoutDashboard size={18} /> API & Analytics
                </NavLink>
                <NavLink to="/requests" className={navLinkClass} style={{ justifyContent: 'flex-start' }}>
                    <FileText size={18} /> Список заявок
                </NavLink>
                <NavLink to="/inventory" className={navLinkClass} style={{ justifyContent: 'flex-start' }}>
                    <Monitor size={18} /> Статус техники
                </NavLink>

                <div style={{ flex: 1 }}></div>

                <button onClick={handleLogout} className="btn" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', justifyContent: 'flex-start' }}>
                    <LogOut size={18} /> Выйти
                </button>
            </nav>

            <main className="main-content">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
