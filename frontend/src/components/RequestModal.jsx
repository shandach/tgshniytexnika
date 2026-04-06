import { useState, useEffect } from 'react';
import { X, Send, Save } from 'lucide-react';
import api from '../api';
import { format } from 'date-fns';

const RequestModal = ({ reqId, onClose, onUpdate }) => {
    const [req, setReq] = useState(null);
    const [newComment, setNewComment] = useState('');
    const [rejectReason, setRejectReason] = useState('');

    useEffect(() => {
        loadReq();
    }, [reqId]);

    const loadReq = async () => {
        const res = await api.get(`/requests/${reqId}`);
        setReq(res.data);
    };

    const handleStatusChange = async (decision) => {
        if (decision === 'rejected' && !rejectReason.trim()) {
            alert("Укажите причину отказа!");
            return;
        }
        await api.patch(`/requests/${reqId}/status`, {
            status: 'closed',
            final_decision: decision,
            reject_reason: decision === 'rejected' ? rejectReason : null
        });
        onUpdate();
        onClose();
    };

    const handleSendComment = async () => {
        if (!newComment.trim()) return;
        await api.post(`/requests/${reqId}/comments`, { comment_text: newComment });
        setNewComment('');
        loadReq();
    };

    if (!req) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
            <div className="glass-panel" style={{ width: '90%', maxWidth: '800px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid var(--glass-border)' }}>
                    <h3 style={{ fontSize: '1.4rem' }}>Заявка #{req.request_number}</h3>
                    <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X /></button>
                </div>

                {/* Content */}
                <div style={{ display: 'flex', overflowY: 'auto' }}>

                    {/* Info Side */}
                    <div style={{ flex: 1, padding: '24px', borderRight: '1px solid var(--glass-border)' }}>
                        <h4 style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>Информация о заявке</h4>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                            <div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>ФИО</div>
                                <div>{req.employee_fio_snapshot}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Должность</div>
                                <div>{req.employee_position_snapshot || '-'}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Ветка/BXM</div>
                                <div>{req.branch_name_snapshot} ({req.bhm_code_snapshot})</div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Инвентарный код</div>
                                <div>{req.inventory_code_snapshot || 'Нет'}</div>
                            </div>
                        </div>

                        <div style={{ marginBottom: '24px', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Основание</div>
                            <div style={{ marginTop: '8px' }}>{req.reason_text || req.problem_text || 'Не указано'}</div>
                        </div>

                        {req.status !== 'closed' && (
                            <div style={{ marginTop: '24px', display: 'flex', gap: '10px' }}>
                                <button onClick={() => handleStatusChange('approved')} className="btn btn-primary" style={{ flex: 1 }}>Одобрить</button>
                                <div style={{ display: 'flex', flex: 1, gap: '5px' }}>
                                    <input
                                        type="text"
                                        placeholder="Причина отказа"
                                        value={rejectReason}
                                        onChange={e => setRejectReason(e.target.value)}
                                        style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)', color: 'white', padding: '8px', borderRadius: '8px', outline: 'none' }}
                                    />
                                    <button onClick={() => handleStatusChange('rejected')} className="btn" style={{ background: 'var(--danger)', color: 'white' }}>Отказать</button>
                                </div>
                            </div>
                        )}

                        {req.status === 'closed' && (
                            <div style={{ marginTop: '24px', padding: '16px', background: req.final_decision === 'approved' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                                Решение: <strong>{req.final_decision === 'approved' ? 'Одобрено' : 'Отклонено'}</strong>
                                {req.reject_reason && <p style={{ marginTop: '8px', fontSize: '0.9rem' }}>Причина: {req.reject_reason}</p>}
                            </div>
                        )}

                    </div>

                    {/* Comments Side */}
                    <div style={{ width: '350px', display: 'flex', flexDirection: 'column', background: 'rgba(255,255,255,0.02)' }}>
                        <div style={{ padding: '20px', borderBottom: '1px solid var(--glass-border)', fontWeight: 500 }}>
                            Комментарии
                        </div>

                        <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {req.comments.length === 0 ? (
                                <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '20px', fontSize: '0.9rem' }}>Нет комментариев</div>
                            ) : (
                                req.comments.map(c => (
                                    <div key={c.id} style={{ background: 'rgba(59, 130, 246, 0.15)', padding: '12px', borderRadius: '8px', borderBottomLeftRadius: 0 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{c.author_name}</span>
                                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{format(new Date(c.created_at), 'HH:mm dd.MM')}</span>
                                        </div>
                                        <div style={{ fontSize: '0.9rem' }}>{c.comment_text}</div>
                                    </div>
                                ))
                            )}
                        </div>

                        <div style={{ padding: '16px', borderTop: '1px solid var(--glass-border)', display: 'flex', gap: '8px' }}>
                            <input
                                type="text"
                                placeholder="Написать комментарий..."
                                value={newComment}
                                onChange={e => setNewComment(e.target.value)}
                                style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)', color: 'white', padding: '10px', borderRadius: '8px', outline: 'none' }}
                            />
                            <button onClick={handleSendComment} className="btn btn-primary" style={{ padding: '10px', minWidth: 'auto' }}><Send size={16} /></button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default RequestModal;
