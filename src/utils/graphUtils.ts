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

    // Casos especiales
    if (type.toLowerCase() === 'desafío' || type.toLowerCase() === 'problem') return '#EF4444';
    if (type.toLowerCase() === 'solución' || type.toLowerCase() === 'solution') return '#22C55E';
    if (type.toLowerCase() === 'conceptual_quote') return '#3B82F6';

    const hash = type.split('').reduce((acc, char) =>
        char.charCodeAt(0) + ((acc << 5) - acc), 0);
    return NODE_COLOR_PALETTE[Math.abs(hash) % NODE_COLOR_PALETTE.length];
}
