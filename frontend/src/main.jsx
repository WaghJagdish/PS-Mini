import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowDownRight, ArrowUpRight, BrainCircuit, CheckCircle2, CircleAlert, Code2, Container, Github, GitBranch, HeartPulse, RefreshCw, ShieldCheck, Terminal, Workflow } from 'lucide-react';
import './styles.css';

const fmt = (n) => typeof n === 'number' ? `${(n * 100).toFixed(2)}%` : '—';
const pretty = (name) => name.replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase());

function MetricCard({ label, value, note, icon: Icon, trend }) {
  return <article className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon size={17}/></span></div><div className="metric-value">{value}</div><div className="metric-note">{trend && (trend === 'up' ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>)}{note}</div></article>;
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [sample, setSample] = useState(null);
  const [features, setFeatures] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState(null);

  const refresh = async () => {
    setLoading(true); setError('');
    try {
      const [d, s] = await Promise.all([fetch('/dashboard').then(r => { if (!r.ok) throw new Error('Dashboard endpoint unavailable'); return r.json(); }), fetch('/sample-input').then(r => { if (!r.ok) throw new Error('Sample input unavailable'); return r.json(); })]);
      setDashboard(d); setSample(s); setFeatures(s.features); setLastRefresh(new Date());
    } catch (e) { setError(`${e.message}. Make sure the API container is running and a model has been trained.`); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, []);

  const runPrediction = async (e) => {
    e.preventDefault(); setPredicting(true); setError(''); setPrediction(null);
    try {
      const response = await fetch('/predict', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ features: features.map(Number) }) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'Prediction failed');
      setPrediction(body);
    } catch (e) { setError(e.message); }
    finally { setPredicting(false); }
  };

  const decision = dashboard?.decision;
  const metrics = dashboard?.metrics;
  const featureNames = sample?.feature_names || [];
  const metricPairs = useMemo(() => metrics ? [['Accuracy', metrics.accuracy], ['F1 score', metrics.f1], ['Precision', metrics.precision], ['Recall', metrics.recall]] : [], [metrics]);

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><BrainCircuit size={22}/></div><div><strong>ModelOps</strong><span>DEPLOYMENT CONSOLE</span></div></div>
      <div className="nav-label">WORKSPACE</div>
      <a className="nav-item active" href="#overview"><Activity size={17}/> Overview</a>
      <a className="nav-item" href="#prediction"><HeartPulse size={17}/> Prediction lab</a>
      <a className="nav-item" href="#pipeline"><Workflow size={17}/> CI/CD pipeline</a>
      <div className="sidebar-bottom"><div className="side-status"><span className="status-dot"/><div><strong>Local environment</strong><small>Jenkins · Docker · FastAPI</small></div></div><div className="side-note">Educational demo only. Not for clinical use.</div></div>
    </aside>

    <main className="main-content">
      <header className="topbar"><div><div className="eyebrow">MACHINE LEARNING / DEVOPS</div><h1>Model deployment overview</h1><p>Monitor model quality, review release decisions and test the prediction API.</p></div><button className="button secondary refresh-button" onClick={refresh} disabled={loading}><RefreshCw size={15} className={loading ? 'spin' : ''}/>{loading ? 'Refreshing' : 'Refresh data'}</button></header>

      {error && <div className="alert error-alert"><CircleAlert size={18}/><span>{error}</span></div>}

      <section id="overview" className="section-block">
        <div className="section-heading"><div><h2>Production snapshot</h2><p>Metrics from the currently packaged model artifact</p></div><span className="live-pill"><span className="status-dot"/> API dashboard</span></div>
        <div className="metric-grid">
          <MetricCard label="Accuracy" value={fmt(metrics?.accuracy)} note="Fixed holdout set" icon={Activity}/>
          <MetricCard label="F1 score" value={fmt(metrics?.f1)} note="Primary release metric" icon={ShieldCheck}/>
          <MetricCard label="Precision" value={fmt(metrics?.precision)} note="Positive class: malignant" icon={BrainCircuit}/>
          <MetricCard label="Recall" value={fmt(metrics?.recall)} note="Positive class: malignant" icon={HeartPulse}/>
        </div>
      </section>

      <section id="pipeline" className="section-block">
        <div className="section-heading"><div><h2>Release decision</h2><p>Last decision artifact packaged into this deployment</p></div><span className={`decision-pill ${decision?.decision === 'deploy' ? 'good' : decision?.decision === 'reject' ? 'neutral' : ''}`}>{decision?.decision ? decision.decision.toUpperCase() : 'NOT AVAILABLE'}</span></div>
        <div className="panel decision-panel">
          <div className="decision-main"><div className={`decision-symbol ${decision?.decision === 'deploy' ? 'good' : ''}`}>{decision?.decision === 'deploy' ? <CheckCircle2 size={23}/> : <GitBranch size={23}/>}</div><div><h3>{decision?.decision === 'deploy' ? 'Candidate approved for deployment' : decision?.decision === 'reject' ? 'Existing model retained' : 'Decision artifact not found'}</h3><p>{decision?.reason || 'Run the Jenkins pipeline to generate a model comparison decision.'}</p></div></div>
          <div className="comparison-grid"><div className="comparison-card"><span>Candidate F1</span><strong>{fmt(decision?.candidate?.f1)}</strong><small>Newly trained model</small></div><div className="comparison-card"><span>Incumbent F1</span><strong>{fmt(decision?.incumbent?.f1)}</strong><small>Previously approved model</small></div><div className="comparison-card"><span>Candidate accuracy</span><strong>{fmt(decision?.candidate?.accuracy)}</strong><small>Same holdout split</small></div><div className="comparison-card"><span>Incumbent accuracy</span><strong>{fmt(decision?.incumbent?.accuracy)}</strong><small>Tie-breaker metric</small></div></div>
          <div className="decision-foot"><span><ShieldCheck size={15}/> F1 score first, accuracy tie-breaker</span><span><RefreshCw size={14}/> {lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString()}` : 'Waiting for API'}</span></div>
        </div>
      </section>

      <section className="section-block pipeline-section">
        <div className="section-heading"><div><h2>Automated pipeline</h2><p>Expected lifecycle on every GitHub push</p></div></div>
        <div className="pipeline-track">
          <div className="pipeline-step"><div className="step-icon github"><Github size={19}/></div><strong>GitHub</strong><small>Push code</small></div><div className="pipeline-connector"/>
          <div className="pipeline-step"><div className="step-icon jenkins"><Workflow size={19}/></div><strong>Jenkins</strong><small>Test & retrain</small></div><div className="pipeline-connector"/>
          <div className="pipeline-step"><div className="step-icon evaluate"><ShieldCheck size={19}/></div><strong>Evaluate</strong><small>Compare F1 / accuracy</small></div><div className="pipeline-connector"/>
          <div className="pipeline-step"><div className="step-icon docker"><Container size={19}/></div><strong>Docker</strong><small>Deploy if better</small></div>
        </div>
        <div className="pipeline-caption"><Terminal size={15}/> This UI shows the last packaged decision; live Jenkins build history is available in the Jenkins console.</div>
      </section>

      <section id="prediction" className="section-block">
        <div className="section-heading"><div><h2>Prediction lab</h2><p>Send 30 numeric features to the running model API</p></div><span className="demo-label">DEMO MODE</span></div>
        <div className="panel prediction-panel">
          <div className="prediction-intro"><div className="prediction-icon"><Code2 size={21}/></div><div><h3>Test a sample prediction</h3><p>Load the dataset's first example, then run inference. You can edit any feature value.</p></div><button className="button secondary compact" onClick={() => { if (sample) { setFeatures(sample.features); setPrediction(null); } }} disabled={!sample}>Load sample</button></div>
          <form onSubmit={runPrediction}>
            <div className="feature-grid">{featureNames.map((name, i) => <label className="feature-field" key={name}><span title={name}>{pretty(name)}</span><input type="number" step="any" value={features[i] ?? ''} onChange={e => setFeatures(old => old.map((v, idx) => idx === i ? e.target.value : v))} required /></label>)}</div>
            <div className="form-footer"><span>Required: exactly 30 numeric features</span><button className="button primary" type="submit" disabled={predicting || features.length !== 30}>{predicting ? 'Running prediction…' : 'Run prediction'}</button></div>
          </form>
          {prediction && <div className={`prediction-result ${prediction.class_name === 'malignant' ? 'warning' : 'success'}`}><div className="result-icon">{prediction.class_name === 'malignant' ? <CircleAlert size={20}/> : <CheckCircle2 size={20}/>}</div><div><span>MODEL OUTPUT</span><h3>{prediction.class_name === 'malignant' ? 'Malignant class predicted' : 'Benign class predicted'}</h3><p>Predicted class ID: {prediction.prediction}. This is an educational dataset demonstration, not a medical assessment.</p></div></div>}
        </div>
      </section>
      <footer className="footer"><span>ModelOps · Professional Skills Development mini-project</span><span>Built with React, FastAPI, Jenkins & Docker</span></footer>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
