import { useState, useEffect } from 'react';
import { RefreshCw, Monitor, ChevronDown, ChevronRight, Wrench } from 'lucide-react';
import api from '../api';

const Inventory = () => {
    const [tree, setTree] = useState({});
    const [loading, setLoading] = useState(true);
    const [expandedRegions, setExpandedRegions] = useState({});
    const [expandedCities, setExpandedCities] = useState({});
    const [expandedBranches, setExpandedBranches] = useState({});

    const fetchInventory = async () => {
        setLoading(true);
        try {
            const res = await api.get('/inventory/tree');
            setTree(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInventory();
    }, []);

    const handleStatusChange = async (invId, newStatus) => {
        try {
            await api.patch(`/inventory/${invId}/status`, { status: newStatus });
            fetchInventory();
        } catch (err) {
            alert("Ошибка при обновлении статуса");
        }
    };

    const toggleRegion = (reg) => setExpandedRegions(prev => ({ ...prev, [reg]: !prev[reg] }));
    const toggleCity = (reg, city) => setExpandedCities(prev => ({ ...prev, [`${reg}_${city}`]: !prev[`${reg}_${city}`] }));
    const toggleBranch = (city, bhm) => setExpandedBranches(prev => ({ ...prev, [`${city}_${bhm}`]: !prev[`${city}_${bhm}`] }));

    const StatusIcon = ({ status }) => {
        if (status === 'active') return <span className="badge active" style={{ marginLeft: '10px' }}>Активен</span>;
        if (status === 'repair') return <span className="badge repair" style={{ marginLeft: '10px' }}><Wrench size={12} style={{ marginRight: '4px' }} />В ремонте</span>;
        return <span className="badge closed" style={{ marginLeft: '10px' }}>{status}</span>;
    };

    return (
        <div className="animate-fade">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h2 style={{ fontSize: '2rem' }}>База инвентаря</h2>
                <button className="btn btn-outline" onClick={fetchInventory}><RefreshCw size={18} /> Обновить</button>
            </div>

            <div className="glass-panel" style={{ padding: '24px', minHeight: '400px' }}>
                {loading ? (
                    <div>Загрузка дерева инвентаря...</div>
                ) : Object.keys(tree).length === 0 ? (
                    <div>Нет данных</div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {Object.entries(tree).map(([region, cities]) => (
                            <div key={region} className="glass-panel" style={{ border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', overflow: 'hidden' }}>
                                <div
                                    onClick={() => toggleRegion(region)}
                                    style={{ padding: '16px 20px', background: 'rgba(255,255,255,0.03)', cursor: 'pointer', display: 'flex', alignItems: 'center', fontWeight: '600' }}
                                >
                                    {expandedRegions[region] ? <ChevronDown size={18} style={{ marginRight: '8px' }} /> : <ChevronRight size={18} style={{ marginRight: '8px' }} />}
                                    Регион: {region}
                                </div>

                                {expandedRegions[region] && (
                                    <div style={{ padding: '0 0 10px 20px', background: 'rgba(0,0,0,0.2)' }}>
                                        {Object.entries(cities).map(([city, branches]) => (
                                            <div key={city} style={{ marginTop: '10px' }}>
                                                <div
                                                    onClick={() => toggleCity(region, city)}
                                                    style={{ padding: '10px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', color: 'var(--text-main)', fontWeight: 500 }}
                                                >
                                                    {expandedCities[`${region}_${city}`] ? <ChevronDown size={16} style={{ marginRight: '8px' }} /> : <ChevronRight size={16} style={{ marginRight: '8px' }} />}
                                                    Город / Улица: {city}
                                                </div>

                                                {expandedCities[`${region}_${city}`] && (
                                                    <div style={{ paddingLeft: '20px' }}>
                                                        {Object.entries(branches).map(([branchName, items]) => (
                                                            <div key={branchName} style={{ marginTop: '10px' }}>
                                                                <div
                                                                    onClick={() => toggleBranch(city, branchName)}
                                                                    style={{ padding: '8px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}
                                                                >
                                                                    {expandedBranches[`${city}_${branchName}`] ? <ChevronDown size={14} style={{ marginRight: '8px' }} /> : <ChevronRight size={14} style={{ marginRight: '8px' }} />}
                                                                    Филиал (BXM): {branchName}
                                                                </div>

                                                                {expandedBranches[`${city}_${branchName}`] && (
                                                                    <div style={{ paddingLeft: '34px', paddingRight: '20px', display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '10px' }}>
                                                                        {items.map(item => (
                                                                            <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                                                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                                                                    <Monitor size={16} style={{ marginRight: '10px', color: 'var(--primary)' }} />
                                                                                    <span>{item.type.toUpperCase()} — <strong>{item.code}</strong></span>
                                                                                    <StatusIcon status={item.status} />
                                                                                </div>
                                                                                <select
                                                                                    value={item.status}
                                                                                    onChange={(e) => handleStatusChange(item.id, e.target.value)}
                                                                                    className="glass-panel"
                                                                                    style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid var(--glass-border)', color: 'white', padding: '4px 8px', borderRadius: '4px', outline: 'none' }}
                                                                                >
                                                                                    <option value="active">Active</option>
                                                                                    <option value="repair">Repair</option>
                                                                                    <option value="write_off">Списано</option>
                                                                                </select>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Inventory;
