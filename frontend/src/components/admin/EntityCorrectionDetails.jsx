import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  Checkbox,
  IconButton,
  Tooltip,
  Collapse,
  Alert,
  Grid
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  AutoFixHigh as AutoFixHighIcon,
  Delete as DeleteIcon,
  Merge as MergeIcon,
  Visibility as VisibilityIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';

const EntityCorrectionDetails = ({ 
  corrections = [], 
  deletions = [], 
  merges = [], 
  onApplySelected,
  loading = false 
}) => {
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [expandedSections, setExpandedSections] = useState({
    corrections: true,
    deletions: false,
    merges: false
  });

  const allItems = [
    ...corrections.map(item => ({ ...item, category: 'corrections' })),
    ...deletions.map(item => ({ ...item, category: 'deletions' })),
    ...merges.map(item => ({ ...item, category: 'merges' }))
  ];

  const handleSelectAll = (category) => {
    const categoryItems = allItems.filter(item => item.category === category);
    const newSelected = new Set(selectedItems);
    
    const allCategorySelected = categoryItems.every(item => 
      selectedItems.has(`${item.category}-${item.entity?.id || item.entities?.[0]?.id}`)
    );

    if (allCategorySelected) {
      // Deseleccionar todos de esta categoría
      categoryItems.forEach(item => {
        newSelected.delete(`${item.category}-${item.entity?.id || item.entities?.[0]?.id}`);
      });
    } else {
      // Seleccionar todos de esta categoría
      categoryItems.forEach(item => {
        newSelected.add(`${item.category}-${item.entity?.id || item.entities?.[0]?.id}`);
      });
    }
    
    setSelectedItems(newSelected);
  };

  const handleSelectItem = (item) => {
    const itemId = `${item.category}-${item.entity?.id || item.entities?.[0]?.id}`;
    const newSelected = new Set(selectedItems);
    
    if (selectedItems.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    
    setSelectedItems(newSelected);
  };

  const getSelectedCorrections = () => {
    return allItems.filter(item => 
      selectedItems.has(`${item.category}-${item.entity?.id || item.entities?.[0]?.id}`)
    );
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'correct': return <AutoFixHighIcon color="warning" />;
      case 'delete': return <DeleteIcon color="error" />;
      case 'merge': return <MergeIcon color="info" />;
      default: return null;
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

  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'error';
      default: return 'default';
    }
  };

  const renderCorrectionTable = (items, category, title) => {
    if (items.length === 0) return null;

    const isExpanded = expandedSections[category];
    const categoryItems = items.map(item => ({ ...item, category }));
    const selectedCount = categoryItems.filter(item => 
      selectedItems.has(`${category}-${item.entity?.id || item.entities?.[0]?.id}`)
    ).length;

    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6">
                {title} ({items.length})
              </Typography>
              {selectedCount > 0 && (
                <Chip 
                  label={`${selectedCount} seleccionados`} 
                  size="small" 
                  color="primary" 
                />
              )}
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Button
                size="small"
                onClick={() => handleSelectAll(category)}
                startIcon={selectedCount === items.length ? <CancelIcon /> : <CheckCircleIcon />}
              >
                {selectedCount === items.length ? 'Deseleccionar Todo' : 'Seleccionar Todo'}
              </Button>
              <IconButton onClick={() => toggleSection(category)}>
                {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
          </Box>

          <Collapse in={isExpanded}>
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">Seleccionar</TableCell>
                    <TableCell>Entidad</TableCell>
                    <TableCell>Tipo Actual</TableCell>
                    {category === 'corrections' && <TableCell>Tipo Sugerido</TableCell>}
                    {category === 'merges' && <TableCell>Entidades a Fusionar</TableCell>}
                    <TableCell>Razón</TableCell>
                    <TableCell>Confianza</TableCell>
                    <TableCell>Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {categoryItems.map((item, index) => {
                    const itemId = `${category}-${item.entity?.id || item.entities?.[0]?.id}`;
                    const isSelected = selectedItems.has(itemId);
                    
                    return (
                      <TableRow key={index} selected={isSelected}>
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={isSelected}
                            onChange={() => handleSelectItem(item)}
                          />
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getActionIcon(item.action)}
                            <Typography variant="body2" fontWeight="medium">
                              {item.entity?.name || item.entities?.[0]?.name || 'Desconocido'}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={item.entity?.type || item.entities?.[0]?.type || 'N/A'} 
                            size="small" 
                            variant="outlined" 
                          />
                        </TableCell>
                        {category === 'corrections' && (
                          <TableCell>
                            <Chip 
                              label={item.suggested_type} 
                              size="small" 
                              color={getActionColor(item.action)}
                            />
                          </TableCell>
                        )}
                        {category === 'merges' && (
                          <TableCell>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                              {item.entities?.slice(1).map((entity, idx) => (
                                <Chip 
                                  key={idx}
                                  label={entity.name} 
                                  size="small" 
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </TableCell>
                        )}
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {item.reason}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip 
                            label={item.confidence || 'medium'} 
                            size="small" 
                            color={getConfidenceColor(item.confidence)}
                          />
                        </TableCell>
                        <TableCell>
                          <Tooltip title="Ver detalles">
                            <IconButton size="small">
                              <VisibilityIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Collapse>
        </CardContent>
      </Card>
    );
  };

  return (
    <Box>
      {/* Resumen de Selección */}
      {selectedItems.size > 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography>
              {selectedItems.size} elementos seleccionados para corrección
            </Typography>
            <Button
              variant="contained"
              startIcon={<AutoFixHighIcon />}
              onClick={() => onApplySelected(getSelectedCorrections())}
              disabled={loading || selectedItems.size === 0}
            >
              {loading ? 'Aplicando...' : 'Aplicar Seleccionados'}
            </Button>
          </Box>
        </Alert>
      )}

      {/* Estadísticas Rápidas */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <AutoFixHighIcon color="warning" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">{corrections.length}</Typography>
              <Typography variant="body2" color="text.secondary">
                Correcciones de Tipo
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <DeleteIcon color="error" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">{deletions.length}</Typography>
              <Typography variant="body2" color="text.secondary">
                Eliminaciones
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <MergeIcon color="info" sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h6">{merges.length}</Typography>
              <Typography variant="body2" color="text.secondary">
                Fusiones
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tablas de Correcciones */}
      {renderCorrectionTable(corrections, 'corrections', 'Correcciones de Tipo')}
      {renderCorrectionTable(deletions, 'deletions', 'Eliminaciones')}
      {renderCorrectionTable(merges, 'merges', 'Fusiones')}

      {/* Mensaje si no hay correcciones */}
      {corrections.length === 0 && deletions.length === 0 && merges.length === 0 && (
        <Alert severity="success">
          <Typography variant="h6">¡Excelente!</Typography>
          <Typography>No se encontraron problemas de calidad en las entidades.</Typography>
        </Alert>
      )}
    </Box>
  );
};

export default EntityCorrectionDetails;
