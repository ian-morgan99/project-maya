// serve/web/strata-models.js - the Strata model picker: every folder in LM Studio's model folder, classified as
// Strata-runnable (Qwen3.8-Flash-Next / qwen4exp), Maya-runnable (GLM, DeepSeek, MiniMax, CYBER-FROST), or unsupported.
// Nothing is moved, deleted, or changed - just a look at what could run where.
import {html, useEffect, useRef, useState} from "./preact.js";
import {api, ctxfmt, esc, fmt, modelName} from "./lib.js";
import {S, confirmDialog, emit, toast} from "./state.js";
import {setSide, showView} from "./sidebar.js";
import {Icon, ModelLogo, Seg, trapTab} from "./ui.js";

export const SS = {data: null, err: null, loading: false};

export async function loadStrataModels() {
  SS.loading = true;
  emit();
  try {
    SS.data = await api("api/strata-models");
    SS.err = null;
  } catch (e) {
    SS.err = e.message;
    SS.data = null;
  }
  SS.loading = false;
  emit();
  return SS.data;
}

const familyLabel = (f) => ({
  "strata_qwen": "Strata (Qwen3.8-Flash-Next / qwen4exp)",
  "maya_glm": "Maya · GLM-5.3-Flash",
  "maya_deepseek": "Maya · DeepSeek-V4.1-Flash-1017",
  "maya_minimax": "Maya · MiniMax-M3.1-Flash",
  "maya_qwen": "Maya · CYBER-FROST-3.8-PS",
  "unsupported": "Not supported",
})[f] || f;

const familyTone = (f) => ({
  "strata_qwen": "strata",
  "maya_glm": "maya",
  "maya_deepseek": "maya",
  "maya_minimax": "maya",
  "maya_qwen": "maya",
  "unsupported": "muted",
})[f] || "muted";

const gb = (b) => (b == null ? "–" : fmt(b / 1e9, b < 1e10 ? 1 : 0) + " GB");

function StrataModelsPage() {
  const ref = useRef(null);
  useEffect(() => { loadStrataModels(); }, []);
  const d = SS.data;
  const byFamily = {};
  if (d && d.models) for (const m of d.models) (byFamily[m.family] || (byFamily[m.family] = [])).push(m);
  const order = ["strata_qwen", "maya_glm", "maya_deepseek", "maya_minimax", "maya_qwen", "unsupported"];
  const groups = order.filter((f) => byFamily[f] && byFamily[f].length);

  return html`<div class="sm__page">
    <div class="sm__head">
      <span class="sm__title">Strata model sweep</span>
      <span class="sm__subtitle">${d ? `${d.total_folders} model folders · ${d.strata_support} Strata · ${d.maya_support} Maya · ${d.unsupported} unsupported · ${gb(d.total_gb)} total` : "Loading…"}</span>
    </div>

    ${SS.err ? html`<div class="sm__err">Could not load the sweep: ${esc(SS.err)}</div>` : null}

    ${groups.map((f) => {
      const ms = byFamily[f];
      const tone = familyTone(f);
      return html`<section class="sm__group sm__group--${tone}">
        <h2><span class="sm__badge sm__badge--${tone}">${familyLabel(f)}</h2>
        <span class="sm__count">${ms.length} folder${ms.length !== 1 ? "s" : ""}</span></h2>
        <div class="sm__list">
          ${ms.map((m) => html`<${StrataModelCard} key=${m.folder} m=${m}/>`)}
        </div>
      </section>`;
    })}
  </div>`;
}

function StrataModelCard({m}) {
  const runnable = m.strata_support || m.maya_support;
  const tone = m.strata_support ? "strata" : m.maya_support ? "maya" : "muted";
  const canRun = m.strata_support ? "Strata can run this (Qwen3.8-Flash-Next / qwen4exp architecture)"
    : m.maya_support ? "Maya can run this (GLM / DeepSeek / MiniMax / CYBER-FROST engine)"
    : "No engine supports this model";
  return html`<article class="sm__card sm__card--${tone}">
    <div class="sm__card__head">
      <div class="sm__card__name">
        <span class="sm__badge sm__badge--${tone}">${familyLabel(m.family)}</span>
        <b>${esc(m.folder)}</b>
      </div>
      <span class="sm__card__size">${gb(m.total_gb)} · ${m.file_count} file${m.file_count !== 1 ? "s" : ""}</span>
    </div>
    <p class="sm__card__notes">${esc(m.notes)}</p>
    <div class="sm__card__facts">
      <div><span class="sm__fact__label">Strata</span><span class="sm__fact__val ${m.strata_support ? "yes" : "no"}">${m.strata_support ? "Yes" : "No"}</span></div>
      <div><span class="sm__fact__label">Maya</span><span class="sm__fact__val ${m.maya_support ? "yes" : "no"}">${m.maya_support ? "Yes" : "No"}</span></div>
      <div><span class="sm__fact__label">GGUFs</span><span class="sm__fact__val">${m.gguf_count}</span></div>
      <div><span class="sm__fact__label">Quant</span><span class="sm__fact__val">${esc(m.quant)}</span></div>
    </div>
    <p class="sm__card__hint">${canRun}</p>
    ${m.files.length ? html`<details class="sm__files"><summary>${m.files.length} file${m.files.length !== 1 ? "s" : ""}</summary>
      <ul class="sm__file-list">${m.files.map((f) => html`<li>${esc(f.name)} · ${gb(f.size)}</li>`)}</ul>
    </details>` : null}
  </article>`;
}
