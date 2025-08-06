'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Wand2, Delete, Merge, CheckCircle, XCircle, Eye } from 'lucide-react';

interface CorrectionItem {
  action: string;
  entity?: { id: string; name: string; type: string; };
  entities?: { id: string; name: string; type: string; }[];
  reason: string;
  suggested_type?: string;
  confidence?: 'high' | 'medium' | 'low';
  category: 'corrections' | 'deletions' | 'merges';
}

interface EntityCorrectionDetailsProps {
  corrections: any[];
  deletions: any[];
  merges: any[];
  onApplySelected: (selected: CorrectionItem[]) => void;
  loading: boolean;
}

const EntityCorrectionDetails = ({
  corrections = [],
  deletions = [],
  merges = [],
  onApplySelected,
  loading = false
}: EntityCorrectionDetailsProps) => {
  const [selectedItems, setSelectedItems] = useState(new Set());

  const allItems = [
    ...corrections.map(item => ({ ...item, category: 'corrections' })),
    ...deletions.map(item => ({ ...item, category: 'deletions' })),
    ...merges.map(item => ({ ...item, category: 'merges' }))
  ];

  const handleSelectAll = (category: string, items: any[]) => {
    const categoryItems = items.map((item: any) => `${category}-${item.entity?.id || item.entities?.[0]?.id}`);
    const newSelected = new Set(selectedItems);
    const allSelected = categoryItems.every((id: string) => newSelected.has(id));

    if (allSelected) {
      categoryItems.forEach((id: string) => newSelected.delete(id));
    } else {
      categoryItems.forEach((id: string) => newSelected.add(id));
    }
    setSelectedItems(newSelected);
  };

  const handleSelectItem = (item: CorrectionItem) => {
    const itemId = `${item.category}-${item.entity?.id || item.entities?.[0]?.id}`;
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const getSelectedCorrections = () => {
    return allItems.filter((item: CorrectionItem) =>
      selectedItems.has(`${item.category}-${item.entity?.id || item.entities?.[0]?.id}`)
    );
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'correct': return <Wand2 className="h-4 w-4 text-yellow-500" />;
      case 'delete': return <Delete className="h-4 w-4 text-red-500" />;
      case 'merge': return <Merge className="h-4 w-4 text-blue-500" />;
      default: return null;
    }
  };

  const getConfidenceVariant = (confidence: string | undefined) => {
    switch (confidence) {
      case 'high': return 'default';
      case 'medium': return 'default';
      case 'low': return 'destructive';
      default: return 'secondary';
    }
  };

  const renderCorrectionTable = (items: any[], category: string, title: string) => {
    if (items.length === 0) return null;

    const categoryItems: CorrectionItem[] = items.map((item: any) => ({ ...item, category } as CorrectionItem));
    const selectedCount = categoryItems.filter((item: CorrectionItem) =>
      selectedItems.has(`${category}-${item.entity?.id || item.entities?.[0]?.id}`)
    ).length;

    return (
      <AccordionItem value={category}>
        <AccordionTrigger>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold">{title} ({items.length})</h3>
            {selectedCount > 0 && <Badge>{selectedCount} seleccionados</Badge>}
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <div className="flex justify-end mb-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleSelectAll(category, items)}
            >
              {selectedCount === items.length ? <XCircle className="mr-2 h-4 w-4" /> : <CheckCircle className="mr-2 h-4 w-4" />}
              {selectedCount === items.length ? 'Deseleccionar Todo' : 'Seleccionar Todo'}
            </Button>
          </div>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50px]">Sel.</TableHead>
                  <TableHead>Entidad</TableHead>
                  <TableHead>Tipo Actual</TableHead>
                  {category === 'corrections' && <TableHead>Tipo Sugerido</TableHead>}
                  {category === 'merges' && <TableHead>Fusionar</TableHead>}
                  <TableHead>Razón</TableHead>
                  <TableHead>Confianza</TableHead>
                  <TableHead>Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {categoryItems.map((item: CorrectionItem, index: number) => {
                  const itemId = `${category}-${item.entity?.id || item.entities?.[0]?.id}`;
                  const isSelected = selectedItems.has(itemId);
                  
                  return (
                    <TableRow key={index} data-state={isSelected ? 'selected' : ''}>
                      <TableCell>
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => handleSelectItem(item)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 font-medium">
                          {getActionIcon(item.action)}
                          {item.entity?.name || item.entities?.[0]?.name || 'Desconocido'}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{item.entity?.type || item.entities?.[0]?.type || 'N/A'}</Badge>
                      </TableCell>
                      {category === 'corrections' && (
                        <TableCell>
                          <Badge variant="default">{item.suggested_type}</Badge>
                        </TableCell>
                      )}
                      {category === 'merges' && (
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {item.entities?.slice(1).map((entity: any, idx: number) => (
                              <Badge key={idx} variant="secondary">{entity.name}</Badge>
                            ))}
                          </div>
                        </TableCell>
                      )}
                      <TableCell className="text-sm text-muted-foreground">{item.reason}</TableCell>
                      <TableCell>
                        <Badge variant={getConfidenceVariant(item.confidence)}>{item.confidence || 'medium'}</Badge>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </AccordionContent>
      </AccordionItem>
    );
  };

  return (
    <div className="space-y-6">
      {selectedItems.size > 0 && (
        <Alert>
          <Wand2 className="h-4 w-4" />
          <AlertTitle>Aplicar Cambios</AlertTitle>
          <AlertDescription className="flex justify-between items-center">
            <span>{selectedItems.size} elementos seleccionados para corrección.</span>
            <Button
              onClick={() => onApplySelected(getSelectedCorrections())}
              disabled={loading || selectedItems.size === 0}
            >
              {loading ? 'Aplicando...' : 'Aplicar Seleccionados'}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Correcciones de Tipo</CardTitle>
            <Wand2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{corrections.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Eliminaciones</CardTitle>
            <Delete className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{deletions.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fusiones</CardTitle>
            <Merge className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{merges.length}</div>
          </CardContent>
        </Card>
      </div>

      <Accordion type="multiple" defaultValue={['corrections', 'deletions', 'merges']}>
        {renderCorrectionTable(corrections, 'corrections', 'Correcciones de Tipo')}
        {renderCorrectionTable(deletions, 'deletions', 'Eliminaciones Sugeridas')}
        {renderCorrectionTable(merges, 'merges', 'Fusiones Sugeridas')}
      </Accordion>

      {corrections.length === 0 && deletions.length === 0 && merges.length === 0 && (
        <Alert variant="default">
          <CheckCircle className="h-4 w-4" />
          <AlertTitle>¡Excelente!</AlertTitle>
          <AlertDescription>No se encontraron problemas de calidad en las entidades.</AlertDescription>
        </Alert>
      )}
    </div>
  );
};

export default EntityCorrectionDetails;