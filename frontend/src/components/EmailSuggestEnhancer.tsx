"use client";
import { useEffect } from "react";

export default function EmailSuggestEnhancer() {
  useEffect(() => {
    const apply = () => {
      const inputs = Array.from(document.querySelectorAll('input[type="email"], input[placeholder*="email" i], input[name*="email" i], input[placeholder*="@"], textarea[placeholder*="@"]')) as HTMLInputElement[];
      for (const el of inputs as any[]) {
        el.setAttribute("list", "email-domain-suggest");
        el.setAttribute("autocomplete", "email");
        if (!el.getAttribute("placeholder")) el.setAttribute("placeholder", "name@gmail.com");
      }
    };
    apply();
    const mo = new MutationObserver(() => apply());
    mo.observe(document.body, { childList: true, subtree: true });
    return () => mo.disconnect();
  }, []);
  return <datalist id="email-domain-suggest"><option value="@gmail.com" /><option value="@outlook.com" /><option value="@yahoo.com" /></datalist>;
}
