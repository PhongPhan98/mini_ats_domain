"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const ALLOWED_TAGS = new Set(["P", "DIV", "BR", "STRONG", "B", "EM", "I", "U", "UL", "OL", "LI", "H2", "H3", "SPAN"]);
const SAFE_STYLE = /^(?:background-color|color|text-align):\s*(?:#[0-9a-f]{3,8}|rgb\([\d\s,.%]+\)|rgba\([\d\s,.%]+\)|left|center|right|yellow|transparent)$/i;

function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function plainToHtml(value: string, listMode: boolean) {
  const lines = value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length) return "<p><br></p>";
  if (listMode) return `<ul>${lines.map((line) => `<li>${escapeHtml(line.replace(/^[-•]\s*/, ""))}</li>`).join("")}</ul>`;
  return lines.map((line) => `<p>${escapeHtml(line)}</p>`).join("");
}

export function sanitizeRichText(value: string) {
  if (typeof window === "undefined" || !value) return "";
  const doc = new DOMParser().parseFromString(`<div>${value}</div>`, "text/html");
  const root = doc.body.firstElementChild as HTMLElement | null;
  if (!root) return "";
  const clean = (node: Node): Node | null => {
    if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent || "");
    if (node.nodeType !== Node.ELEMENT_NODE) return null;
    const source = node as HTMLElement;
    if (!ALLOWED_TAGS.has(source.tagName)) {
      const fragment = document.createDocumentFragment();
      Array.from(source.childNodes).forEach((child) => { const safe = clean(child); if (safe) fragment.appendChild(safe); });
      return fragment;
    }
    const element = document.createElement(source.tagName.toLowerCase());
    const styles = (source.getAttribute("style") || "").split(";").map((item) => item.trim()).filter((item) => SAFE_STYLE.test(item));
    if (styles.length) element.setAttribute("style", styles.join("; "));
    Array.from(source.childNodes).forEach((child) => { const safe = clean(child); if (safe) element.appendChild(safe); });
    return element;
  };
  const output = document.createElement("div");
  Array.from(root.childNodes).forEach((child) => { const safe = clean(child); if (safe) output.appendChild(safe); });
  return output.innerHTML.slice(0, 50000);
}

function normalizedEditorText(editor: HTMLElement) {
  return editor.innerText
    .replace(/\u00a0/g, " ")
    .split("\n")
    .map((line) => line.replace(/^[•]\s*/, "").trimEnd())
    .filter((line, index, lines) => line.trim() || (index > 0 && lines[index - 1].trim()))
    .join("\n")
    .trim();
}

