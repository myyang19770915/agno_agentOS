import { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Tooltip,
  Typography,
  Alert,
} from '@mui/material';
import TableChartIcon from '@mui/icons-material/TableChart';
import ViewListIcon from '@mui/icons-material/ViewList';
import KeyIcon from '@mui/icons-material/Key';
import RefreshIcon from '@mui/icons-material/Refresh';
import { fetchTables, fetchTableSchema, fetchTableRows } from '../api';

export default function DatabasePage() {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [schema, setSchema] = useState(null);
  const [rows, setRows] = useState([]);
  const [rowsTotal, setRowsTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [rowsLoading, setRowsLoading] = useState(false);

  const loadTables = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTables();
      setTables(data.tables || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTables(); }, [loadTables]);

  const selectTable = useCallback(async (table) => {
    setSelected(table);
    setPage(0);
    try {
      const [schemaData, rowsData] = await Promise.all([
        fetchTableSchema(table.table_name, table.table_schema),
        fetchTableRows(table.table_name, {
          schema: table.table_schema,
          limit: rowsPerPage,
          offset: 0,
        }),
      ]);
      setSchema(schemaData);
      setRows(rowsData.rows || []);
      setRowsTotal(rowsData.total || 0);
    } catch {
      setSchema(null);
      setRows([]);
    }
  }, [rowsPerPage]);

  const loadRows = useCallback(async (newPage, newLimit) => {
    if (!selected) return;
    setRowsLoading(true);
    try {
      const data = await fetchTableRows(selected.table_name, {
        schema: selected.table_schema,
        limit: newLimit,
        offset: newPage * newLimit,
      });
      setRows(data.rows || []);
      setRowsTotal(data.total || 0);
    } catch { /* ignore */ }
    setRowsLoading(false);
  }, [selected]);

  const handlePageChange = (_, newPage) => {
    setPage(newPage);
    loadRows(newPage, rowsPerPage);
  };

  const handleRowsPerPageChange = (e) => {
    const rpp = parseInt(e.target.value, 10);
    setRowsPerPage(rpp);
    setPage(0);
    loadRows(0, rpp);
  };

  const columns = schema?.columns || [];
  const columnNames = rows.length > 0 ? Object.keys(rows[0]) : columns.map(c => c.column_name);
  const pkColumns = new Set(columns.filter(c => c.is_primary_key).map(c => c.column_name));

  return (
    <Box sx={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Table list sidebar */}
      <Paper
        sx={{
          width: 280,
          minWidth: 280,
          overflow: 'auto',
          borderRight: 1,
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="subtitle1" fontWeight={700}>
            Tables
          </Typography>
          <Tooltip title="重新整理">
            <IconButton size="small" onClick={loadTables}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Divider />
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress size={28} />
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ m: 1 }}>{error}</Alert>
        ) : (
          <List dense sx={{ flex: 1, overflow: 'auto' }}>
            {tables.map((t) => (
              <ListItemButton
                key={`${t.table_schema}.${t.table_name}`}
                selected={selected?.table_name === t.table_name && selected?.table_schema === t.table_schema}
                onClick={() => selectTable(t)}
                sx={{ borderRadius: 1, mx: 0.5, mb: 0.3 }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {t.table_type === 'VIEW' ? <ViewListIcon fontSize="small" /> : <TableChartIcon fontSize="small" />}
                </ListItemIcon>
                <ListItemText
                  primary={t.table_name}
                  secondary={t.table_schema}
                  primaryTypographyProps={{ fontSize: 13, fontWeight: 600 }}
                  secondaryTypographyProps={{ fontSize: 11 }}
                />
                {t.table_type === 'VIEW' && (
                  <Chip label="VIEW" size="small" variant="outlined" sx={{ height: 20, fontSize: 10 }} />
                )}
              </ListItemButton>
            ))}
          </List>
        )}
      </Paper>

      {/* Right panel: schema + data */}
      <Box sx={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {!selected ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, opacity: 0.5 }}>
            <Typography variant="h6">← 請選擇一個 Table</Typography>
          </Box>
        ) : (
          <>
            {/* Schema card */}
            <Card sx={{ m: 2, mb: 1 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {selected.table_schema}.{selected.table_name}
                  {selected.table_type === 'VIEW' && (
                    <Chip label="VIEW" size="small" sx={{ ml: 1 }} />
                  )}
                </Typography>
                {columns.length > 0 && (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.8, mt: 1 }}>
                    {columns.map((col) => (
                      <Chip
                        key={col.column_name}
                        icon={pkColumns.has(col.column_name) ? <KeyIcon fontSize="small" /> : undefined}
                        label={`${col.column_name} (${col.data_type})`}
                        size="small"
                        color={pkColumns.has(col.column_name) ? 'primary' : 'default'}
                        variant="outlined"
                      />
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>

            {/* Data table */}
            <Box sx={{ flex: 1, mx: 2, mb: 2, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <TableContainer component={Paper} sx={{ flex: 1, overflow: 'auto' }}>
                {rowsLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress size={28} />
                  </Box>
                ) : (
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        {columnNames.map((col) => (
                          <TableCell
                            key={col}
                            sx={{
                              fontWeight: 700,
                              fontSize: 12,
                              backgroundColor: 'background.paper',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {pkColumns.has(col) && <KeyIcon sx={{ fontSize: 14, mr: 0.5, verticalAlign: 'text-bottom' }} />}
                            {col}
                          </TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {rows.map((row, idx) => (
                        <TableRow key={idx} hover>
                          {columnNames.map((col) => (
                            <TableCell key={col} sx={{ fontSize: 12, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {row[col] == null ? <span style={{ opacity: 0.3 }}>NULL</span> : String(row[col])}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                      {rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={columnNames.length || 1} align="center" sx={{ py: 4, opacity: 0.5 }}>
                            無資料
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                )}
              </TableContainer>
              <TablePagination
                component="div"
                count={rowsTotal}
                page={page}
                onPageChange={handlePageChange}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={handleRowsPerPageChange}
                rowsPerPageOptions={[10, 25, 50, 100]}
                labelRowsPerPage="每頁筆數"
                sx={{ borderTop: 1, borderColor: 'divider', flexShrink: 0 }}
              />
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}
