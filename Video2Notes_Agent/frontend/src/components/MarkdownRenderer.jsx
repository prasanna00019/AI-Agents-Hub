import React from 'react';
import ReactMarkdown from 'react-markdown';

const MarkdownRenderer = ({ content, variant = 'default', compact = false }) => {
  const className = [
    'markdown-body',
    variant === 'print' ? 'markdown-body--print' : '',
    compact ? 'markdown-body--compact' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={className}>
      <ReactMarkdown
        components={{
          a: ({ href, children, ...props }) => (
            <a href={href} target="_blank" rel="noreferrer" {...props}>
              {children}
            </a>
          ),
        }}
      >
        {content || ''}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;