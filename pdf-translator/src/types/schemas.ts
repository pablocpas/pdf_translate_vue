import { z } from 'zod';

// Pasos de procesamiento del backend
export const processingStepSchema = z.enum([
  'Iniciando traducción',
  'Preparando documento',
  'Analizando páginas',
  'Traduciendo contenido',
  'Finalizando documento',
  'Procesando',
]);

// Esquema de progreso
export const translationProgressSchema = z.object({
  step: processingStepSchema, 
  details: z.any().optional().nullable(),
});

// Esquema de tarea de traducción
export const translationTaskSchema = z.object({
  id: z.string().min(1, 'ID is required'),
  status: z.enum(['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED']),
  originalFile: z.string(),
  translatedFile: z.string().optional().nullable(),
  error: z.string().optional().nullable(),
  progress: translationProgressSchema.optional().nullable(),
});

// Esquema para datos de posición
const positionSchema = z.object({
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
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


// Esquemas para editor

// Respuesta de subida
export const uploadResponseSchema = z.object({
  taskId: z.string().min(1),
});

// Texto de traducción
export const translationTextSchema = z.object({
  id: z.number(),
  original_text: z.string(),
  translated_text: z.string(),
});

// Traducción de página
export const pageTranslationSchema = z.object({
  page_number: z.number(),
  translations: z.array(translationTextSchema),
});

// Datos de traducción completos
export const translationDataSchema = z.object({
  pages: z.array(pageTranslationSchema),
});


// Tipos TypeScript

export type TranslationProgress = z.infer<typeof translationProgressSchema>;
export type TranslationTask = z.infer<typeof translationTaskSchema>;
export type UploadResponse = z.infer<typeof uploadResponseSchema>;
export type TranslationText = z.infer<typeof translationTextSchema>;
export type PageTranslation = z.infer<typeof pageTranslationSchema>;
export type TranslationData = z.infer<typeof translationDataSchema>;
export type TranslationAndPositionData = z.infer<typeof translationAndPositionDataSchema>;