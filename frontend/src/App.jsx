import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import KnowledgeGraphAdmin from './pages/admin/KnowledgeGraphAdmin';

// Tema personalizado
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderRadius: 12,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
          <Routes>
            {/* Ruta principal - redirigir al grafo de conocimiento */}
            <Route path="/" element={<Navigate to="/knowledge-graph" replace />} />
            
            {/* Página principal del grafo de conocimiento */}
            <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
            
            {/* Panel de administración del grafo */}
            <Route path="/admin/knowledge-graph" element={<KnowledgeGraphAdmin />} />
            
            {/* Ruta de fallback */}
            <Route path="*" element={<Navigate to="/knowledge-graph" replace />} />
          </Routes>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;
