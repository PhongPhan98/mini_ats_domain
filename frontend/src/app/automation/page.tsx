"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";

type Rule = {
  id: string;
  enabled: boolean;
  on_stage: string;
  actions: { type: string; message?: string; url?: string; subject?: string; body?: string }[];
};

export default function AutomationPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const [rulesData, eventsData] = await Promise.all([
      apiGet<{ rules: Rule[] }>("/api/automation/rules"),
      apiGet<{ events: any[] }>("/api/automation/events?limit=80"),
    ]);
    setRules(rulesData.rules || []);
    setEvents(eventsData.events || []);
  };

  useEffect(() => {
    load();
  }, []);

  const addRule = () => {
    setRules((prev) => [
      ...prev,
      {
        id: `rule-${Date.now()}`,
        enabled: true,
        on_stage: "interview",
        actions: [{ type: "log", message: "Stage changed" }],
      },
    ]);
  };

  const saveRules = async () => {
    setSaving(true);
    try {
      await apiPost("/api/automation/rules", { rules });
      await load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid page-enter">
      <div className="card">
        <h2>Automation Rules</h2>
        <small>Trigger actions when candidate moves to a stage.</small>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3>Rules ({rules.length})</h3>
          <div className="toolbar-actions">
            <button className="btn-outline" onClick={addRule}>Add Rule</button>
            <button onClick={saveRules} disabled={saving}>{saving ? "Saving..." : "Save Rules"}</button>
          </div>
        </div>

        <div className="grid">
          {rules.map((r, idx) => (
            <div key={r.id} className="card" style={{ marginBottom: 8 }}>
              <div className="grid grid-3">
                <div>
                  <label>Rule ID</label>
                  <input value={r.id} onChange={(e) => setRules((prev) => prev.map((x, i) => i === idx ? { ...x, id: e.target.value } : x))} />
                </div>
                <div>
                  <label>On Stage</label>
                  <select value={r.on_stage} onChange={(e) => setRules((prev) => prev.map((x, i) => i === idx ? { ...x, on_stage: e.target.value } : x))}>
                    {["applied", "screening", "interview", "offer", "hired", "rejected"].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label>Enabled</label>
                  <select value={r.enabled ? "1" : "0"} onChange={(e) => setRules((prev) => prev.map((x, i) => i === idx ? { ...x, enabled: e.target.value === "1" } : x))}>
                    <option value="1">Enabled</option>
                    <option value="0">Disabled</option>
                  </select>
                </div>
              </div>
              <div style={{ marginTop: 8 }}>
                <small>Action type: log / email / webhook (edit in JSON rules file for advanced multi-actions)</small>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>Automation Event Log</h3>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Candidate</th>
              <th>Stage</th>
              <th>Rule</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={`${e.timestamp}-${i}`}>
                <td>{e.timestamp}</td>
                <td>{e.candidate_name}</td>
                <td>{e.stage}</td>
                <td>{e.rule_id}</td>
                <td>{e.result}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
