import { z } from 'zod';
import type { UploadResponse, TranslationTask } from '@/types';
import apiClient from './client';
import { ApiRequestError, ErrorCode } from '@/types/api';

const uploadResponseSchema = z.object({
  taskId: z.string().min(1)
});

const translationProgressSchema = z.object({
  current: z.number(),
  total: z.number(),
  percent: z.number()
});

const translationTaskSchema = z.object({
  id: z.string().min(1, 'ID is required'),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  originalFile: z.string(),
  translatedFile: z.string().nullable(),
  error: z.string().nullable(),
  progress: translationProgressSchema.nullable()
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
        { 
          code: ErrorCode.VALIDATION_ERROR,
          message: error.message 
        }
      );
    }
    throw error;
  }
}

export async function getTranslationStatus(taskId: string): Promise<TranslationTask> {
  try {
    const response = await apiClient.get<TranslationTask>(`/pdfs/status/${taskId}`);
    console.log('Server response:', response.data);
    try {
      const validatedData = translationTaskSchema.parse(response.data);
      return validatedData;
    } catch (validationError) {
      if (validationError instanceof z.ZodError) {
        console.error('Validation error details:', validationError.errors);
      }
      throw validationError;
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new ApiRequestError(
        'Respuesta del servidor inválida',
        500,
        { 
          code: ErrorCode.VALIDATION_ERROR,
          message: error.message 
        }
      );
    }
    throw error;
  }
}

export async function downloadTranslatedPdf(taskId: string): Promise<Blob> {
  const response = await apiClient.get(`/pdfs/download/translated/${taskId}`, {
    responseType: 'blob',
  });
  
  if (!(response.data instanceof Blob)) {
    throw new ApiRequestError(
      'Respuesta del servidor inválida: se esperaba un archivo PDF',
      500,
      {
        code: ErrorCode.VALIDATION_ERROR,
        message: 'La respuesta no es un archivo PDF válido'
      }
    );
  }
  
  return response.data;
}
