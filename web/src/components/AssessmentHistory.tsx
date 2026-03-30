import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDashboard } from '../context/DashboardContext';
import './AssessmentHistory.css';

export function AssessmentHistory() {
  const { history, fetchHistory, isLoading, error, compareAssessments, getAssessmentDetail } = useDashboard();
  const navigate = useNavigate();
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  const [detailView, setDetailView] = useState<any>(null);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleCompare = async () => {
    if (selectedForCompare.length !== 2) return;
    
    try {
      const result = await compareAssessments(selectedForCompare[0], selectedForCompare[1]);
      setComparisonResult(result);
      setDetailView(null);
    } catch (err) {
      console.error('Comparison failed:', err);
    }
  };

  const toggleSelection = (id: string) => {
    setSelectedForCompare(prev => {
      if (prev.includes(id)) {
        return prev.filter(i => i !== id);
      }
      if (prev.length >= 2) {
        return [prev[1], id];
      }
      return [...prev, id];
    });
    setComparisonResult(null);
  };

  const viewDetail = async (id: string) => {
    try {
      const detail = await getAssessmentDetail(id);
      setDetailView(detail);
      setComparisonResult(null);
    } catch (err) {
      console.error('Failed to load detail:', err);
    }
  };

  if (isLoading) {
    return <div className="loading">Loading assessment history...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (history.length === 0) {
    return (
      <div className="empty-history">
        <p>You haven't completed any assessments yet.</p>
        <button className="btn-primary" onClick={() => navigate('/assessment')}>
          Take Your First Assessment
        </button>
      </div>
    );
  }

  return (
    <div className="assessment-history">
      {/* Comparison Controls */}
      {selectedForCompare.length > 0 && (
        <div className="compare-controls">
          <span>
            Selected: {selectedForCompare.length}/2
          </span>
          <button
            className="btn-primary"
            onClick={handleCompare}
            disabled={selectedForCompare.length !== 2}
          >
            Compare Selected
          </button>
          <button
            className="btn-secondary"
            onClick={() => {
              setSelectedForCompare([]);
              setComparisonResult(null);
            }}
          >
            Clear
          </button>
        </div>
      )}

      {/* Comparison View */}
      {comparisonResult && (() => {
        const date1 = comparisonResult.assessment_1.completed_at
          ? new Date(comparisonResult.assessment_1.completed_at).toLocaleDateString()
          : 'In Progress';
        const date2 = comparisonResult.assessment_2.completed_at
          ? new Date(comparisonResult.assessment_2.completed_at).toLocaleDateString()
          : 'In Progress';

        const renderDeltaTable = (
          label: string,
          items1: { name: string; score: number }[],
          items2: { name: string; score: number }[]
        ) => {
          const map2 = new Map(items2.map(i => [i.name, i.score]));
          return (
            <div className="mb-6">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">{label}</h4>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 border-b border-gray-200">
                    <th className="pb-1 font-medium w-1/2">Gift</th>
                    <th className="pb-1 font-medium text-center">{date1}</th>
                    <th className="pb-1 font-medium text-center">Change</th>
                    <th className="pb-1 font-medium text-center">{date2}</th>
                  </tr>
                </thead>
                <tbody>
                  {items1.map((item) => {
                    const score2 = map2.get(item.name) ?? item.score;
                    const delta = score2 - item.score;
                    const improved = delta > 0;
                    const declined = delta < 0;
                    const rowBg = improved
                      ? 'bg-green-50'
                      : declined
                      ? 'bg-red-50'
                      : '';
                    const deltaLabel = improved
                      ? `▲ +${delta}`
                      : declined
                      ? `▼ ${delta}`
                      : '—';
                    const deltaColor = improved
                      ? 'text-green-600 font-semibold'
                      : declined
                      ? 'text-red-500 font-semibold'
                      : 'text-gray-400';
                    return (
                      <tr key={item.name} className={`border-b border-gray-100 ${rowBg}`}>
                        <td className="py-1.5 pr-2 font-medium text-gray-700">{item.name}</td>
                        <td className="py-1.5 text-center text-gray-500">{item.score}</td>
                        <td className={`py-1.5 text-center text-xs ${deltaColor}`}>{deltaLabel}</td>
                        <td className="py-1.5 text-center text-gray-700 font-medium">{score2}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        };

        return (
          <div className="my-4 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-gray-800">Assessment Comparison</h3>
              <div className="flex gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-green-400"></span> Improved</span>
                <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-red-400"></span> Declined</span>
                <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-gray-300"></span> Unchanged</span>
              </div>
            </div>
            {renderDeltaTable('Spiritual Gifts', comparisonResult.assessment_1.gifts, comparisonResult.assessment_2.gifts)}
            {renderDeltaTable('Influencing Styles', comparisonResult.assessment_1.passions, comparisonResult.assessment_2.passions)}
          </div>
        );
      })()}

      {/* Detail View */}
      {detailView && (
        <div className="detail-view">
          <div className="detail-header">
            <h3>Assessment Details</h3>
            <button className="btn-close" onClick={() => setDetailView(null)}>×</button>
          </div>
          
          <div className="detail-section">
            <h4>Spiritual Gifts</h4>
            <div className="detail-gifts">
              {detailView.gifts.map((gift: any) => (
                <div key={gift.id} className="detail-gift-item">
                  <strong>{gift.name}</strong>
                  <span>Score: {gift.score}/20</span>
                </div>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <h4>Influencing Styles</h4>
            <div className="detail-passions">
              {detailView.passions.map((passion: any) => (
                <div key={passion.id} className="detail-passion-item">
                  <strong>{passion.name}</strong>
                  <span>Score: {passion.score}</span>
                </div>
              ))}
            </div>
          </div>

          {detailView.selections && (
            <div className="detail-section">
              <h4>Your Selections</h4>
              {detailView.selections.abilities.length > 0 && (
                <div className="detail-selections">
                  <strong>Abilities:</strong>
                  <div className="tags">
                    {detailView.selections.abilities.map((a: string, i: number) => (
                      <span key={i} className="tag">{a}</span>
                    ))}
                  </div>
                </div>
              )}
              {detailView.selections.people.length > 0 && (
                <div className="detail-selections">
                  <strong>People:</strong>
                  <div className="tags">
                    {detailView.selections.people.map((p: string, i: number) => (
                      <span key={i} className="tag">{p}</span>
                    ))}
                  </div>
                </div>
              )}
              {detailView.selections.causes.length > 0 && (
                <div className="detail-selections">
                  <strong>Causes:</strong>
                  <div className="tags">
                    {detailView.selections.causes.map((c: string, i: number) => (
                      <span key={i} className="tag">{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* History Table */}
      <div className="history-table">
        <table>
          <thead>
            <tr>
              <th>Compare</th>
              <th>Date</th>
              <th>Top Gifts</th>
              <th>Influencing Styles</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {history.map((assessment) => (
              <tr key={assessment.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedForCompare.includes(assessment.id)}
                    onChange={() => toggleSelection(assessment.id)}
                  />
                </td>
                <td>
                  {assessment.completed_at
                    ? new Date(assessment.completed_at).toLocaleDateString()
                    : 'In Progress'}
                </td>
                <td>
                  <div className="table-gifts">
                    {assessment.top_gifts.map((g, i) => (
                      <span key={i} className="mini-tag gift">
                        {g.name} ({g.score})
                      </span>
                    ))}
                  </div>
                </td>
                <td>
                  <div className="table-passions">
                    {assessment.top_passions.map((p, i) => (
                      <span key={i} className="mini-tag passion">
                        {p.name} ({p.score})
                      </span>
                    ))}
                  </div>
                </td>
                <td>
                  <button
                    className="btn-view"
                    onClick={() => viewDetail(assessment.id)}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
