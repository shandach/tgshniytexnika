import { useEffect, useState } from 'react';
import { Activity, CheckCircle, Clock, XCircle } from 'lucide-react';
import api from '../api';

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchKPI = async () => {
            try {
                const res = await api.get('/dashboard/kpi');
                setStats(res.data);
            } catch (err) {
                console.error("Failed to fetch KPIs", err);
            } finally {
                setLoading(false);
            }
        };
        fetchKPI();
    }, []);

    if (loading) return <div>Загрузка...</div>;

    return (
        <div className="animate-fade">
            <h2 style={{ fontSize: '2rem', marginBottom: '24px' }}>Обзорная статистика</h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px' }}>

                <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '16px', borderRadius: '12px', color: '#60a5fa' }}>
                        <Activity size={32} />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '4px' }}>Всего заявок</p>
                        <h3 style={{ fontSize: '2rem', fontWeight: 700 }}>{stats?.total_requests || 0}</h3>
                    </div>
                </div>

                <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '16px', borderRadius: '12px', color: '#fbbf24' }}>
                        <Clock size={32} />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '4px' }}>Активные заявки</p>
                        <h3 style={{ fontSize: '2rem', fontWeight: 700 }}>{stats?.active_requests || 0}</h3>
                    </div>
                </div>

                <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '16px', borderRadius: '12px', color: '#34d399' }}>
                        <CheckCircle size={32} />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '4px' }}>Одобрено</p>
                        <h3 style={{ fontSize: '2rem', fontWeight: 700 }}>{stats?.approved_requests || 0}</h3>
                    </div>
                </div>

                <div className="glass-panel" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '16px', borderRadius: '12px', color: '#f87171' }}>
                        <XCircle size={32} />
                    </div>
                    <div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '4px' }}>Отклонено</p>
                        <h3 style={{ fontSize: '2rem', fontWeight: 700 }}>{stats?.rejected_requests || 0}</h3>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default Dashboard;
