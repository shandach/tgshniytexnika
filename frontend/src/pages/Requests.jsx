import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { Eye, Search, Filter } from 'lucide-react';
import api from '../api';
import RequestModal from '../components/RequestModal';

const Requests = () => {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedReqId, setSelectedReqId] = useState(null);

    // Filters
    const [statusFilter, setStatusFilter] = useState('');

    const fetchRequests = async () => {
        setLoading(true);
        try {
            const qs = statusFilter ? `?status=${statusFilter}` : '';
            const res = await api.get(`/requests${qs}`);
            setRequests(res.data.items);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [statusFilter]);

    const StatusBadge = ({ status }) => {
        return <span className={`badge ${status}`}>{status.toUpperCase()}</span>;
    };

    return (
        <div className="animate-fade">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h2 style={{ fontSize: '2rem' }}>Управление заявками</h2>

                <div style={{ display: 'flex', gap: '16px' }}>
                    <select
                        className="glass-panel"
                        style={{ padding: '10px 16px', color: 'white', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)', outline: 'none' }}
                        value={statusFilter}
                        onChange={e => setStatusFilter(e.target.value)}
                    >
                        <option value="">Все статусы</option>
                        <option value="new">Новые</option>
                        <option value="in_progress">В процессе</option>
                        <option value="closed">Закрытые</option>
                    </select>
                </div>
            </div>

            <div className="glass-panel" style={{ overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead style={{ background: 'rgba(255,255,255,0.05)' }}>
                        <tr>
                            <th style={{ padding: '16px', color: 'var(--text-muted)' }}>Номер</th>
                            <th style={{ padding: '16px', color: 'var(--text-muted)' }}>Филиал / BXM</th>
                            <th style={{ padding: '16px', color: 'var(--text-muted)' }}>Сотрудник</th>
                            <th style={{ padding: '16px', color: 'var(--text-muted)' }}>Тип заявки</th>
                            <th style={{ padding: '16px', color: 'var(--text-muted)' }}>Инвентарь</th>
                            <th style={{ padding: '16px', color: 'var(--text-muted)' }}>Статус</th>
                            <th style={{ padding: '16px', color: 'var(--text-muted)' }}>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center' }}>Загрузка...</td></tr>
                        ) : requests.length === 0 ? (
                            <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center' }}>Заявки не найдены</td></tr>
                        ) : (
                            requests.map(req => (
                                <tr key={req.id} style={{ borderBottom: '1px solid var(--glass-border)', transition: 'background 0.2s' }}>
                                    <td style={{ padding: '16px', fontWeight: 500 }}>{req.request_number}</td>
                                    <td style={{ padding: '16px' }}>
                                        {req.branch_name_snapshot}<br />
                                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>BXM: {req.bhm_code_snapshot}</span>
                                    </td>
                                    <td style={{ padding: '16px' }}>
                                        {req.employee_fio_snapshot}<br />
                                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{req.employee_position_snapshot || 'Нет должности'}</span>
                                    </td>
                                    <td style={{ padding: '16px' }}>
                                        {req.request_type === 'replacement' ? 'Замена' :
                                            req.request_type === 'new_issue' ? 'Выдача' : 'Поломка'}
                                    </td>
                                    <td style={{ padding: '16px' }}>{req.inventory_code_snapshot || '—'}</td>
                                    <td style={{ padding: '16px' }}>
                                        <StatusBadge status={req.status} />
                                    </td>
                                    <td style={{ padding: '16px' }}>
                                        <button
                                            onClick={() => setSelectedReqId(req.id)}
                                            className="btn btn-outline"
                                            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                                        >
                                            <Eye size={14} /> Открыть
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {selectedReqId && (
                <RequestModal
                    reqId={selectedReqId}
                    onClose={() => setSelectedReqId(null)}
                    onUpdate={fetchRequests}
                />
            )}
        </div>
    );
};

export default Requests;
