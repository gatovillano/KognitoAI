import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Tooltip,
  CircularProgress
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  BugReport as BugReportIcon,
  AutoFixHigh as AutoFixHighIcon,
  Delete as DeleteIcon,
  Merge as MergeIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { apiRequest } from '../../utils/api';

const EntityQualityDashboard = () => {
  const [statistics, setStatistics] = useState(null);
  const [reviewResults, setReviewResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [applyLoading, setApplyLoading] = useState(false);
  const [selectedCorrections, setSelectedCorrections] = useState([]);
  const [showCorrectionDialog, setShowCorrectionDialog] = useState(false);
  const [correctionResults, setCorrectionResults] = useState(null);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    setLoading(true);
    try {
      const response = await apiRequest('/api/knowledge-graph/entity-statistics', 'GET');
      if (response.success) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('Error loading statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  const runQualityReview = async () => {
    setReviewLoading(true);
    try {
      const response = await apiRequest('/api/knowledge-graph/review-entities', 'POST', {});
      if (response.success) {
        setReviewResults(response.data);
      }
    } catch (error) {
      console.error('Error running quality review:', error);
    } finally {
      setReviewLoading(false);
    }
  };

  const applyCorrections = async (corrections, autoApply = false) => {
    setApplyLoading(true);
    try {
      const response = await apiRequest('/api/knowledge-graph/apply-corrections', 'POST', {
        corrections,
        auto_apply: autoApply
      });
      if (response.success) {
        setCorrectionResults(response.data);
        // Recargar estadísticas después de aplicar correcciones
        await loadStatistics();
        // Limpiar resultados de revisión para forzar nueva revisión
        setReviewResults(null);
      }
    } catch (error) {
      console.error('Error applying corrections:', error);
    } finally {
      setApplyLoading(false);
    }
  };

  const getQualityColor = (score) => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'warning';
    return 'error';
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'correct': return <AutoFixHighIcon color="warning" />;
      case 'delete': return <DeleteIcon color="error" />;
      case 'merge': return <MergeIcon color="info" />;
      default: return <InfoIcon />;
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'correct': return 'warning';
      case 'delete': return 'error';
      case 'merge': return 'info';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <BugReportIcon />
        Control de Calidad de Entidades
      </Typography>

      {/* Estadísticas Generales */}
      {statistics && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Entidades
                </Typography>
                <Typography variant="h4">
                  {statistics.summary.total_entities.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Relaciones
                </Typography>
                <Typography variant="h4">
                  {statistics.summary.total_relationships.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Tipos de Entidades
                </Typography>
                <Typography variant="h4">
                  {statistics.summary.entity_types_count}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Tipos de Relaciones
                </Typography>
                <Typography variant="h4">
                  {statistics.summary.relationship_types_count}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Botones de Acción */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={loadStatistics}
          disabled={loading}
        >
          Actualizar Estadísticas
        </Button>
        <Button
          variant="contained"
          color="warning"
          startIcon={<AssessmentIcon />}
          onClick={runQualityReview}
          disabled={reviewLoading}
        >
          {reviewLoading ? 'Analizando...' : 'Ejecutar Revisión de Calidad'}
        </Button>
      </Box>

      {/* Resultados de Revisión */}
      {reviewResults && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AssessmentIcon />
              Resultados de Revisión de Calidad
            </Typography>

            {/* Puntuación de Calidad */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                Puntuación de Calidad: {reviewResults.summary.quality_score.toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={reviewResults.summary.quality_score}
                color={getQualityColor(reviewResults.summary.quality_score)}
                sx={{ height: 10, borderRadius: 5 }}
              />
            </Box>

            {/* Resumen de Problemas */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={4}>
                <Alert severity="warning" sx={{ height: '100%' }}>
                  <Typography variant="h6">{reviewResults.summary.corrections_needed}</Typography>
                  <Typography variant="body2">Correcciones Necesarias</Typography>
                </Alert>
              </Grid>
              <Grid item xs={12} md={4}>
                <Alert severity="error" sx={{ height: '100%' }}>
                  <Typography variant="h6">{reviewResults.summary.deletions_needed}</Typography>
                  <Typography variant="body2">Eliminaciones Necesarias</Typography>
                </Alert>
              </Grid>
              <Grid item xs={12} md={4}>
                <Alert severity="info" sx={{ height: '100%' }}>
                  <Typography variant="h6">{reviewResults.summary.merges_needed}</Typography>
                  <Typography variant="body2">Fusiones Necesarias</Typography>
                </Alert>
              </Grid>
            </Grid>

            {/* Recomendaciones */}
            {reviewResults.summary.recommendations.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Recomendaciones:
                </Typography>
                <List dense>
                  {reviewResults.summary.recommendations.map((rec, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <InfoIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText primary={rec} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}

            {/* Botones de Acción para Correcciones */}
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                color="success"
                startIcon={<AutoFixHighIcon />}
                onClick={() => {
                  const allCorrections = [
                    ...reviewResults.corrections,
                    ...reviewResults.deletions,
                    ...reviewResults.merges
                  ];
                  setSelectedCorrections(allCorrections);
                  setShowCorrectionDialog(true);
                }}
                disabled={reviewResults.summary.issues_found === 0}
              >
                Aplicar Todas las Correcciones ({reviewResults.summary.issues_found})
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  setSelectedCorrections(reviewResults.corrections);
                  setShowCorrectionDialog(true);
                }}
                disabled={reviewResults.corrections.length === 0}
              >
                Solo Correcciones de Tipo ({reviewResults.corrections.length})
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Tabla de Entidades por Tipo */}
      {statistics && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Distribución de Entidades por Tipo
            </Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Tipo</TableCell>
                    <TableCell align="right">Cantidad</TableCell>
                    <TableCell align="right">Confianza Promedio</TableCell>
                    <TableCell>Métodos de Extracción</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {statistics.entity_types.map((type) => (
                    <TableRow key={type.type}>
                      <TableCell>
                        <Chip label={type.type} variant="outlined" />
                      </TableCell>
                      <TableCell align="right">
                        {type.count.toLocaleString()}
                      </TableCell>
                      <TableCell align="right">
                        {(type.avg_confidence * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell>
                        {type.methods.map((method, index) => (
                          <Chip
                            key={index}
                            label={method}
                            size="small"
                            sx={{ mr: 0.5, mb: 0.5 }}
                          />
                        ))}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Dialog de Confirmación de Correcciones */}
      <Dialog
        open={showCorrectionDialog}
        onClose={() => setShowCorrectionDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Confirmar Aplicación de Correcciones
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Se aplicarán {selectedCorrections.length} correcciones:
          </Typography>
          <List sx={{ maxHeight: 300, overflow: 'auto' }}>
            {selectedCorrections.slice(0, 10).map((correction, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  {getActionIcon(correction.action)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={correction.action.toUpperCase()}
                        size="small"
                        color={getActionColor(correction.action)}
                      />
                      <Typography variant="body2">
                        {correction.entity?.name || 'Entidad desconocida'}
                      </Typography>
                    </Box>
                  }
                  secondary={correction.reason}
                />
              </ListItem>
            ))}
            {selectedCorrections.length > 10 && (
              <ListItem>
                <ListItemText
                  primary={`... y ${selectedCorrections.length - 10} correcciones más`}
                />
              </ListItem>
            )}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCorrectionDialog(false)}>
            Cancelar
          </Button>
          <Button
            onClick={() => {
              applyCorrections(selectedCorrections, true);
              setShowCorrectionDialog(false);
            }}
            variant="contained"
            disabled={applyLoading}
          >
            {applyLoading ? 'Aplicando...' : 'Aplicar Correcciones'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Resultados de Corrección */}
      {correctionResults && (
        <Alert
          severity={correctionResults.failed === 0 ? 'success' : 'warning'}
          sx={{ mt: 2 }}
          onClose={() => setCorrectionResults(null)}
        >
          <Typography variant="subtitle1">
            Correcciones Aplicadas: {correctionResults.applied} exitosas, {correctionResults.failed} fallidas
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default EntityQualityDashboard;
