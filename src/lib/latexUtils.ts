import katex from 'katex';

/**
 * Mapa de comandos LaTeX comunes a sus equivalentes Unicode.
 */
const LATEX_SYMBOL_MAP: Record<string, string> = {
  // Flechas
  leftrightarrow: '↔',
  longleftrightarrow: '↔',
  Leftrightarrow: '⇔',
  Longleftrightarrow: '⇔',
  iff: '⇔',
  rightarrow: '→',
  longrightarrow: '→',
  to: '→',
  Rightarrow: '⇒',
  Longrightarrow: '⇒',
  implies: '⇒',
  leftarrow: '←',
  longleftarrow: '←',
  gets: '←',
  Leftarrow: '⇐',
  Longleftarrow: '⇐',
  impliedby: '⇐',
  uparrow: '↑',
  Uparrow: '⇑',
  downarrow: '↓',
  Downarrow: '⇓',
  updownarrow: '↕',
  Updownarrow: '⇕',
  mapsto: '↦',
  hookleftarrow: '↩',
  hookrightarrow: '↪',
  nearrow: '↗',
  searrow: '↘',
  swarrow: '↙',
  nwarrow: '↖',

  // Operadores y relaciones
  times: '×',
  div: '÷',
  pm: '±',
  mp: '∓',
  cdot: '·',
  bullet: '•',
  ast: '∗',
  star: '⋆',
  approx: '≈',
  neq: '≠',
  ne: '≠',
  leq: '≤',
  le: '≤',
  geq: '≥',
  ge: '≥',
  equiv: '≡',
  sim: '∼',
  simeq: '≃',
  cong: '≅',
  propto: '∝',
  ll: '≪',
  gg: '≫',

  // Conjuntos y lógica
  infty: '∞',
  in: '∈',
  notin: '∉',
  ni: '∋',
  subset: '⊂',
  subseteq: '⊆',
  supset: '⊃',
  supseteq: '⊇',
  cup: '∪',
  cap: '∩',
  emptyset: '∅',
  varnothing: '∅',
  forall: '∀',
  exists: '∃',
  nexists: '∄',
  neg: '¬',
  lnot: '¬',
  land: '∧',
  lor: '∨',
  oplus: '⊕',
  otimes: '⊗',
  perp: '⊥',
  parallel: '∥',
  angle: '∠',
  therefore: '∴',
  because: '∵',

  // Cálculo y varios
  partial: '∂',
  nabla: '∇',
  sum: '∑',
  prod: '∏',
  int: '∫',
  checkmark: '✓',
  ldots: '…',
  cdots: '⋯',
  dots: '…',

  // Letras griegas comunes
  alpha: 'α',
  beta: 'β',
  gamma: 'γ',
  delta: 'δ',
  epsilon: 'ε',
  varepsilon: 'ε',
  zeta: 'ζ',
  eta: 'η',
  theta: 'θ',
  vartheta: 'ϑ',
  iota: 'ι',
  kappa: 'κ',
  lambda: 'λ',
  mu: 'μ',
  nu: 'ν',
  xi: 'ξ',
  pi: 'π',
  rho: 'ρ',
  sigma: 'σ',
  tau: 'τ',
  upsilon: 'υ',
  phi: 'φ',
  varphi: 'ϕ',
  chi: 'χ',
  psi: 'ψ',
  omega: 'ω',
  Gamma: 'Γ',
  Delta: 'Δ',
  Theta: 'Θ',
  Lambda: 'Λ',
  Xi: 'Ξ',
  Pi: 'Π',
  Sigma: 'Σ',
  Upsilon: 'Υ',
  Phi: 'Φ',
  Psi: 'Ψ',
  Omega: 'Ω',
};

/**
 * Comandos de flechas/símbolos que a veces el LLM escribe sueltos sin delimitadores `$`
 * (ej. `\leftrightarrow` o `\rightarrow`).
 */
const BARE_LATEX_ARROWS_REGEX =
  /\\(longleftrightarrow|leftrightarrow|Longleftrightarrow|Leftrightarrow|longrightarrow|rightarrow|Longrightarrow|Rightarrow|longleftarrow|leftarrow|Longleftarrow|Leftarrow|updownarrow|Updownarrow|uparrow|downarrow|mapsto|implies|impliedby|iff|approx|neq|leq|geq|times|pm|infty)\b/g;

/**
 * Protege bloques de código (```...``` y `...`) reemplazándolos temporalmente por tokens.
 */
