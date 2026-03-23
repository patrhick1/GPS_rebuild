import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../context/AssessmentContext';
import './AssessmentResults.css';

export function AssessmentResults() {
  const { results } = useAssessment();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect if no results
    if (!results) {
      navigate('/dashboard');
    }
  }, [results, navigate]);

  if (!results) {
    return null;
  }

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="assessment-results">
      {/* Header */}
      <header className="results-header">
        <h1>Your GPS Assessment Results</h1>
        <div className="results-actions no-print">
          <button className="btn-secondary" onClick={handlePrint}>
            Print Results
          </button>
          <button className="btn-primary" onClick={() => navigate('/dashboard')}>
            Return to Dashboard
          </button>
        </div>
      </header>

      {/* Top Gifts Section */}
      <section className="results-section">
        <h2>Your Top Spiritual Gifts</h2>
        <p className="section-description">
          These are your highest-scoring spiritual gifts based on your assessment responses.
        </p>
        
        <div className="gifts-grid">
          {results.top_gifts.map((gift, index) => (
            <div key={gift.id} className="gift-card primary">
              <div className="gift-rank">#{index + 1}</div>
              <h3>{gift.name}</h3>
              <div className="gift-score">Score: {gift.points}/20</div>
              <p>{gift.description}</p>
            </div>
          ))}
        </div>

        {/* All Gifts Chart */}
        <div className="all-gifts">
          <h3>All Gift Scores</h3>
          <div className="gifts-chart">
            {results.gifts.map((gift) => (
              <div key={gift.id} className="chart-bar-wrapper">
                <div className="chart-label">{gift.short_code}</div>
                <div className="chart-bar-container">
                  <div 
                    className={`chart-bar ${gift.points >= 16 ? 'high' : gift.points >= 12 ? 'medium' : 'low'}`}
                    style={{ width: `${(gift.points / 20) * 100}%` }}
                  />
                </div>
                <div className="chart-value">{gift.points}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Influencing Styles Section */}
      <section className="results-section">
        <h2>Your Influencing Styles</h2>
        <p className="section-description">
          These describe how you naturally influence others and communicate.
        </p>
        
        <div className="passions-grid">
          {results.top_passions.map((passion, index) => (
            <div key={passion.id} className={`passion-card ${index === 0 ? 'primary' : 'secondary'}`}>
              <div className="passion-label">{index === 0 ? 'Primary' : 'Secondary'}</div>
              <h3>{passion.name}</h3>
              <div className="passion-score">Score: {passion.points}</div>
              <p>{passion.description}</p>
            </div>
          ))}
        </div>

        {/* All Passions Chart */}
        <div className="all-passions">
          <h3>All Style Scores</h3>
          <div className="passions-chart">
            {results.passions.map((passion) => {
              const maxScore = 90; // Approximate max for passions
              return (
                <div key={passion.id} className="chart-bar-wrapper">
                  <div className="chart-label">{passion.short_code}</div>
                  <div className="chart-bar-container">
                    <div 
                      className={`chart-bar ${passion.points >= 70 ? 'high' : passion.points >= 50 ? 'medium' : 'low'}`}
                      style={{ width: `${(passion.points / maxScore) * 100}%` }}
                    />
                  </div>
                  <div className="chart-value">{passion.points}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Selections Section */}
      <section className="results-section selections">
        <h2>Your Selections</h2>
        
        {results.abilities.length > 0 && (
          <div className="selection-group">
            <h3>Key Abilities</h3>
            <div className="selection-tags">
              {results.abilities.map((ability, idx) => (
                <span key={idx} className="tag">{ability}</span>
              ))}
            </div>
          </div>
        )}

        {results.people.length > 0 && (
          <div className="selection-group">
            <h3>People You're Passionate About</h3>
            <div className="selection-tags">
              {results.people.map((person, idx) => (
                <span key={idx} className="tag">{person}</span>
              ))}
            </div>
          </div>
        )}

        {results.causes.length > 0 && (
          <div className="selection-group">
            <h3>Causes You Care About</h3>
            <div className="selection-tags">
              {results.causes.map((cause, idx) => (
                <span key={idx} className="tag">{cause}</span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Story Responses Section */}
      {results.stories.length > 0 && (
        <section className="results-section stories">
          <h2>Your Story</h2>
          
          {results.stories.map((story, idx) => (
            <div key={idx} className="story-response">
              <h3>{story.question}</h3>
              <p className="story-answer">{story.answer}</p>
            </div>
          ))}
        </section>
      )}

      {/* Footer */}
      <footer className="results-footer no-print">
        <button className="btn-secondary" onClick={handlePrint}>
          Print Results
        </button>
        <button className="btn-primary" onClick={() => navigate('/dashboard')}>
          Return to Dashboard
        </button>
      </footer>
    </div>
  );
}
