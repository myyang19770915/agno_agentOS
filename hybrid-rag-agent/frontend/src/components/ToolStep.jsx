import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Collapse,
  IconButton,
  LinearProgress,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import BuildIcon from '@mui/icons-material/Build';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

function prettify(obj) {
  if (typeof obj === 'string') {
    try { obj = JSON.parse(obj); } catch { return obj; }
  }
  return JSON.stringify(obj, null, 2);
}

export default function ToolStep({ step }) {
  const [open, setOpen] = useState(false);

  const isCompleted = step.status === 'done';
  const isError = step.result?.error || step.result?.ok === false;

  return (
    <Card
      variant="outlined"
      sx={{
        my: 1,
        borderColor: isError ? 'error.main' : isCompleted ? 'success.dark' : 'primary.dark',
        borderLeftWidth: 3,
      }}
    >
      <CardContent sx={{ py: 1, px: 2, '&:last-child': { pb: 1 } }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isCompleted ? (
            isError ? <ErrorIcon color="error" fontSize="small" /> : <CheckCircleIcon color="success" fontSize="small" />
          ) : (
            <BuildIcon color="primary" fontSize="small" />
          )}
          <Chip
            label={step.tool_name}
            size="small"
            color="primary"
            variant="outlined"
            sx={{ fontFamily: 'monospace', fontWeight: 700 }}
          />
          {!isCompleted && <LinearProgress sx={{ flex: 1, ml: 1, borderRadius: 1, height: 4 }} />}
          {isCompleted && (
            <IconButton size="small" onClick={() => setOpen(!open)}>
              {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
            </IconButton>
          )}
        </Box>

        {/* Args summary */}
        {step.tool_args && (
          <Typography variant="caption" sx={{ display: 'block', mt: 0.5, opacity: 0.7, fontFamily: 'monospace' }}>
            {Object.entries(step.tool_args)
              .filter(([, v]) => v != null && v !== '')
              .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
              .join(' | ')}
          </Typography>
        )}

        {/* Collapsible result */}
        <Collapse in={open} timeout="auto">
          {step.result != null && (
            <Box
              component="pre"
              sx={{
                mt: 1,
                p: 1.5,
                borderRadius: 1,
                backgroundColor: 'rgba(0,0,0,0.3)',
                fontSize: 11,
                lineHeight: 1.5,
                overflow: 'auto',
                maxHeight: 300,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {prettify(step.result)}
            </Box>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
}
