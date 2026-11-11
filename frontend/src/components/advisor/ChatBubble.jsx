import React from 'react';
import { Bot, User, Sparkles } from 'lucide-react';
import { Badge } from '../common/Badge';
import { resolveAdvisorProvider } from '../../utils/advisorProvider';

/**
 * Safely parse inline markdown tokens (**bold**, *italic*, `code`) into pure React elements.
 * Never uses dangerouslySetInnerHTML.
 */
const parseInlineTokens = (text, keyPrefix = 'inline') => {
  if (!text) return null;

  // Split on bold, italic, or inline code tokens
  const tokenRegex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    if (!part) return null;

    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return (
        <strong key={key} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return (
        <em key={key} className="italic text-slate-700">
          {part.slice(1, -1)}
        </em>
      );
    }

    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code key={key} className="px-1.5 py-0.5 mx-0.5 rounded bg-slate-100 text-slate-800 font-mono text-xs">
          {part.slice(1, -1)}
        </code>
      );
    }

    return part;
  });
};

/**
 * Safely parse multiline markdown structure (headings, bullet points, sub-lists, paragraphs)
 * into native React elements.
 */
const renderSafeMarkdown = (content) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let currentList = [];
  let listKeyIndex = 0;

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${listKeyIndex++}`} className="list-disc pl-5 my-2 space-y-1 text-slate-700 text-sm">
          {currentList.map((item, idx) => (
            <li key={`li-${idx}`} className="leading-relaxed">
              {item}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      return;
    }

    // Check headings
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={`h4-${index}`} className="text-sm font-bold text-slate-900 mt-3 mb-1 tracking-tight">
          {parseInlineTokens(trimmed.slice(4), `h4-in-${index}`)}
        </h4>
      );
      return;
    }

    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={`h3-${index}`} className="text-base font-bold text-slate-900 mt-3.5 mb-1.5 tracking-tight">
          {parseInlineTokens(trimmed.slice(3), `h3-in-${index}`)}
        </h3>
      );
      return;
    }

    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={`h2-${index}`} className="text-lg font-bold text-slate-900 mt-4 mb-2 tracking-tight">
          {parseInlineTokens(trimmed.slice(2), `h2-in-${index}`)}
        </h2>
      );
      return;
    }

    // Check sub-bullets (starts with indentation like "  * " or "    - ")
    if (line.startsWith('  * ') || line.startsWith('  - ') || line.startsWith('    * ') || line.startsWith('    - ')) {
      const subContent = line.replace(/^\s+[*|-]\s+/, '');
      currentList.push(
        <div key={`sub-${index}`} className="pl-4 text-xs text-slate-600 mt-0.5">
          {parseInlineTokens(subContent, `sub-in-${index}`)}
        </div>
      );
      return;
    }

    // Check primary bullet point
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const itemContent = trimmed.slice(2);
      currentList.push(parseInlineTokens(itemContent, `li-in-${index}`));
      return;
    }

    // Regular paragraph line
    flushList();
    elements.push(
      <p key={`p-${index}`} className="text-sm text-slate-700 leading-relaxed my-1.5">
        {parseInlineTokens(trimmed, `p-in-${index}`)}
      </p>
    );
  });

  flushList();
  return elements;
};

export const ChatBubble = ({ message, isLatest = false }) => {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 mb-4">
        <div className="max-w-xl bg-brand-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm text-sm leading-relaxed">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center shrink-0 shadow-xs">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  // Model response
  const provider = resolveAdvisorProvider(message);

  return (
    <div className="flex justify-start gap-3 mb-5">
      <div className="w-8 h-8 rounded-full bg-purple-100 text-purple-700 border border-purple-200 flex items-center justify-center shrink-0 shadow-xs">
        <Bot className="w-4 h-4" />
      </div>

      <div className="max-w-2xl flex-1 bg-white border border-slate-200/80 rounded-2xl rounded-tl-sm p-4 sm:p-5 shadow-xs">
        {/* Model header tag */}
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
            <Sparkles className="w-3.5 h-3.5 text-purple-600" />
            <span>FinAdvisor Copilot</span>
          </div>

          <Badge
            variant={provider.isGemini ? 'primary' : 'default'}
            size="sm"
            className="text-[10px]"
          >
            {provider.label}
          </Badge>
        </div>

        {/* Formatted body */}
        <div className="space-y-1">
          {renderSafeMarkdown(message.content || message.reply)}
        </div>
      </div>
    </div>
  );
};

export default ChatBubble;
