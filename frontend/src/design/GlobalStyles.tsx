import { useEffect } from "react";
import { AMBER, SURFACE2, BORDER, TEXT_MID, TEXT_BODY, TEXT } from "./tokens";

const FONT_IMPORT = `@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap');`;

const css = `
  ${FONT_IMPORT}
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Syne', sans-serif; background: #080C14; color: #E8E4D9; overflow: hidden; }
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #2A3040; border-radius: 2px; }

  @keyframes fadeUp { from { opacity:0; transform:translateY(10px);} to { opacity:1; transform:translateY(0);} }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  @keyframes shimmer { 0%{background-position:-400px 0} 100%{background-position:400px 0} }
  @keyframes scanline { 0%{top:-4px} 100%{top:100%} }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
  @keyframes slideIn { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }
  @keyframes grow { from{width:0} to{width:100%} }

  .fade-up { animation: fadeUp .4s ease forwards; }
  .slide-in { animation: slideIn .3s ease forwards; }

  .scan-overlay {
    position:absolute; inset:0; pointer-events:none; overflow:hidden; border-radius:inherit;
  }
  .scan-overlay::after {
    content:''; position:absolute; left:0; width:100%; height:4px;
    background: linear-gradient(transparent, rgba(234,179,8,.15), transparent);
    animation: scanline 4s linear infinite;
  }
  .noise {
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.04'/%3E%3C/svg%3E");
  }

  /* react-markdown output styling */
  .md-content p { font-size: 12px; line-height: 1.7; color: ${TEXT_BODY}; margin-bottom: 6px; }
  .md-content p:last-child { margin-bottom: 0; }
  .md-content strong { color: ${TEXT}; font-weight: 700; }
  .md-content em { color: ${TEXT_MID}; font-style: italic; }
  .md-content h1, .md-content h2, .md-content h3 {
    color: ${TEXT}; font-size: 12px; font-weight: 700;
    margin-bottom: 4px; margin-top: 8px;
  }
  .md-content ul, .md-content ol {
    font-size: 12px; color: ${TEXT_BODY}; padding-left: 18px; margin-bottom: 6px; line-height: 1.7;
  }
  .md-content li { margin-bottom: 2px; }
  .md-content code {
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    background: ${SURFACE2}; border: 1px solid ${BORDER};
    padding: 1px 5px; border-radius: 3px; color: ${AMBER};
  }
  .md-content pre {
    background: ${SURFACE2}; border: 1px solid ${BORDER};
    border-radius: 6px; padding: 12px; margin-bottom: 8px; overflow-x: auto;
  }
  .md-content pre code { background: none; border: none; padding: 0; }
  .md-content table {
    width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 11px;
  }
  .md-content th {
    background: ${AMBER}15; color: ${AMBER}; font-weight: 600;
    font-family: 'Syne', sans-serif; padding: 5px 8px; text-align: left;
  }
  .md-content td {
    padding: 5px 8px; color: ${TEXT_MID};
    font-family: 'JetBrains Mono', monospace;
    border-bottom: 1px solid ${BORDER};
  }
  .md-content tr:nth-child(even) td { background: ${SURFACE2}88; }
  .md-content blockquote {
    border-left: 2px solid ${AMBER}44; padding-left: 12px;
    color: ${TEXT_MID}; font-style: italic; margin-bottom: 6px;
  }
  .md-content a { color: ${AMBER}; text-decoration: underline; }
  .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
`;

export default function GlobalStyles() {
  useEffect(() => {
    const tag = document.createElement("style");
    tag.textContent = css;
    document.head.appendChild(tag);
    return () => { document.head.removeChild(tag); };
  }, []);
  return null;
}