function protectCodeSegments(text: string): {
  protectedText: string;
  restoreCode: (input: string) => string;
} {
  const codeSegments: string[] = [];
  const protectedText = text.replace(/```[\s\S]*?```|`[^`\n]+`/g, (match) => {
    const idx = codeSegments.length;
    codeSegments.push(match);
    return `@@KOGNITO_CODE_${idx}@@`;
  });

  const restoreCode = (input: string): string =>
    input.replace(/@@KOGNITO_CODE_(\d+)@@/g, (_, idx) => codeSegments[Number(idx)] ?? '');

  return { protectedText, restoreCode };
}

/**
 * Convierte símbolos LaTeX simples (como `$\leftrightarrow$` o `\leftrightarrow`)
 * a sus caracteres Unicode nativos, respetando bloques de código.
 */
export function normalizeLatexSymbols(text: string): string {
  if (!text || (!text.includes('$') && !text.includes('\\'))) {
    return text;
  }

  const { protectedText, restoreCode } = protectCodeSegments(text);

  // 1. Reemplazar `$\comando$` o `\(\comando\)` cuando contienen un único símbolo conocido
  let normalized = protectedText.replace(
    /(?:\$\s*\\([a-zA-Z]+)\s*\$|\\\(\s*\\([a-zA-Z]+)\s*\\\))/g,
    (fullMatch, cmd1, cmd2) => {
      const cmd = cmd1 || cmd2;
      return LATEX_SYMBOL_MAP[cmd] ?? fullMatch;
    }
  );

  // 2. Reemplazar flechas/símbolos LaTeX sueltos fuera de expresiones matemáticas complejas
  //    (solo cuando no forman parte de otro comando ni están pegados a `{` o `_` o `^`)
  normalized = normalized.replace(BARE_LATEX_ARROWS_REGEX, (fullMatch, cmd) => {
    return LATEX_SYMBOL_MAP[cmd] ?? fullMatch;
  });

  return restoreCode(normalized);
}

/**
 * Determina si el contenido dentro de `$ ... $` parece realmente una expresión matemática LaTeX
 * y no cantidades monetarias (ej. "$100 y $200").
 */
function isLikelyInlineMath(expr: string): boolean {
  const trimmed = expr.trim();
  if (!trimmed) return false;

  // Si empieza con dígito y es solo número/moneda (ej. "100", "1,000.50 USD"), no es LaTeX
  if (/^\d+([.,]\d+)*(\s*[a-zA-Z%]+)?$/.test(trimmed)) {
    return false;
  }

  // Si contiene comandos LaTeX (\...), superíndices (^), subíndices (_), llaves ({}) o símbolos matemáticos
  if (/[\\^_{}=<>±×÷≈≠≤≥∞∑∏∫√]/.test(trimmed)) {
    return true;
  }

  // Expresiones algebraicas cortas como $x$, $n+1$, $a/b$, $f(x)$
  if (/^[a-zA-Z0-9+\-*/(),.\s]+$/.test(trimmed) && trimmed.length <= 40 && /[a-zA-Z]/.test(trimmed)) {
    return true;
  }

  return false;
}

/**
 * Preprocesa un texto Markdown para:
 * 1. Normalizar símbolos LaTeX simples (`$\leftrightarrow$` -> `↔`).
 * 2. Extraer y renderizar fórmulas LaTeX (`$$...$$`, `\[...\]`, `\(...\)`, `$...$`) con KaTeX,
 *    devolviendo el texto con placeholders seguros para `marked.parse` y una función para restaurar el HTML de KaTeX.
 */
export function extractAndRenderMath(text: string): {
  processedText: string;
  restoreMathHtml: (html: string) => string;
} {
  if (!text || (!text.includes('$') && !text.includes('\\'))) {
    return {
      processedText: text,
      restoreMathHtml: (html: string) => html,
    };
  }

  const { protectedText, restoreCode } = protectCodeSegments(text);
  const mathHtmlSegments: string[] = [];

  const pushMathPlaceholder = (latex: string, displayMode: boolean): string => {
    try {
      const rendered = katex.renderToString(latex.trim(), {
        displayMode,
        throwOnError: false,
        output: 'html',
      });
      const idx = mathHtmlSegments.length;
      mathHtmlSegments.push(rendered);
      return `@@KOGNITO_MATH_${idx}@@`;
    } catch {
      return latex;
    }
  };

  // Primero reemplazamos símbolos simples como `$\leftrightarrow$` por Unicode directo
  let working = protectedText.replace(
    /(?:\$\s*\\([a-zA-Z]+)\s*\$|\\\(\s*\\([a-zA-Z]+)\s*\\\))/g,
    (fullMatch, cmd1, cmd2) => {
      const cmd = cmd1 || cmd2;
      return LATEX_SYMBOL_MAP[cmd] ?? fullMatch;
    }
  );

  // 1. Bloques matemáticos: $$ ... $$ y \[ ... \]
  working = working.replace(/\$\$([\s\S]+?)\$\$/g, (_, expr) =>
    pushMathPlaceholder(expr, true)
  );
  working = working.replace(/\\\[([\s\S]+?)\\\]/g, (_, expr) =>
    pushMathPlaceholder(expr, true)
  );

  // 2. Matemáticas en línea con \( ... \)
  working = working.replace(/\\\(([\s\S]+?)\\\)/g, (_, expr) =>
    pushMathPlaceholder(expr, false)
  );

  // 3. Matemáticas en línea con $ ... $ (evitando $$ y precios)
  working = working.replace(/(?<!\\|\$)\$(?!\$|\s)([^$\n]+?)(?<!\s|\$)\$(?!\$)/g, (fullMatch, expr) => {
    if (!isLikelyInlineMath(expr)) {
      return fullMatch;
    }
    return pushMathPlaceholder(expr, false);
  });

  // 4. Flechas/símbolos LaTeX sueltos que hayan quedado fuera de delimitadores `$`
  working = working.replace(BARE_LATEX_ARROWS_REGEX, (fullMatch, cmd) => {
    return LATEX_SYMBOL_MAP[cmd] ?? fullMatch;
  });

  const processedText = restoreCode(working);

  const restoreMathHtml = (html: string): string =>
    html.replace(/@@KOGNITO_MATH_(\d+)@@/g, (_, idx) => mathHtmlSegments[Number(idx)] ?? '');

  return { processedText, restoreMathHtml };
}
