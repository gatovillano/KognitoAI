// src/utils/graphUtils.ts

export const NODE_COLOR_PALETTE = [
    '#3B82F6', // blue-500
    '#EF4444', // red-500
    '#22C55E', // green-500
    '#F59E0B', // amber-500
    '#8B5CF6', // violet-500
    '#EC4899', // pink-500
    '#14B8A6', // teal-500
    '#F97316', // orange-500
    '#6366F1', // indigo-500
    '#84CC16', // lime-500
    '#06B6D4', // cyan-500
    '#A855F7', // purple-500
    '#D946EF', // fuchsia-500
    '#EAB308', // yellow-500
    '#64748B', // slate-500
];

export function getNodeColor(type: string): string {
    if (!type || type.toLowerCase() === 'desconocido') return '#9CA3AF'; // gray-400 for unknown or 'desconocido'

    const normalized = type.toLowerCase();

    // Casos especiales con color único
    if (normalized === 'desafío' || normalized === 'problem') return '#EF4444';
    if (normalized === 'solución' || normalized === 'solution') return '#22C55E';
    if (normalized === 'conceptual_quote') return '#E74C3C';
    if (normalized === 'document') return '#64748B'; // slate-500

    // Tipos antropológicos con colores diferenciados
    if (normalized === 'anthropological_quote') return '#F59E0B'; // amber
    if (normalized === 'anthropological_code') return '#10B981'; // emerald
    if (normalized === 'anthropological_category') return '#06B6D4'; // cyan

    const hash = type.split('').reduce((acc, char) =>
        char.charCodeAt(0) + ((acc << 5) - acc), 0);
    return NODE_COLOR_PALETTE[Math.abs(hash) % NODE_COLOR_PALETTE.length];
}
