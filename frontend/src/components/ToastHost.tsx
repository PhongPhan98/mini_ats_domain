"use client";

import { useEffect, useState } from "react";

type Toast = { id: number; message: string; type: "success" | "error" | "info" };

export default function ToastHost() {
  const [items, setItems] = useState<Toast[]>([]);

  useEffect(() => {
    const onToast = (e: Event) => {
      const d = (e as CustomEvent).detail || {};
      const item: Toast = {
        id: Date.now() + Math.floor(Math.random() * 1000),
        message: d.message || "Done",
        type: d.type || "info",
      };
      setItems((prev) => [item, ...prev].slice(0, 4));
      setTimeout(() => setItems((prev) => prev.filter((x) => x.id !== item.id)), 2600);
    };
    window.addEventListener("miniats:toast", onToast);
    return () => window.removeEventListener("miniats:toast", onToast);
  }, []);

  return (
    <div className="toast-host">
      {items.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}
