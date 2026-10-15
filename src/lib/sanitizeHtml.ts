'use client';

import DOMPurify, { type Config } from 'isomorphic-dompurify';

const LINK_REL = 'noopener noreferrer nofollow';

const FEDIVERSE_SANITIZE_OPTIONS: Config = {
  USE_PROFILES: { html: true },
  ADD_ATTR: ['target', 'rel', 'class'],
};

const MARKDOWN_SANITIZE_OPTIONS: Config = {
  USE_PROFILES: { html: true },
  ADD_ATTR: [
    'target',
    'rel',
    'class',
    'style',
    'title',
    'alt',
    'data-language',
    'data-mermaid-code',
    'data-hydrated',
    'data-citation-number',
    'data-cmd',
    'data-session-id',
  ],
  ADD_TAGS: ['svg', 'path', 'polyline', 'line', 'circle', 'rect'],
  ALLOWED_URI_REGEXP:
    /^(?:(?:https?|mailto|data|blob):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i,
};

let linkHooksConfigured = false;

function configureLinkSafetyHooks(): void {
  if (linkHooksConfigured) {
    return;
  }

  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A') {
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', LINK_REL);
    }
  });

  linkHooksConfigured = true;
}

function sanitizeWithOptions(
  html: string | null | undefined,
  options: Config
): string {
  if (!html) {
    return '';
  }

  configureLinkSafetyHooks();
  return DOMPurify.sanitize(html, options) as string;
}

/**
 * Sanitiza HTML procedente del Fediverso/Mastodon antes de dangerouslySetInnerHTML.
 */
export function sanitizeFediverseHtml(html: string | null | undefined): string {
  return sanitizeWithOptions(html, FEDIVERSE_SANITIZE_OPTIONS);
}

/**
 * Sanitiza HTML generado por marked/LLM antes de dangerouslySetInnerHTML.
 */
export function sanitizeMarkdownHtml(html: string | null | undefined): string {
  return sanitizeWithOptions(html, MARKDOWN_SANITIZE_OPTIONS);
}
