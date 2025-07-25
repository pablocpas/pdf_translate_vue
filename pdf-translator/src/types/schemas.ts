import { z } from 'zod';

// 1. NUEVO: Enum para los pasos de procesamiento que envía el backend.
// Esto hace tu código más robusto.
export const processingStepSchema = z.enum([
  'En cola',
  'Convirtiendo PDF a imágenes',
  'Procesando páginas en paralelo',
  'Ensamblando PDF final',
  'Desconocido',
]);

// 2. MODIFICADO: El esquema de progreso ahora refleja la nueva estructura.
export const translationProgressSchema = z.object({
  step: processingStepSchema, // Usa el nuevo enum
  details: z.any().optional().nullable(), // 'details' puede ser cualquier cosa (texto, objeto, etc.) o no existir.
});

// 3. MODIFICADO: El esquema de la tarea ahora usa el nuevo esquema de progreso.
// También ajusto el enum de 'status' para que use mayúsculas, como lo envía el backend.
export const translationTaskSchema = z.object({
  id: z.string().min(1, 'ID is required'),
  status: z.enum(['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED']), // MAYÚSCULAS
  originalFile: z.string(),
  translatedFile: z.string().optional().nullable(),
  error: z.string().optional().nullable(),
  progress: translationProgressSchema.optional().nullable(), // Usa el nuevo esquema de progreso
});

// 4. NUEVO: Esquema para la respuesta completa de /translation-data/{id}
// Esto te permite validar toda la respuesta de una vez y obtener los datos de posición.
const positionSchema = z.object({
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
  // coordinates: z.object({ x1: z.number(), y1: z.number(), x2: z.number(), y2: z.number() }) // Descomenta si necesitas las coordenadas en píxeles
});

const regionSchema = z.object({
  id: z.number(),
  position: positionSchema,
});

const pagePositionSchema = z.object({
  page_number: z.number(),
  dimensions: z.object({ width: z.number(), height: z.number() }),
  regions: z.array(regionSchema),
});

const positionsDataSchema = z.object({
  pages: z.array(pagePositionSchema),
  // images: z.any().optional() // Descomenta si vas a usar los datos de las imágenes
});

export const translationAndPositionDataSchema = z.object({
  pages: z.array(z.object({
    page_number: z.number(),
    translations: z.array(z.object({
      id: z.number(),
      original_text: z.string(),
      translated_text: z.string()
    }))
  })),
  positions: positionsDataSchema
});


// --- Esquemas sin cambios ---

// Upload response schema
export const uploadResponseSchema = z.object({
  taskId: z.string().min(1),
});

// Translation text schema (usado para el editor)
export const translationTextSchema = z.object({
  id: z.number(),
  original_text: z.string(),
  translated_text: z.string(),
});

// Page translation schema (usado para el editor)
export const pageTranslationSchema = z.object({
  page_number: z.number(),
  translations: z.array(translationTextSchema),
});

// Translation data schema (usado para el editor, para enviar en el PUT)
export const translationDataSchema = z.object({
  pages: z.array(pageTranslationSchema),
});


// --- Exportación de Tipos para TypeScript ---

export type TranslationProgress = z.infer<typeof translationProgressSchema>;
export type TranslationTask = z.infer<typeof translationTaskSchema>;
export type UploadResponse = z.infer<typeof uploadResponseSchema>;
export type TranslationText = z.infer<typeof translationTextSchema>;
export type PageTranslation = z.infer<typeof pageTranslationSchema>;
export type TranslationData = z.infer<typeof translationDataSchema>;
export type TranslationAndPositionData = z.infer<typeof translationAndPositionDataSchema>;