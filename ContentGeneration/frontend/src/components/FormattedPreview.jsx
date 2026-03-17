import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Platform-aware formatted preview component.
 *
 * Renders content with platform-specific styling:
 * - WhatsApp: *bold*, _italic_, ~strikethrough~, ```code```, green bubble
 * - Telegram: Markdown with bold, italic, code, links
 * - LinkedIn: Clean professional paragraphs, hashtag highlighting
 * - Twitter/X: Thread view with tweet cards, character count
 * - Generic: Full Markdown rendering via react-markdown
 */

// ── WhatsApp preview ─────────────────────────────────────────────
function WhatsAppPreview({ content }) {
  const formatWaText = (text) => {
    // Bold *text*
    let formatted = text.replace(/\*([^*]+)\*/g, '<strong>$1</strong>')
    // Italic _text_
    formatted = formatted.replace(/(?<!\w)_([^_]+)_(?!\w)/g, '<em>$1</em>')
    // Strikethrough ~text~
    formatted = formatted.replace(/~([^~]+)~/g, '<del>$1</del>')
    // Monospace ```text```
    formatted = formatted.replace(/```([^`]+)```/g, '<code class="bg-emerald-100 px-1 py-0.5 rounded text-[13px] font-mono">$1</code>')
    // Inline code `text`
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="bg-emerald-100 px-1 py-0.5 rounded text-[13px] font-mono">$1</code>')
    return formatted
  }

  const blocks = content.split(/\n{2,}/).filter(Boolean)

  return (
    <div className="space-y-2">
      {blocks.map((block, i) => (
        <div
          key={i}
          className="rounded-xl bg-[#dcf8c6] px-4 py-2.5 text-[14px] leading-relaxed text-slate-800 shadow-sm max-w-[90%]"
          style={{ fontFamily: "'Segoe UI', system-ui, sans-serif" }}
        >
          {block.split('\n').map((line, j) => (
            <p
              key={j}
              className={j > 0 ? 'mt-1' : ''}
              dangerouslySetInnerHTML={{ __html: formatWaText(line) }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

// ── Telegram preview ─────────────────────────────────────────────
function TelegramPreview({ content }) {
  return (
    <div className="rounded-xl bg-[#1a1a2e] p-4 text-[14px] leading-relaxed text-slate-200 shadow-sm">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="text-lg font-bold text-white mb-2" {...p} />,
          h2: (p) => <h2 className="text-base font-bold text-white mb-2" {...p} />,
          h3: (p) => <h3 className="text-sm font-bold text-white mb-1.5" {...p} />,
          p: (p) => <p className="mb-2 text-slate-200" {...p} />,
          strong: (p) => <strong className="font-bold text-white" {...p} />,
          em: (p) => <em className="italic text-blue-300" {...p} />,
          code: ({ inline, ...p }) => inline
            ? <code className="bg-slate-700 text-green-300 px-1 py-0.5 rounded text-[13px] font-mono" {...p} />
            : <code className="block bg-slate-800 text-green-300 p-3 rounded-lg text-[13px] font-mono mt-2 mb-2 overflow-x-auto" {...p} />,
          a: (p) => <a className="text-blue-400 underline" target="_blank" rel="noopener noreferrer" {...p} />,
          ul: (p) => <ul className="list-disc list-inside mb-2 space-y-0.5" {...p} />,
          ol: (p) => <ol className="list-decimal list-inside mb-2 space-y-0.5" {...p} />,
          li: (p) => <li className="text-slate-200" {...p} />,
          blockquote: (p) => <blockquote className="border-l-2 border-blue-500 pl-3 italic text-slate-300 mb-2" {...p} />,
          hr: () => <hr className="border-slate-600 my-3" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

// ── LinkedIn preview ─────────────────────────────────────────────
function LinkedInPreview({ content }) {
  const highlightHashtags = (text) => {
    return text.replace(/#(\w+)/g, '<span class="text-blue-600 font-semibold">#$1</span>')
  }

  const blocks = content.split(/\n{2,}/).filter(Boolean)

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="space-y-3">
        {blocks.map((block, i) => {
          if (block.startsWith('#') && !block.startsWith('##')) {
            const heading = block.replace(/^#+\s*/, '')
            return <h3 key={i} className="text-base font-bold text-slate-900">{heading}</h3>
          }
          if (block === '---') {
            return <hr key={i} className="border-slate-100" />
          }
          return (
            <div key={i}>
              {block.split('\n').map((line, j) => (
                <p
                  key={j}
                  className={`text-[14px] leading-relaxed text-slate-700 ${j > 0 ? 'mt-1' : ''}`}
                  dangerouslySetInnerHTML={{ __html: highlightHashtags(line) }}
                />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Twitter/X thread preview ─────────────────────────────────────
function TwitterPreview({ content }) {
  // Split tweets by horizontal rule or triple dash
  const tweets = content.split(/\n-{3,}\n|\n={3,}\n/).map(t => t.trim()).filter(Boolean)

  return (
    <div className="space-y-3">
      {tweets.map((tweet, i) => {
        const charCount = tweet.length
        const isOverLimit = charCount > 280
        return (
          <div
            key={i}
            className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-600 flex items-center justify-center text-white text-xs font-bold">
                {i + 1}
              </div>
              <div className="text-xs text-slate-400 font-semibold">Tweet {i + 1}/{tweets.length}</div>
            </div>
            <p className="text-[14px] leading-relaxed text-slate-800 whitespace-pre-wrap">{tweet}</p>
            <div className="mt-2 flex items-center justify-between">
              <span className={`text-[11px] font-mono ${isOverLimit ? 'text-rose-500 font-bold' : 'text-slate-400'}`}>
                {charCount}/280
              </span>
              {isOverLimit && (
                <span className="text-[10px] text-rose-500 font-semibold">⚠ Over character limit</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Generic Markdown preview ─────────────────────────────────────
function GenericPreview({ content }) {
  return (
    <div className="prose prose-sm prose-slate max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="text-lg font-bold text-slate-900 mb-2 mt-4" {...p} />,
          h2: (p) => <h2 className="text-base font-bold text-slate-900 mb-2 mt-3" {...p} />,
          h3: (p) => <h3 className="text-sm font-bold text-slate-800 mb-1.5 mt-2" {...p} />,
          p: (p) => <p className="mb-2 text-slate-700 leading-relaxed text-[14px]" {...p} />,
          strong: (p) => <strong className="font-bold text-slate-900" {...p} />,
          em: (p) => <em className="italic" {...p} />,
          code: ({ inline, ...p }) => inline
            ? <code className="bg-slate-100 text-indigo-600 px-1.5 py-0.5 rounded text-[13px] font-mono" {...p} />
            : <code className="block bg-slate-50 border border-slate-100 p-3 rounded-lg text-[13px] font-mono mt-2 mb-2 overflow-x-auto" {...p} />,
          a: (p) => <a className="text-indigo-600 underline" target="_blank" rel="noopener noreferrer" {...p} />,
          ul: (p) => <ul className="list-disc list-inside mb-2 space-y-0.5 text-[14px]" {...p} />,
          ol: (p) => <ol className="list-decimal list-inside mb-2 space-y-0.5 text-[14px]" {...p} />,
          li: (p) => <li className="text-slate-700" {...p} />,
          blockquote: (p) => <blockquote className="border-l-2 border-indigo-300 pl-3 italic text-slate-500 mb-2" {...p} />,
          hr: () => <hr className="border-slate-200 my-3" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

// ── Main FormattedPreview component ──────────────────────────────
export function FormattedPreview({ content, platform }) {
  if (!content) {
    return <p className="text-sm text-slate-400 italic">No content yet.</p>
  }

  const PLATFORM_LABELS = {
    whatsapp: { label: 'WhatsApp Preview', color: 'bg-emerald-100 text-emerald-700' },
    telegram: { label: 'Telegram Preview', color: 'bg-blue-100 text-blue-700' },
    linkedin: { label: 'LinkedIn Preview', color: 'bg-sky-100 text-sky-700' },
    twitter: { label: 'Twitter/X Preview', color: 'bg-slate-100 text-slate-700' },
  }
  const meta = PLATFORM_LABELS[platform] || { label: 'Preview', color: 'bg-indigo-100 text-indigo-700' }

  return (
    <div>
      <span className={`inline-block mb-3 rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${meta.color}`}>
        {meta.label}
      </span>
      {platform === 'whatsapp' && <WhatsAppPreview content={content} />}
      {platform === 'telegram' && <TelegramPreview content={content} />}
      {platform === 'linkedin' && <LinkedInPreview content={content} />}
      {platform === 'twitter' && <TwitterPreview content={content} />}
      {!['whatsapp', 'telegram', 'linkedin', 'twitter'].includes(platform) && <GenericPreview content={content} />}
    </div>
  )
}
