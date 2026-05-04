"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import { useAppLanguage } from "../../lib/language";

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
  const [selectedRuleIdx, setSelectedRuleIdx] = useState<number | null>(null);
  const [ruleDraft, setRuleDraft] = useState<Rule | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);
  const { t } = useAppLanguage();

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
        <h2 style={{ marginTop: 0 }}>{t("automation_title")}</h2>
        <small>{t("automation_hint")}</small>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3 style={{ margin: 0 }}>{t("rules")} <span className="chip">{rules.length}</span></h3>
          <div className="toolbar-actions">
            <button className="btn-outline" onClick={addRule}>{t("add_rule")}</button>
            <button onClick={saveRules} disabled={saving}>{saving ? t("saving") : t("save_rules")}</button>
          </div>
        </div>

        
        <div className="card" style={{ marginBottom: 10 }}>
          <h4 style={{ marginTop: 0, marginBottom: 8 }}>Automation Jobs</h4>
          <div className="grid" style={{ gap: 6 }}>
            {rules.map((r, idx) => (
              <div key={`pick-${r.id}-${idx}`} className="toolbar" style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 8 }}>
                <div><strong>{r.id}</strong><small style={{ display: "block" }}>Stage: {r.on_stage} • {r.enabled ? "Enabled" : "Disabled"}</small></div>
                <div className="toolbar-actions">
                  <button style={{ width: "auto" }} onClick={() => { setSelectedRuleIdx(idx); setRuleDraft(JSON.parse(JSON.stringify(r))); setTimeout(() => document.getElementById('rule-editor-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50); }}>Edit</button>
                </div>
              </div>
            ))}
            {!rules.length ? <small>No automation jobs yet</small> : null}
          </div>
        </div>

        <div className="grid">
          {rules.map((r, idx) => (
            <div key={r.id} className="card rule-card" style={{ marginBottom: 8 }}>
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
                <button className="btn-outline" style={{ width: "auto" }} onClick={() => { setSelectedRuleIdx(idx); setRuleDraft(JSON.parse(JSON.stringify(r))); }}>View / Edit</button>
                <button className="btn-outline" onClick={(e) => { e.stopPropagation(); addAction(idx, "log"); }}>+ Log</button>
                <button className="btn-outline" onClick={(e) => { e.stopPropagation(); addAction(idx, "email"); }}>+ Email</button>
                <button className="btn-outline" onClick={(e) => { e.stopPropagation(); addAction(idx, "webhook"); }}>+ Webhook</button>
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
          {!rules.length && <small>{t("no_rules")}</small>}
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <div>
            <h3 style={{ margin: 0 }}>Automation workflow</h3>
            <small>Create stage-based rules, review actions, then save once.</small>
          </div>
          <div className="chip-wrap">
            <span className="chip">1) Define stage</span>
            <span className="chip">2) Add actions</span>
            <span className="chip">3) Save rules</span>
          </div>
        </div>
      </div>


      {selectedEvent ? <div className="card"><div className="toolbar"><h3 style={{ margin: 0 }}>Event Detail</h3><button className="btn-outline" style={{ width: "auto" }} onClick={() => setSelectedEvent(null)}>Close</button></div><pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(selectedEvent, null, 2)}</pre></div> : null}

      {selectedRuleIdx !== null && ruleDraft ? (
        <div id="rule-editor-panel" className="card">
          <div className="toolbar">
            <h3 style={{ margin: 0 }}>Selected Automation Rule Editor</h3>
            <div className="toolbar-actions">
              <button className="btn-outline" style={{ width: "auto" }} onClick={() => setSelectedRuleIdx(null)}>Close</button>
              <button className="btn-outline" style={{ width: "auto" }} onClick={() => setRules((prev)=>[...prev,{...ruleDraft,id:`${ruleDraft.id}-copy-${Date.now()}`}])}>Duplicate</button>
              <button className="btn-outline" style={{ width: "auto" }} onClick={() => { setRules((prev) => prev.filter((_, i) => i !== selectedRuleIdx)); setSelectedRuleIdx(null); }}>Delete</button>
              <button style={{ width: "auto" }} onClick={() => { if (selectedRuleIdx!==null) setRules((prev)=>prev.map((r,i)=>i===selectedRuleIdx?ruleDraft:r)); }}>Save Changes</button>
            </div>
          </div>
          <div className="grid grid-3">
            <div><label>Rule ID</label><input value={ruleDraft.id} onChange={(e)=>setRuleDraft({...ruleDraft,id:e.target.value})} /></div>
            <div><label>On Stage</label><select value={ruleDraft.on_stage} onChange={(e)=>setRuleDraft({...ruleDraft,on_stage:e.target.value})}>{STAGES.map((st)=><option key={st} value={st}>{st}</option>)}</select></div>
            <div><label>Enabled</label><select value={ruleDraft.enabled?"1":"0"} onChange={(e)=>setRuleDraft({...ruleDraft,enabled:e.target.value==="1"})}><option value="1">Enabled</option><option value="0">Disabled</option></select></div>
          </div>
        </div>
      ) : null}

      <div className="card">
        <div className="toolbar"><h3 style={{ margin: 0 }}>{t("event_log")}</h3><div className="toolbar-actions"><small>Recent automation runs and outcomes.</small><button className="btn-outline" style={{ width: "auto" }} onClick={async () => { await apiPost("/api/automation/events/clear", {}); setEvents([]); }}>Clear All</button></div></div>
        <div style={{ maxHeight: 320, overflow: "auto", border: "1px solid var(--border)", borderRadius: 8 }}><table>
          <thead>
            <tr>
              <th>{t("time")}</th>
              <th>{t("candidate")}</th>
              <th>{t("stage")}</th>
              <th>{t("rule")}</th>
              <th>{t("result")}</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={`${e.timestamp}-${i}`} style={{ cursor: "pointer" }} onClick={() => setSelectedEvent(e)}>
                <td>{e.timestamp}</td>
                <td>{e.candidate_name}</td>
                <td>{e.stage}</td>
                <td>{e.rule_id}</td>
                <td>{e.result}</td><td><button className="btn-outline" style={{ width: "auto" }} onClick={(ev) => { ev.stopPropagation(); setEvents((prev) => prev.filter((_, idx) => idx !== i)); }}>Delete</button></td></tr>
            ))}
            {!events.length && (
              <tr><td colSpan={6}><small>{t("no_events")}</small></td></tr>
            )}
          </tbody>
        </table></div>
      </div>
          </div>
  );
}
