const $ = (id) => document.getElementById(id);
const ns = "http://www.w3.org/2000/svg";
const labels = { free: "Livre", occupied: "Ocupada", unknown: "Desconhecida" };
const colors = { free: "#45d48d", occupied: "#ff7575", unknown: "#eac471" };
let current = null;
let drawing = false;
let points = [];
let selectionSize = null;
let frozenUrl = null;
let retryTimer = null;
let settingsLoaded = false;
let busy = false;

function notice(message, error = false) {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
}

async function api(path, method = "GET", body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 7000);
  try {
    const response = await fetch(path, {
      method, signal: controller.signal,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail
        : Array.isArray(data.detail) ? data.detail.map((item) => item.msg.replace(/^Value error, /, "")).join(" ")
        : "Confira os valores informados.";
      throw new Error(detail);
    }
    return data;
  } finally { clearTimeout(timeout); }
}

function startVideo() {
  if (drawing) return;
  clearTimeout(retryTimer);
  $("camera-image").src = `/api/video?t=${Date.now()}`;
}
$("camera-image").addEventListener("error", () => {
  if (!drawing) retryTimer = setTimeout(startVideo, 1800);
});

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(ns, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  return element;
}

function orderedCorners(corners) {
  const center = corners.reduce(([x, y], point) => [x + point[0] / 4, y + point[1] / 4], [0, 0]);
  return [...corners].sort((a, b) =>
    Math.atan2(a[1] - center[1], a[0] - center[0]) - Math.atan2(b[1] - center[1], b[0] - center[0]));
}

function selectionError(corners) {
  if (corners.length !== 4) return "Marque os quatro cantos antes de salvar.";
  let area = 0;
  let direction = 0;
  for (let i = 0; i < 4; i++) {
    const a = corners[i], b = corners[(i + 1) % 4], c = corners[(i + 2) % 4];
    const cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
    if (Math.abs(cross) < 1e-8 || (direction && Math.sign(cross) !== direction)) {
      return "Marque quatro cantos distintos no contorno da vaga. Use Remover último ponto para corrigir.";
    }
    direction = Math.sign(cross);
    area += a[0] * b[1] - b[0] * a[1];
  }
  if (Math.abs(area) / 2 < 0.0005) return "A região ficou pequena demais. Amplie a seleção dos cantos da vaga.";
  return null;
}

function drawRegions() {
  const svg = $("regions");
  svg.replaceChildren();
  if (!current) return;
  for (const spot of current.spots) {
    if (!spot.camera_roi) continue;
    const color = colors[spot.state] || colors.unknown;
    svg.append(svgElement("polygon", {
      points: spot.camera_roi.map((point) => point.join(",")).join(" "),
      fill: color, stroke: color, class: "region", opacity: drawing ? ".3" : "1",
    }));
    if (!drawing) {
      const [x, y] = spot.camera_roi[0];
      const text = svgElement("text", { x: Math.min(.9, x + .01), y: Math.max(.03, y - .012), class: "region-label" });
      text.textContent = `${spot.id} · ${labels[spot.state]}`;
      svg.append(text);
    }
  }
  if (drawing && points.length) {
    const outline = points.length === 4 ? orderedCorners(points) : points;
    svg.append(svgElement(points.length === 4 ? "polygon" : "polyline", {
      points: outline.map((point) => point.join(",")).join(" "),
      fill: points.length === 4 ? "#36ce8a" : "none", stroke: "#65ffc0", class: "region",
    }));
    points.forEach(([x, y]) => svg.append(svgElement("circle", { cx: x, cy: y, r: ".008", class: "region-point" })));
  }
  $("point-counter").textContent = `${points.length} de 4 pontos`;
  $("save-region").disabled = points.length !== 4 || busy;
  $("undo-point").disabled = points.length === 0 || busy;
}

function controls() {
  if (!current) return;
  $("select-region").disabled = !current.camera_online || drawing || busy;
  $("save-reference").disabled = !current.camera_online || current.calibrated_count === 0 || !$("confirm-empty").checked || drawing || busy;
  $("toggle-analysis").disabled = busy || drawing || (!current.analysis_enabled && !(current.camera_online && current.reference_ready));
  $("toggle-analysis").textContent = current.analysis_enabled ? "Pausar análise" : "Iniciar análise";
  $("selection-controls").hidden = !drawing;
  $("selection-hint").hidden = !drawing;
  $("camera-stage").classList.toggle("selecting", drawing);
  $("spot-select").disabled = drawing || busy;
}

