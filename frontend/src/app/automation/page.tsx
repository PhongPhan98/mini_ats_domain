"use client";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";

export default function AutomationPage() {
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("Interview Invitation");
  const [body, setBody] = useState("Hello, you are invited to interview.");
  const [sendAt, setSendAt] = useState("");
  const [items, setItems] = useState<any[]>([]);

  const load = async () => {
    const d = await apiGet<{ items: any[] }>("/api/automation/email/schedules");
    setItems(d.items || []);
  };
  useEffect(() => { load(); }, []);

  return <div className="grid page-enter">
    <div className="card"><h2 style={{ marginTop: 0 }}>Email Scheduler</h2><small>Simple flow for HR: write email, send now or schedule send.</small></div>
    <div className="card"><div className="grid">
      <input type="email" list="email-domain-suggest" placeholder="candidate@gmail.com" value={to} onChange={(e)=>setTo(e.target.value)} />
      <input placeholder="Subject" value={subject} onChange={(e)=>setSubject(e.target.value)} />
      <textarea rows={6} placeholder="Email content" value={body} onChange={(e)=>setBody(e.target.value)} />
      <input type="datetime-local" value={sendAt} onChange={(e)=>setSendAt(e.target.value)} />
      <div className="toolbar-actions"><button onClick={async()=>{await apiPost('/api/automation/email/send-now',{to,subject,body});}}>Send Now</button><button className="btn-outline" onClick={async()=>{await apiPost('/api/automation/email/schedules',{to,subject,body,send_at:sendAt}); await load();}}>Schedule Send</button></div>
    </div></div>
    <div className="card"><h3 style={{ marginTop: 0 }}>Scheduled Emails</h3><div className="grid">{items.map((x)=><div key={x.id} className="card"><strong>{x.to}</strong><small>{x.subject}</small><small>{x.send_at}</small><small>{x.status}</small></div>)}{!items.length?<small>No scheduled emails yet</small>:null}</div></div>
  </div>;
}
