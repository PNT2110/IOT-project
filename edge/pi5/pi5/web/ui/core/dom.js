// core/dom.js - DOM builder and modal primitives for Pi 5 local interface

export const modalRoot = document.getElementById("modal-root");

export function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === false || value == null) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key in node && key !== "list") node[key] = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

export function banner(kind, text) {
  return h("div", { class: `banner ${kind}`, role: kind === "error" ? "alert" : "status" }, text);
}

export function form(fields, submitLabel, onSubmit) {
  const status = h("div");
  const button = h("button", { class: "primary", type: "submit" }, submitLabel);
  const node = h("form", {
    onsubmit: async (event) => {
      event.preventDefault();
      button.disabled = true;
      status.replaceChildren();
      try { await onSubmit(Object.fromEntries(new FormData(node))); }
      catch (error) { status.replaceChildren(banner("error", error.message)); }
      finally { button.disabled = false; }
    },
  }, fields, status, button);
  return node;
}

export function field(label, name, attrs = {}) {
  return h("label", {}, label, h("input", { name, required: true, ...attrs }));
}

export function closeModal() {
  const root = modalRoot || document.getElementById("modal-root");
  if (root) root.replaceChildren();
}

export function modal(title, ...content) {
  const root = modalRoot || document.getElementById("modal-root");
  const dialog = h("section", { class: "dialog", role: "dialog", "aria-modal": "true", "aria-label": title },
    h("div", { class: "row between" }, h("h2", {}, title), h("button", { type: "button", "aria-label": "Đóng", onclick: closeModal }, "×")), content);
  if (root) {
    root.replaceChildren(h("div", { class: "overlay", onmousedown: (event) => { if (event.target === event.currentTarget) closeModal(); } }, dialog));
  }
  dialog.querySelector("input, select, textarea, button.primary")?.focus();
}
