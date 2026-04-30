// src/components/chat/MixedContentRenderer.tsx
import React, { useState, useEffect, useRef } from 'react';
import { View, StyleSheet, Text, Platform } from 'react-native';
import Markdown from 'react-native-markdown-display';
import { WebView } from 'react-native-webview';
import { MessageContentPart } from '../../api/chatService';
import { ReasoningBlock } from './ReasoningBlock';
import { ToolCallBlock } from './ToolCallBlock';

interface Props {
  content?: string;
  contentParts?: MessageContentPart[];
  isDarkMode: boolean;
  theme: any;
  markdownStyles: any;
}

// Helper to detect if a snippet contains significant HTML
const isHtmlBlock = (text: string) => {
  const trimmed = text.trim();
  if (!trimmed.startsWith('<')) return false;
  
  const htmlIndicators = [
    '<!doctype', '<html', '<div', '<table', '<style', 
    '<script', '<body', '<svg', '<section', '<article', 
    '<pre', '<form', '<canvas', '<iframe'
  ];
  
  const lower = trimmed.toLowerCase();
  return htmlIndicators.some(indicator => lower.startsWith(indicator)) || 
         (lower.includes('<style>') && lower.includes('</style>'));
};

const InlineHtmlMessage = ({ html, isDark, theme }: { html: string; isDark: boolean; theme: any }) => {
  const [height, setHeight] = useState(100);
  const webViewRef = useRef<WebView>(null);
  
  const fg = isDark ? '#ececec' : '#111827';
  const bg = isDark ? '#1f2937' : '#f9fafb';
  const accent = theme.primary || '#3b82f6';
  const border = isDark ? '#374151' : '#e5e7eb';

  // Injected JS to monitor height changes and report back
  const injectedJs = `
    (function() {
      var height = 0;
      function updateHeight() {
        var newHeight = document.body.scrollHeight;
        if (Math.abs(height - newHeight) > 2) {
          height = newHeight;
          window.ReactNativeWebView.postMessage(String(height));
        }
      }
      
      // Initial update
      updateHeight();
      
      // Observer for content changes (ideal for streaming)
      var observer = new MutationObserver(function() {
        updateHeight();
      });
      observer.observe(document.body, { 
        attributes: true, 
        childList: true, 
        characterData: true, 
        subtree: true 
      });
      
      // Event listener for images/resources
      window.addEventListener('load', updateHeight);
      window.addEventListener('resize', updateHeight);
    })();
    true;
  `;

  const webViewHtml = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          html, body { 
            background: transparent; 
            color: ${fg}; 
            font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            font-size: 15px; 
            line-height: 1.6; 
            overflow: hidden;
          }
          .container { padding: 4px 2px; }
          h1, h2, h3 { margin: 16px 0 8px; color: ${accent}; font-weight: 800; letter-spacing: -0.025em; }
          h1 { font-size: 1.5rem; }
          h2 { font-size: 1.25rem; }
          h3 { font-size: 1.1rem; }
          
          table { width: 100%; border-collapse: separate; border-spacing: 0; margin: 16px 0; font-size: 13px; border-radius: 8px; overflow: hidden; border: 1px solid ${border}; }
          th { background: ${isDark ? '#374151' : '#f3f4f6'}; font-weight: 700; padding: 12px 10px; text-align: left; }
          td { padding: 10px; border-top: 1px solid ${border}; }
          
          .card { 
            background: ${bg}; 
            border-radius: 12px; 
            padding: 16px; 
            margin: 12px 0; 
            border: 1px solid ${border};
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          }
          pre, code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: ${isDark ? '#111827' : '#f1f5f9'}; border-radius: 6px; }
          code { padding: 2px 4px; font-size: 0.9em; color: ${accent}; }
          pre { padding: 12px; margin: 12px 0; overflow-x: auto; font-size: 0.85em; }
          pre code { padding: 0; background: transparent; color: inherit; }
          
          ul, ol { padding-left: 20px; margin: 12px 0; }
          li { margin-bottom: 4px; }
          
          blockquote { border-left: 4px solid ${accent}; padding-left: 16px; margin: 16px 0; font-style: italic; color: ${isDark ? '#9ca3af' : '#4b5563'}; }
          hr { border: 0; border-top: 1px solid ${border}; margin: 20px 0; }
        </style>
      </head>
      <body><div class="container">${html}</div></body>
    </html>
  `;

  return (
    <View style={{ height: height, width: '100%', marginVertical: 4, overflow: 'hidden' }}>
      <WebView
        ref={webViewRef}
        originWhitelist={['*']}
        source={{ html: webViewHtml }}
        scrollEnabled={false}
        onMessage={e => {
          const h = parseInt(e.nativeEvent.data, 10);
          if (!isNaN(h) && h > 0) {
            setHeight(h + 10); // Added small buffer
          }
        }}
        injectedJavaScript={injectedJs}
        style={{ backgroundColor: 'transparent' }}
        javaScriptEnabled={true}
        domStorageEnabled={true}
      />
    </View>
  );
};

export const MixedContentRenderer: React.FC<Props> = ({ content, contentParts, isDarkMode, theme, markdownStyles }) => {
  
  const renderPart = (part: MessageContentPart, index: number) => {
    switch (part.type) {
      case 'reasoning':
        return <ReasoningBlock key={index} content={part.content} isDarkMode={isDarkMode} theme={theme} markdownStyles={markdownStyles} />;
      case 'tool_call':
        return <ToolCallBlock key={index} part={part} isDarkMode={isDarkMode} theme={theme} />;
      case 'text':
        return renderTextWithHtml(part.content, index);
      default:
        return null;
    }
  };

  const renderTextWithHtml = (text: string, baseKey: number | string) => {
    if (!text) return null;
    
    // Split text by common HTML block-level tags but keep them in the array
    const parts = text.split(/(?=<html|<div|<table|<style|<svg|<body|<section|<article|<pre|<form|<canvas|<iframe)/gi);
    
    return parts.map((part, pIdx) => {
      const key = `${baseKey}-${pIdx}`;
      if (isHtmlBlock(part)) {
        return <InlineHtmlMessage key={key} html={part} isDark={isDarkMode} theme={theme} />;
      }
      
      if (!part.trim()) return null;

      return (
        <View key={key} style={styles.markdownPart}>
          {/* @ts-ignore */}
          <Markdown style={markdownStyles}>
            {part}
          </Markdown>
        </View>
      );
    });
  };

  if (contentParts && contentParts.length > 0) {
    return (
      <View style={styles.container}>
        {contentParts.map((part, index) => renderPart(part, index))}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {renderTextWithHtml(content || '', 'fallback')}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { width: '100%' },
  markdownPart: { width: '100%' }
});
