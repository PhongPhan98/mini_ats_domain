"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";

type Action = {
  type: "log" | "email" | "webhook";
  message?: string;
  url?: string;
  to?: string;
  subject?: string;
  body?: string;
};

type Rule = {
  id: string;
  enabled: boolean;
  on_stage: string;
  actions: Action[];
};

const STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"];

export default function AutomationPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const [rulesData, eventsData] = await Promise.all([
      apiGet<{ rules: Rule[] }>("/api/automation/rules"),
      apiGet<{ events: any[] }>("/api/automation/events?limit=120"),
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

  const addAction = (idx: number, type: Action["type"]) => {
    setRules((prev) =>
      prev.map((r, i) =>
        i === idx
          ? {
              ...r,
              actions: [
                ...r.actions,
                type === "email"
                  ? { type, subject: "Candidate stage update", body: "Hi {{candidate_name}}, status: {{stage}}" }
                  : type === "webhook"
                  ? { type, url: "https://example.com/webhook" }
                  : { type, message: "Stage changed" },
              ],
            }
          : r
      )
    );
  };

  const updateRule = (idx: number, patch: Partial<Rule>) => {
    setRules((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  };

  const updateAction = (rIdx: number, aIdx: number, patch: Partial<Action>) => {
    setRules((prev) =>
      prev.map((r, i) =>
        i === rIdx
          ? {
              ...r,
              actions: r.actions.map((a, j) => (j === aIdx ? { ...a, ...patch } : a)),
            }
          : r
      )
    );
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
        <small>Trigger log/email/webhook actions on stage change.</small>
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
                  <input value={r.id} onChange={(e) => updateRule(idx, { id: e.target.value })} />
                </div>
                <div>
                  <label>On Stage</label>
                  <select value={r.on_stage} onChange={(e) => updateRule(idx, { on_stage: e.target.value })}>
                    {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label>Enabled</label>
                  <select value={r.enabled ? "1" : "0"} onChange={(e) => updateRule(idx, { enabled: e.target.value === "1" })}>
                    <option value="1">Enabled</option>
                    <option value="0">Disabled</option>
                  </select>
                </div>
              </div>

              <div style={{ marginTop: 12 }} className="toolbar-actions">
                <button className="btn-outline" onClick={() => addAction(idx, "log")}>+ Log</button>
                <button className="btn-outline" onClick={() => addAction(idx, "email")}>+ Email</button>
                <button className="btn-outline" onClick={() => addAction(idx, "webhook")}>+ Webhook</button>
              </div>

              <div className="grid" style={{ marginTop: 10 }}>
                {r.actions.map((a, aIdx) => (
                  <div key={`${r.id}-${aIdx}`} className="card" style={{ marginBottom: 6 }}>
                    <small>Action: {a.type}</small>
                    {a.type === "log" && (
                      <input value={a.message || ""} onChange={(e) => updateAction(idx, aIdx, { message: e.target.value })} placeholder="Log message" />
                    )}
                    {a.type === "email" && (
                      <div className="grid">
                        <input value={a.to || ""} onChange={(e) => updateAction(idx, aIdx, { to: e.target.value })} placeholder="To email (optional, fallback candidate email)" />
                        <input value={a.subject || ""} onChange={(e) => updateAction(idx, aIdx, { subject: e.target.value })} placeholder="Subject" />
                        <textarea rows={3} value={a.body || ""} onChange={(e) => updateAction(idx, aIdx, { body: e.target.value })} placeholder="Body" />
                      </div>
                    )}
                    {a.type === "webhook" && (
                      <input value={a.url || ""} onChange={(e) => updateAction(idx, aIdx, { url: e.target.value })} placeholder="Webhook URL" />
                    )}
                  </div>
                ))}
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
