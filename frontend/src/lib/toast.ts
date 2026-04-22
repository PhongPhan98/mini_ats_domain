"use client";

export type ToastType = "success" | "error" | "info";

export function notify(message: string, type: ToastType = "info") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("miniats:toast", { detail: { message, type } }));
}