function render(data) {
  const wasOnline = current?.camera_online;
  current = data;
  for (const key of ["total", "free", "occupied", "unknown"]) $(`count-${key}`).textContent = data.counts[key];
  $("connection").textContent = data.camera_online ? "Câmera conectada" : "Câmera sem imagem";
  $("connection").classList.toggle("online", data.camera_online);
  $("live-tag").textContent = drawing ? "IMAGEM CONGELADA" : data.camera_online ? "AO VIVO" : "SEM SINAL";
  $("live-tag").classList.toggle("active", data.camera_online && !drawing);
  $("camera-origin").textContent = `Fonte: ${data.camera_url}`;
  $("camera-stage").classList.toggle("offline", !data.camera_online && !drawing);
  $("camera-message").hidden = data.camera_online || drawing;
  if (!data.camera_online) {
    $("camera-message").querySelector("strong").textContent = "Sem imagem recente";
    $("camera-message").querySelector("span:last-child").textContent =
      data.camera_error || "Confira se o computador está na mesma rede da ESP32-CAM.";
  }
  $("camera-image").hidden = !data.image_width && !drawing;
  if (data.image_width && data.image_height) {
    if (!drawing) $("camera-stage").style.aspectRatio = `${data.image_width} / ${data.image_height}`;
    $("video-info").textContent = `${data.image_width} × ${data.image_height} · ${data.fps.toFixed(1)} quadros/s`;
  }
  $("calibrated-count").textContent = `${data.calibrated_count} de ${data.counts.total} regiões calibradas`;
  $("reference-status").textContent = data.reference_ready ? "Referência pronta para o teste" : data.reference_note;
  $("reference-status").classList.toggle("ready", data.reference_ready);
  const selected = $("spot-select").value;
  if ($("spot-select").options.length !== data.spots.length) {
    $("spot-select").replaceChildren(...data.spots.map((spot) => {
      const option = document.createElement("option");
      option.value = spot.id;
      option.textContent = `${spot.id} · ${spot.label}`;
      return option;
    }));
    if (data.spots.some((spot) => spot.id === selected)) $("spot-select").value = selected;
  }
  $("spots").replaceChildren(...data.spots.map((spot) => {
    const card = document.createElement("div");
    card.className = `spot${spot.id === $("spot-select").value ? " selected" : ""}`;
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `Selecionar ${spot.label}`);
    const title = document.createElement("div");
    title.className = "spot-title";
    const name = document.createElement("strong");
    name.textContent = `${spot.id} · ${spot.label}`;
    const badge = document.createElement("span");
    badge.className = `spot-badge ${spot.state}`;
    badge.textContent = labels[spot.state];
    title.append(name, badge);
    const detail = document.createElement("p");
    detail.textContent = spot.camera_roi
      ? spot.reason + (spot.changed_ratio === null ? "" : ` Alteração: ${(spot.changed_ratio * 100).toFixed(1)}%.`)
      : "Selecione a região desta vaga na imagem.";
    card.append(title, detail);
    const choose = () => {
      if (!drawing) {
        $("spot-select").value = spot.id;
        drawRegions();
        document.querySelectorAll(".spot").forEach((item) => item.classList.remove("selected"));
        card.classList.add("selected");
      }
    };
    card.addEventListener("click", choose);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); }
    });
    return card;
  }));
  if (!settingsLoaded) {
    const settings = data.detection;
    $("pixel-threshold").value = settings.pixel_difference_threshold;
    $("free-threshold").value = (settings.free_max_changed_ratio * 100).toFixed(1);
    $("occupied-threshold").value = (settings.occupied_min_changed_ratio * 100).toFixed(1);
    $("confirmation-frames").value = settings.confirmation_frames;
    settingsLoaded = true;
  }
  if (data.camera_online && !wasOnline && !drawing) startVideo();
  controls();
  drawRegions();
}

async function action(work) {
  busy = true;
  controls();
  try { await work(); }
  catch (error) { notice(error.message || "Não foi possível concluir a operação.", true); }
  finally { busy = false; controls(); drawRegions(); }
}

