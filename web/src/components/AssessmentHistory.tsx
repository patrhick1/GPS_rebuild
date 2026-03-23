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
      {comparisonResult && (
        <div className="comparison-view">
          <h3>Assessment Comparison</h3>
          <div className="comparison-grid">
            <div className="comparison-column">
              <h4>
                {new Date(comparisonResult.assessment_1.completed_at).toLocaleDateString()}
              </h4>
              <div className="comparison-gifts">
                <h5>Spiritual Gifts</h5>
                {comparisonResult.assessment_1.gifts.map((gift: any) => (
                  <div key={gift.id} className="comparison-item">
                    <span>{gift.name}</span>
                    <span className="score">{gift.score}</span>
                  </div>
                ))}
              </div>
              <div className="comparison-passions">
                <h5>Influencing Styles</h5>
                {comparisonResult.assessment_1.passions.map((passion: any) => (
                  <div key={passion.id} className="comparison-item">
                    <span>{passion.name}</span>
                    <span className="score">{passion.score}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="comparison-column">
              <h4>
                {new Date(comparisonResult.assessment_2.completed_at).toLocaleDateString()}
              </h4>
              <div className="comparison-gifts">
                <h5>Spiritual Gifts</h5>
                {comparisonResult.assessment_2.gifts.map((gift: any) => (
                  <div key={gift.id} className="comparison-item">
                    <span>{gift.name}</span>
                    <span className="score">{gift.score}</span>
                  </div>
                ))}
              </div>
              <div className="comparison-passions">
                <h5>Influencing Styles</h5>
                {comparisonResult.assessment_2.passions.map((passion: any) => (
                  <div key={passion.id} className="comparison-item">
                    <span>{passion.name}</span>
                    <span className="score">{passion.score}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

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
