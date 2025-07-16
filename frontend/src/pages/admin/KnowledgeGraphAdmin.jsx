import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Paper,
  Breadcrumbs,
  Link
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  BugReport as BugReportIcon,
  Assessment as AssessmentIcon,
  Settings as SettingsIcon,
  Home as HomeIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import EntityQualityDashboard from '../../components/admin/EntityQualityDashboard';
import EntityCorrectionDetails from '../../components/admin/EntityCorrectionDetails';

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const KnowledgeGraphAdmin = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const navigate = useNavigate();

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const tabs = [
    {
      label: 'Dashboard',
      icon: <DashboardIcon />,
      component: <EntityQualityDashboard />
    },
    {
      label: 'Control de Calidad',
      icon: <BugReportIcon />,
      component: <EntityQualityDashboard />
    },
    {
      label: 'Estadísticas Avanzadas',
      icon: <AssessmentIcon />,
      component: (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            Estadísticas avanzadas próximamente...
          </Typography>
        </Box>
      )
    },
    {
      label: 'Configuración',
      icon: <SettingsIcon />,
      component: (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            Configuración del grafo próximamente...
          </Typography>
        </Box>
      )
    }
  ];

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link
          color="inherit"
          href="#"
          onClick={() => navigate('/dashboard')}
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
        >
          <HomeIcon fontSize="small" />
          Dashboard
        </Link>
        <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <SettingsIcon fontSize="small" />
          Administración del Grafo de Conocimiento
        </Typography>
      </Breadcrumbs>

      {/* Título Principal */}
      <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', mb: 4 }}>
        🧠 Administración del Grafo de Conocimiento
      </Typography>

      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 4 }}>
        Herramientas avanzadas para gestionar, revisar y optimizar la calidad de las entidades y relaciones 
        en el grafo de conocimiento. Mantén tu base de conocimiento limpia y precisa.
      </Typography>

      {/* Tabs de Navegación */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              minHeight: 72,
              textTransform: 'none',
              fontSize: '1rem',
              fontWeight: 500
            }
          }}
        >
          {tabs.map((tab, index) => (
            <Tab
              key={index}
              icon={tab.icon}
              label={tab.label}
              iconPosition="start"
              sx={{
                '& .MuiTab-iconWrapper': {
                  marginBottom: '0 !important',
                  marginRight: 1
                }
              }}
            />
          ))}
        </Tabs>

        {/* Contenido de las Tabs */}
        {tabs.map((tab, index) => (
          <TabPanel key={index} value={currentTab} index={index}>
            {tab.component}
          </TabPanel>
        ))}
      </Paper>

      {/* Información Adicional */}
      <Paper sx={{ p: 3, mt: 4, bgcolor: 'background.default' }}>
        <Typography variant="h6" gutterBottom>
          💡 Consejos para el Control de Calidad
        </Typography>
        <Box component="ul" sx={{ pl: 2, '& li': { mb: 1 } }}>
          <li>
            <Typography variant="body2">
              <strong>Ejecuta revisiones regulares:</strong> Realiza controles de calidad después de procesar nuevos documentos.
            </Typography>
          </li>
          <li>
            <Typography variant="body2">
              <strong>Revisa antes de aplicar:</strong> Siempre revisa las correcciones sugeridas antes de aplicarlas automáticamente.
            </Typography>
          </li>
          <li>
            <Typography variant="body2">
              <strong>Monitorea las estadísticas:</strong> Una puntuación de calidad superior al 85% indica un grafo saludable.
            </Typography>
          </li>
          <li>
            <Typography variant="body2">
              <strong>Fusiona duplicados:</strong> Las entidades duplicadas pueden afectar la precisión de las consultas.
            </Typography>
          </li>
          <li>
            <Typography variant="body2">
              <strong>Elimina entidades inválidas:</strong> Artículos, preposiciones y palabras comunes no aportan valor semántico.
            </Typography>
          </li>
        </Box>
      </Paper>
    </Container>
  );
};

export default KnowledgeGraphAdmin;
