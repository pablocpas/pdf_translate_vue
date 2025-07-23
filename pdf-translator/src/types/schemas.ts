import { z } from 'zod';

// Progress schema shared between API and store
export const translationProgressSchema = z.object({
  current: z.number(),
  total: z.number(),
  percent: z.number()
});

// Task schema shared between API and store
export const translationTaskSchema = z.object({
  id: z.string().min(1, 'ID is required'),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  originalFile: z.string(),
  translatedFile: z.string().optional().nullable(),
  error: z.string().optional().nullable(),
  progress: translationProgressSchema.optional().nullable()
});

// Upload response schema
export const uploadResponseSchema = z.object({
  taskId: z.string().min(1)
});

// Translation text schema
export const translationTextSchema = z.object({
  id: z.number(),
  original_text: z.string(),
  translated_text: z.string()
});

// Page translation schema
export const pageTranslationSchema = z.object({
  page_number: z.number(),
  translations: z.array(translationTextSchema)
});

// Translation data schema
export const translationDataSchema = z.object({
  pages: z.array(pageTranslationSchema)
});

// Type exports for TypeScript
export type TranslationProgress = z.infer<typeof translationProgressSchema>;
export type TranslationTask = z.infer<typeof translationTaskSchema>;
export type UploadResponse = z.infer<typeof uploadResponseSchema>;
export type TranslationText = z.infer<typeof translationTextSchema>;
export type PageTranslation = z.infer<typeof pageTranslationSchema>;
export type TranslationData = z.infer<typeof translationDataSchema>;