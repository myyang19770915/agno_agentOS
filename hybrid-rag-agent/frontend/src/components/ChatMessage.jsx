import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Box, Paper, Typography, Avatar } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import ToolStep from './ToolStep';

/**
 * Custom MUI-based markdown components for rendering tables.
 * Handles: alignment, striped rows, header styling, responsive overflow,
 * single-column tables, empty cells, wide multi-column tables.
 */
const markdownComponents = {
  table: ({ children }) => (
    <Box
      sx={{
        overflowX: 'auto',
        my: 2,
        borderRadius: 1,
        border: '1px solid rgba(255,255,255,0.12)',
        '&::-webkit-scrollbar': { height: 6 },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'rgba(255,255,255,0.2)',
          borderRadius: 3,
        },
      }}
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          minWidth: 280,
          fontSize: 13,
          lineHeight: 1.6,
        }}
      >
        {children}
      </table>
    </Box>
  ),

  thead: ({ children }) => (
    <thead
      style={{
        backgroundColor: 'rgba(144, 202, 249, 0.12)',
      }}
    >
      {children}
    </thead>
  ),

  tbody: ({ children }) => <tbody>{children}</tbody>,

  tr: ({ children, ...props }) => {
    // Determine if this is inside tbody for striped rows
    // react-markdown passes `node` — we use isHeader to distinguish
    const isHeader = props.isHeader;
    return (
      <tr
        style={{
          backgroundColor: isHeader
            ? 'transparent'
            : undefined,
          transition: 'background-color 0.15s ease',
        }}
        onMouseEnter={(e) => {
          if (!isHeader) {
            e.currentTarget.style.backgroundColor = 'rgba(144, 202, 249, 0.08)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isHeader) {
            e.currentTarget.style.backgroundColor = '';
          }
        }}
      >
        {children}
      </tr>
    );
  },

  th: ({ children, style }) => (
    <th
      style={{
        padding: '10px 14px',
        fontWeight: 600,
        fontSize: 13,
        color: '#90caf9',
        borderBottom: '2px solid rgba(144, 202, 249, 0.3)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        textAlign: style?.textAlign || 'left',
        whiteSpace: 'nowrap',
        letterSpacing: '0.02em',
      }}
    >
      {children ?? ''}
    </th>
  ),

  td: ({ children, style }) => (
    <td
      style={{
        padding: '8px 14px',
        fontSize: 13,
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        borderRight: '1px solid rgba(255,255,255,0.04)',
        textAlign: style?.textAlign || 'left',
        color: 'rgba(255,255,255,0.85)',
        wordBreak: 'break-word',
      }}
    >
      {children ?? <span style={{ opacity: 0.3 }}>—</span>}
    </td>
  ),
};

export default function ChatMessage({ msg }) {
  const isUser = msg.role === 'user';

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1.5,
        mb: 2,
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
      }}
    >
      <Avatar
        sx={{
          width: 32,
          height: 32,
          bgcolor: isUser ? 'primary.main' : 'secondary.main',
        }}
      >
        {isUser ? <PersonIcon fontSize="small" /> : <SmartToyIcon fontSize="small" />}
      </Avatar>

      <Box sx={{ maxWidth: '80%', minWidth: 0 }}>
        {/* Tool steps */}
        {msg.toolSteps?.length > 0 && (
          <Box sx={{ mb: 1 }}>
            {msg.toolSteps.map((step) => (
              <ToolStep key={step.tool_call_id} step={step} />
            ))}
          </Box>
        )}

        {/* Text content */}
        {msg.content && (
          <Paper
            elevation={0}
            sx={{
              px: 2,
              py: 1.5,
              backgroundColor: isUser ? 'primary.dark' : 'background.paper',
              borderRadius: 2,
              /* Paragraph */
              '& p': { m: 0, mb: 1, '&:last-child': { mb: 0 } },
              /* Code blocks */
              '& pre': {
                backgroundColor: 'rgba(0,0,0,0.3)',
                borderRadius: 1,
                p: 1.5,
                overflow: 'auto',
                fontSize: 12,
              },
              '& code': {
                fontSize: 12,
                fontFamily: 'monospace',
              },
              /* Inline code */
              '& :not(pre) > code': {
                backgroundColor: 'rgba(255,255,255,0.08)',
                padding: '2px 6px',
                borderRadius: '4px',
              },
              /* Lists */
              '& ul, & ol': {
                pl: 3,
                my: 1,
              },
              '& li': {
                fontSize: 14,
                mb: 0.5,
              },
              /* Strikethrough (GFM) */
              '& del': {
                opacity: 0.6,
              },
              /* Task list (GFM) */
              '& input[type="checkbox"]': {
                mr: 1,
              },
              /* Blockquote */
              '& blockquote': {
                borderLeft: '3px solid rgba(144,202,249,0.4)',
                pl: 2,
                ml: 0,
                my: 1,
                opacity: 0.85,
              },
              /* Horizontal rule */
              '& hr': {
                border: 'none',
                borderTop: '1px solid rgba(255,255,255,0.12)',
                my: 2,
              },
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {msg.content}
            </ReactMarkdown>
          </Paper>
        )}

        {/* Typing indicator */}
        {msg.isStreaming && !msg.content && !msg.toolSteps?.length && (
          <Typography variant="body2" sx={{ opacity: 0.5 }}>
            思考中…
          </Typography>
        )}
      </Box>
    </Box>
  );
}
