/* =========================================================
   REFUGIA — Accesibilidad (reutilizable en todas las páginas)
   ---------------------------------------------------------
   Qué hace:
     • Leer en voz alta   (Web Speech API, voz en español)
     • Alto contraste     (se guarda entre páginas y visitas)
     • Ampliar texto      (100 % → 115 % → 130 % → 150 % → 100 %)

   Cómo usarlo en cualquier página:
     1. En el <head> (sin "defer", para aplicar las preferencias
        antes de pintar la página y evitar parpadeos):
          <link rel="stylesheet" href="css/accesibilidad.css">
          <script src="js/accesibilidad.js"></script>
     2. Botones con estos id (los mismos de mapa.html):
          id="btn-lector-voz"  id="btn-contraste"  id="btn-zoom"
        o con el atributo data-a11y="voz" | "contraste" | "zoom".
     3. (Opcional) Marca con data-a11y-leer la zona que se debe leer.
        Si no hay ninguna, se lee el <main>. Si el usuario selecciona
        un texto antes de pulsar el botón, se lee solo esa selección.

   API pública (window.Accesibilidad):
     leer(texto), detener(), alternarLectura(), alternarContraste(),
     ampliarTexto(), restablecer(), anunciar(texto, {visual}),
     definirLectura(funcionQueDevuelveTexto), estado
   ========================================================= */
