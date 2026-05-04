"use client";

export default function InterviewForm({
  schedInterviewer,
  setSchedInterviewer,
  schedAt,
  setSchedAt,
  schedDuration,
  setSchedDuration,
  schedLink,
  setSchedLink,
  schedNotes,
  setSchedNotes,
  onSchedule,
  disabled,
}: any) {
  return (
    <>
      <div className="grid grid-2">
        <div><label>Interviewer email</label><input type="email" list="email-domain-suggest" value={schedInterviewer} onChange={(e) => setSchedInterviewer(e.target.value)} placeholder="name@gmail.com" /></div>
        <div><label>Scheduled at</label><input type="datetime-local" value={schedAt} onChange={(e) => setSchedAt(e.target.value)} /></div>
        <div><label>Duration mins</label><input type="number" min={15} value={schedDuration} onChange={(e) => setSchedDuration(e.target.value)} /></div>
        <div><label>Meeting link</label><input value={schedLink} onChange={(e) => setSchedLink(e.target.value)} placeholder="https://meet..." /></div>
      </div>
      <div style={{ marginTop: 10 }}><label>Notes</label><textarea rows={2} value={schedNotes} onChange={(e) => setSchedNotes(e.target.value)} placeholder="Type notes, email or @mention..." /></div>
      <button style={{ marginTop: 8 }} onClick={onSchedule} disabled={disabled}>Schedule Interview</button>
    </>
  );
}