function stopSelection() {
  drawing = false;
  points = [];
  if (frozenUrl) URL.revokeObjectURL(frozenUrl);
  frozenUrl = null;
  controls();
  drawRegions();
  startVideo();
}

$("select-region").addEventListener("click", () => action(async () => {
  const response = await fetch(`/api/frame.jpg?t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Não há imagem recente para selecionar a região.");
  selectionSize = { width: Number(response.headers.get("X-Frame-Width")), height: Number(response.headers.get("X-Frame-Height")) };
  const url = URL.createObjectURL(await response.blob());
  const loaded = new Image();
  loaded.src = url;
  try { await loaded.decode(); }
  catch (error) { URL.revokeObjectURL(url); throw error; }
  clearTimeout(retryTimer);
  frozenUrl = url;
  drawing = true;
  points = [];
  $("camera-image").src = frozenUrl;
  $("camera-image").hidden = false;
  $("camera-message").hidden = true;
  $("camera-stage").style.aspectRatio = `${selectionSize.width} / ${selectionSize.height}`;
  notice("Clique em quatro cantos distintos da vaga. O contorno é organizado automaticamente. Depois salve a região.");
}));
$("camera-stage").addEventListener("pointerdown", (event) => {
  if (!drawing || points.length >= 4 || busy) return;
  event.preventDefault();
  const rect = $("camera-stage").getBoundingClientRect();
  points.push([
    Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
    Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
  ]);
  if (points.length === 4) {
    const error = selectionError(orderedCorners(points));
    notice(error || "Quatro cantos marcados. Confira o contorno e clique em Salvar região.", Boolean(error));
  }
  drawRegions();
});
$("undo-point").addEventListener("click", () => { points.pop(); drawRegions(); });
$("cancel-region").addEventListener("click", stopSelection);
$("save-region").addEventListener("click", () => action(async () => {
  const corners = orderedCorners(points);
  const error = selectionError(corners);
  if (error) throw new Error(error);
  const data = await api(`/api/spots/${encodeURIComponent($("spot-select").value)}/roi`, "PUT", { points: corners, ...selectionSize });
  stopSelection();
  render(data);
  notice("Região salva. Remova os carros e capture a referência vazia.");
}));
$("confirm-empty").addEventListener("change", controls);
$("spot-select").addEventListener("change", () => { if (current) render(current); });
$("save-reference").addEventListener("click", () => action(async () => {
  const data = await api("/api/reference", "POST", { confirm_empty: $("confirm-empty").checked });
  $("confirm-empty").checked = false;
  render(data);
  notice("Referência vazia salva. Inicie a análise e coloque o carro na vaga.");
}));
$("toggle-analysis").addEventListener("click", () => action(async () => {
  const data = await api("/api/detection", "PUT", { enabled: !current.analysis_enabled });
  render(data);
  notice(data.analysis_enabled ? "Análise iniciada. Observe as confirmações antes de cada mudança." : "Análise pausada. O vídeo continua funcionando.");
}));
$("settings-form").addEventListener("submit", (event) => {
  event.preventDefault();
  action(async () => {
    const values = {
      pixel_difference_threshold: Number($("pixel-threshold").value),
      free_max_changed_ratio: Number($("free-threshold").value) / 100,
      occupied_min_changed_ratio: Number($("occupied-threshold").value) / 100,
      confirmation_frames: Number($("confirmation-frames").value),
    };
    if (!Object.values(values).every(Number.isFinite)) throw new Error("Preencha todos os ajustes.");
    render(await api("/api/detection", "PUT", values));
    notice("Ajustes salvos. As confirmações de estado foram reiniciadas.");
  });
});

async function poll() {
  try { render(await api("/api/status")); }
  catch (error) {
    if (current) {
      render({
        ...current, camera_online: false,
        camera_error: "Não foi possível consultar o computador. Confira o terminal do backend.",
        counts: { total: current.spots.length, free: 0, occupied: 0, unknown: current.spots.length },
        spots: current.spots.map((spot) => ({ ...spot, state: "unknown", reason: "Dados indisponíveis." })),
      });
    }
    $("connection").textContent = "Backend desconectado";
    $("connection").classList.remove("online");
  } finally { setTimeout(poll, 500); }
}
poll();