export default function RichTextField({ label, value, html, onSave, listMode = false, readOnly = false, className = "" }: {
  label: string;
  value: string;
  html?: string;
  onSave: (plainText: string, formattedHtml: string) => void;
  listMode?: boolean;
  readOnly?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const editorRef = useRef<HTMLDivElement>(null);
  const selectionRef = useRef<Range | null>(null);
  const display = useMemo(() => value.trim() || "No details added yet", [value]);

  useEffect(() => {
    if (!open || !editorRef.current) return;
    editorRef.current.innerHTML = sanitizeRichText(html || plainToHtml(value, listMode)) || plainToHtml(value, listMode);
    setWordCount(normalizedEditorText(editorRef.current).split(/\s+/).filter(Boolean).length);
    editorRef.current.focus();
  }, [open, html, value, listMode]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const rememberSelection = () => {
    const selection = window.getSelection();
    if (selection?.rangeCount) selectionRef.current = selection.getRangeAt(0).cloneRange();
    if (editorRef.current) setWordCount(normalizedEditorText(editorRef.current).split(/\s+/).filter(Boolean).length);
  };
  const command = (name: string, argument?: string) => {
    editorRef.current?.focus();
    if (selectionRef.current) {
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(selectionRef.current);
    }
    document.execCommand(name, false, argument);
    rememberSelection();
  };
  const keepSelection = (event: React.MouseEvent) => event.preventDefault();

  return <div className={`rich-field ${className}`}>
    <div className="rich-field-label"><label>{label}</label><span>{html ? "Formatted" : "Plain text"}</span></div>
    <button type="button" className="rich-field-preview" onClick={() => setOpen(true)} aria-label={`${readOnly ? "View" : "Edit"} ${label}`}>
      <span>{display}</span>
      <strong>{readOnly ? "View" : "Open editor"} ↗</strong>
    </button>
    {open && <div className="modal-overlay rich-editor-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
      <section className="modal-card rich-editor-modal" role="dialog" aria-modal="true" aria-label={`${readOnly ? "View" : "Edit"} ${label}`}>
        <div className="rich-editor-header">
          <div><span className="eyebrow">Candidate profile</span><h2>{label}</h2><small>{readOnly ? "Formatted view" : "Select text, then use the formatting tools."}</small></div>
          <button type="button" className="rich-editor-close" onClick={() => setOpen(false)} aria-label="Close editor">×</button>
        </div>
        {!readOnly && <div className="rich-editor-toolbar" role="toolbar" aria-label="Text formatting">
          <select aria-label="Text style" defaultValue="p" onChange={(event) => command("formatBlock", event.target.value)}>
            <option value="p">Normal text</option><option value="h2">Heading</option><option value="h3">Subheading</option>
          </select>
          <span className="rich-toolbar-group">
            <button type="button" onMouseDown={keepSelection} onClick={() => command("bold")} title="Bold"><b>B</b></button>
            <button type="button" onMouseDown={keepSelection} onClick={() => command("italic")} title="Italic"><i>I</i></button>
            <button type="button" onMouseDown={keepSelection} onClick={() => command("underline")} title="Underline"><u>U</u></button>
          </span>
          <span className="rich-toolbar-group">
            <button type="button" onMouseDown={keepSelection} onClick={() => command("insertUnorderedList")} title="Bullet list">• List</button>
            <button type="button" onMouseDown={keepSelection} onClick={() => command("insertOrderedList")} title="Numbered list">1. List</button>
          </span>
          <span className="rich-toolbar-group" aria-label="Highlight color">
            <button className="highlight-yellow" type="button" onMouseDown={keepSelection} onClick={() => command("hiliteColor", "#fff2a8")} title="Yellow highlight">A</button>
            <button className="highlight-green" type="button" onMouseDown={keepSelection} onClick={() => command("hiliteColor", "#ccebd8")} title="Green highlight">A</button>
            <button className="highlight-blue" type="button" onMouseDown={keepSelection} onClick={() => command("hiliteColor", "#cfe5ff")} title="Blue highlight">A</button>
          </span>
          <span className="rich-toolbar-group">
            <button type="button" onMouseDown={keepSelection} onClick={() => command("justifyLeft")} title="Align left">≡</button>
            <button type="button" onMouseDown={keepSelection} onClick={() => command("justifyCenter")} title="Align center">≣</button>
            <button type="button" onMouseDown={keepSelection} onClick={() => command("removeFormat")} title="Clear formatting">Clear</button>
          </span>
          <span className="rich-toolbar-group rich-toolbar-history">
            <button type="button" onMouseDown={keepSelection} onClick={() => command("undo")} title="Undo">↶</button>
            <button type="button" onMouseDown={keepSelection} onClick={() => command("redo")} title="Redo">↷</button>
          </span>
        </div>}
        <div className="rich-editor-paper-wrap">
          <div ref={editorRef} className={`rich-editor-paper ${readOnly ? "rich-editor-readonly" : ""}`} contentEditable={!readOnly} suppressContentEditableWarning onInput={rememberSelection} onKeyUp={rememberSelection} onMouseUp={rememberSelection} />
        </div>
        <div className="rich-editor-footer">
          <small>{wordCount} {wordCount === 1 ? "word" : "words"} · formatting is saved with this candidate</small>
          <div className="toolbar-actions"><button type="button" className="btn-outline" onClick={() => setOpen(false)}>{readOnly ? "Close" : "Cancel"}</button>{!readOnly && <button type="button" onClick={() => { if (!editorRef.current) return; const plain = normalizedEditorText(editorRef.current); const safeHtml = sanitizeRichText(editorRef.current.innerHTML); onSave(plain, safeHtml); setOpen(false); }}>Save content</button>}</div>
        </div>
      </section>
    </div>}
  </div>;
}
