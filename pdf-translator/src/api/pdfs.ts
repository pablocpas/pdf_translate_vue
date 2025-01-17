import { z } from 'zod';
import type { UploadResponse, TranslationTask } from '@/types';
import apiClient from './client';
import { ApiRequestError } from '@/types/api';

const uploadResponseSchema = z.object({
  taskId: z.string().min(1)
});

const translationProgressSchema = z.object({
  current: z.number(),
  total: z.number(),
  percent: z.number()
});

const translationTaskSchema = z.object({
  id: z.string().min(1),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  originalFile: z.string().min(1),
  translatedFile: z.string().optional(),
  error: z.string().optional(),
  progress: translationProgressSchema.optional()
});

export async function uploadPdf(formData: FormData): Promise<UploadResponse> {
  try {
    const response = await apiClient.post<UploadResponse>('/pdfs/translate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    const validatedData = uploadResponseSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new ApiRequestError(
        'Respuesta del servidor inválida',
        500,
        { message: error.message }
      );
    }
    throw error;
  }
}

export async function getTranslationStatus(taskId: string): Promise<TranslationTask> {
  try {
    const response = await apiClient.get<TranslationTask>(`/pdfs/status/${taskId}`);
    const validatedData = translationTaskSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new ApiRequestError(
        'Respuesta del servidor inválida',
        500,
        { message: error.message }
      );
    }
    throw error;
  }
}

export async function downloadTranslatedPdf(taskId: string): Promise<Blob> {
  const response = await apiClient.get(`/pdfs/download/${taskId}`, {
    responseType: 'blob',
  });
  
  if (!(response.data instanceof Blob)) {
    throw new ApiRequestError(
      'Respuesta del servidor inválida: se esperaba un archivo PDF',
      500
    );
  }
  
  return response.data;
}