(function () {
  "use strict";

  const CLAVE = "refugia:accesibilidad";
  const NIVELES_TEXTO = [100, 115, 130, 150];
  const MAX_FRAGMENTO = 220; // caracteres por fragmento de voz
  const raiz = document.documentElement;
  const voz = "speechSynthesis" in window ? window.speechSynthesis : null;

  // ---------------- Preferencias ----------------
  function cargarPreferencias() {
    const porDefecto = {
      contraste: window.matchMedia?.("(prefers-contrast: more)").matches ?? false,
      nivelTexto: 0,
    };
    try {
      return { ...porDefecto, ...JSON.parse(localStorage.getItem(CLAVE) || "{}") };
    } catch {
      return porDefecto; // modo privado o almacenamiento bloqueado
    }
  }

  function guardarPreferencias() {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(prefs));
    } catch {
      /* sin almacenamiento: la preferencia dura solo en esta página */
    }
  }

  // Estado (declarado antes de aplicar las preferencias)
  let prefs = cargarPreferencias();
  const botones = { voz: [], contraste: [], zoom: [] };
  let hablando = false;
  let sesionLectura = 0;
  let proveedorLectura = null;
  let seleccionPrevia = "";

  function aplicarPreferencias() {
    raiz.classList.toggle("a11y-contraste", Boolean(prefs.contraste));
    const nivel = NIVELES_TEXTO[prefs.nivelTexto] ?? 100;
    if (nivel === 100) delete raiz.dataset.a11yTexto;
    else raiz.dataset.a11yTexto = String(nivel);
    actualizarBotones();
  }

  // Se aplica de inmediato (el script está en el <head>)
  aplicarPreferencias();

  // ---------------- Botones ----------------

  function buscarBotones() {
    const porId = { voz: "btn-lector-voz", contraste: "btn-contraste", zoom: "btn-zoom" };
    for (const tipo of Object.keys(botones)) {
      const lista = new Set(document.querySelectorAll(`[data-a11y="${tipo}"]`));
      const conId = document.getElementById(porId[tipo]);
      if (conId) lista.add(conId);
      botones[tipo] = [...lista];
    }
  }

  function actualizarBotones() {
    const nivel = NIVELES_TEXTO[prefs.nivelTexto] ?? 100;
    const enMaximo = prefs.nivelTexto >= NIVELES_TEXTO.length - 1;

    botones.contraste.forEach((b) => b.setAttribute("aria-pressed", String(Boolean(prefs.contraste))));

    botones.zoom.forEach((b) => {
      b.setAttribute("aria-pressed", String(nivel > 100));
      b.setAttribute(
        "aria-label",
        enMaximo ? `Texto al ${nivel} %. Restablecer tamaño` : `Ampliar texto (ahora ${nivel} %)`
      );
      const icono = b.querySelector("i");
      if (icono) {
        icono.classList.toggle("bi-zoom-in", !enMaximo);
        icono.classList.toggle("bi-zoom-out", enMaximo);
      }
    });

    botones.voz.forEach((b) => {
      b.setAttribute("aria-pressed", String(hablando));
      b.setAttribute("aria-label", hablando ? "Detener lectura en voz alta" : "Leer en voz alta");
      const icono = b.querySelector("i");
      if (icono) {
        icono.classList.toggle("bi-volume-up-fill", !hablando);
        icono.classList.toggle("bi-stop-fill", hablando);
      }
      if (!voz) b.setAttribute("aria-disabled", "true");
    });
  }

  // ---------------- Avisos (lector de pantalla + aviso visual) ----------------
  let regionViva = null;
  let aviso = null;
  let temporizadorAviso = null;

  function crearRegiones() {
    if (regionViva) return;
    regionViva = document.createElement("div");
    regionViva.className = "a11y-sr-only";
    regionViva.setAttribute("role", "status");
    regionViva.setAttribute("aria-live", "polite");
    aviso = document.createElement("div");
    aviso.className = "a11y-aviso";
    aviso.setAttribute("aria-hidden", "true"); // el lector ya lo oye en la región viva
    document.body.append(regionViva, aviso);
  }

  function anunciar(texto, { visual = true } = {}) {
    if (!texto) return;
    if (!document.body) {
      document.addEventListener("DOMContentLoaded", () => anunciar(texto, { visual }), { once: true });
      return;
    }
    crearRegiones();
    // Vaciar y volver a escribir para que se anuncie aunque el texto se repita
    regionViva.textContent = "";
    setTimeout(() => (regionViva.textContent = texto), 60);

    if (visual) {
      aviso.textContent = texto;
      aviso.classList.add("a11y-aviso--visible");
      clearTimeout(temporizadorAviso);
      temporizadorAviso = setTimeout(() => aviso.classList.remove("a11y-aviso--visible"), 3500);
    }
  }

  // ---------------- Alto contraste ----------------
  function alternarContraste() {
    prefs.contraste = !prefs.contraste;
    guardarPreferencias();
    aplicarPreferencias();
    anunciar(prefs.contraste ? "Alto contraste activado" : "Alto contraste desactivado");
  }

  // ---------------- Tamaño del texto ----------------
  function ampliarTexto() {
    prefs.nivelTexto = (prefs.nivelTexto + 1) % NIVELES_TEXTO.length;
    guardarPreferencias();
    aplicarPreferencias();
    anunciar(`Tamaño del texto: ${NIVELES_TEXTO[prefs.nivelTexto]} %`);
  }

  function restablecer() {
    prefs = { contraste: false, nivelTexto: 0 };
    guardarPreferencias();
    detener();
    aplicarPreferencias();
    anunciar("Ajustes de accesibilidad restablecidos");
  }

  // ---------------- Lectura en voz alta ----------------

  function elegirVoz() {
    if (!voz) return null;
    const voces = voz.getVoices().filter((v) => v.lang?.toLowerCase().startsWith("es"));
    const preferencia = ["es-co", "es-419", "es-mx", "es-us", "es-es"];
    for (const idioma of preferencia) {
      const encontrada = voces.find((v) => v.lang.toLowerCase().replace("_", "-") === idioma);
      if (encontrada) return encontrada;
    }
    return voces[0] || null;
  }

  // Chrome corta las frases muy largas: se divide el texto en fragmentos
  function dividirTexto(texto) {
    const frases = texto.split(/(?<=[.!?;:])\s+|\n+/).map((f) => f.trim()).filter(Boolean);
    const fragmentos = [];
    let actual = "";
    for (const frase of frases) {
      if ((actual + " " + frase).length > MAX_FRAGMENTO && actual) {
        fragmentos.push(actual);
        actual = frase;
      } else {
        actual = actual ? `${actual} ${frase}` : frase;
      }
    }
    if (actual) fragmentos.push(actual);
    // Una frase sola más larga que el máximo se corta por palabras
    return fragmentos.flatMap((f) =>
      f.length <= MAX_FRAGMENTO ? [f] : f.match(new RegExp(`.{1,${MAX_FRAGMENTO}}(\\s|$)`, "g")) || [f]
    );
  }

  function visible(el) {
    return el && !el.hidden && el.getClientRects().length > 0;
  }

  function textoDeLaPagina() {
    if (seleccionPrevia) return seleccionPrevia;
    if (proveedorLectura) {
      try {
        const texto = proveedorLectura();
        if (texto) return texto;
      } catch (e) {
        console.warn("[Accesibilidad] Error en el proveedor de lectura:", e);
      }
    }
    const zona =
      [...document.querySelectorAll("[data-a11y-leer]")].find(visible) ||
      document.querySelector("main") ||
      document.body;
    return zona.innerText;
  }

  function leer(texto) {
    if (!voz) {
      anunciar("Tu navegador no permite la lectura en voz alta.");
      return;
    }
    const limpio = (texto || "").replace(/\s+\n/g, "\n").replace(/[ \t]+/g, " ").trim();
    if (!limpio) {
      anunciar("No hay texto para leer.");
      return;
    }
    voz.cancel();
    const sesion = ++sesionLectura;
    const vozElegida = elegirVoz();
    const fragmentos = dividirTexto(limpio);

    fragmentos.forEach((fragmento, i) => {
      const enunciado = new SpeechSynthesisUtterance(fragmento);
      enunciado.lang = vozElegida?.lang || "es-CO";
      if (vozElegida) enunciado.voice = vozElegida;
      enunciado.rate = 1;
      if (i === fragmentos.length - 1) {
        enunciado.onend = enunciado.onerror = () => {
          if (sesion === sesionLectura) cambiarEstadoLectura(false);
        };
      }
      voz.speak(enunciado);
    });
    cambiarEstadoLectura(true);
  }

  function detener() {
    sesionLectura++;
    voz?.cancel();
    cambiarEstadoLectura(false);
  }

  function cambiarEstadoLectura(valor) {
    hablando = valor;
    actualizarBotones();
  }

  function alternarLectura() {
    if (hablando) {
      detener();
      return;
    }
    leer(textoDeLaPagina());
    seleccionPrevia = "";
  }

  /** Permite que una página diga qué leer (ej. el mapa lee el lugar seleccionado). */
  function definirLectura(funcion) {
    proveedorLectura = typeof funcion === "function" ? funcion : null;
  }

  // ---------------- Enlazar eventos ----------------
  function enlazar() {
    buscarBotones();
    crearRegiones();
    voz?.getVoices(); // Chrome carga las voces de forma asíncrona: se piden desde ya

    botones.voz.forEach((b) => {
      // Guardar la selección antes de que el clic la borre
      b.addEventListener("pointerdown", () => {
        seleccionPrevia = window.getSelection()?.toString().trim() || "";
      });
      b.addEventListener("click", alternarLectura);
    });
    botones.contraste.forEach((b) => b.addEventListener("click", alternarContraste));
    botones.zoom.forEach((b) => b.addEventListener("click", ampliarTexto));

    // Escape detiene la lectura
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && hablando) detener();
    });

    actualizarBotones();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enlazar, { once: true });
  } else {
    enlazar();
  }

  // No seguir hablando al cambiar de página
  window.addEventListener("pagehide", () => voz?.cancel());
  // Sincronizar si el usuario cambia la preferencia en otra pestaña
  window.addEventListener("storage", (e) => {
    if (e.key === CLAVE) {
      prefs = cargarPreferencias();
      aplicarPreferencias();
    }
  });

  window.Accesibilidad = {
    leer,
    detener,
    alternarLectura,
    alternarContraste,
    ampliarTexto,
    restablecer,
    anunciar,
    definirLectura,
    get estado() {
      return {
        contraste: Boolean(prefs.contraste),
        tamanoTexto: NIVELES_TEXTO[prefs.nivelTexto] ?? 100,
        hablando,
        vozDisponible: Boolean(voz),
      };
    },
  };
})();
