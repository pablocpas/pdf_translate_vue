import { z } from 'zod';
import type { UploadResponse, TranslationTask, TranslationData } from '@/types';
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
    const response = await apiClient.post<any>('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    // Backend returns a TranslationTask object, we need to map it to UploadResponse
    const uploadResponse = { taskId: response.data.id };
    const validatedData = uploadResponseSchema.parse(uploadResponse);
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
    const response = await apiClient.get<any>(`/api/translation/${taskId}/status`);
    console.log('Server response:', response.data);
    
    // Map backend response to frontend format
    const mappedData = {
      id: response.data.id,
      status: response.data.status,
      originalFile: response.data.original_file,
      translatedFile: response.data.translated_file,
      error: response.data.error,
      progress: response.data.progress
    };
    
    try {
      const validatedData = translationTaskSchema.parse(mappedData);
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
  const response = await apiClient.get(`/api/download/${taskId}`, {
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

const translationTextSchema = z.object({
  id: z.number(),
  original_text: z.string(),
  translated_text: z.string()
});

const pageTranslationSchema = z.object({
  page_number: z.number(),
  translations: z.array(translationTextSchema)
});

const translationDataSchema = z.object({
  pages: z.array(pageTranslationSchema)
});

export async function getTranslationData(taskId: string): Promise<TranslationData> {
  try {
    const response = await apiClient.get(`/api/translation/${taskId}/data`);
    // Extract pages data from the response
    const translationData = {
      pages: response.data.pages
    };
    const validatedData = translationDataSchema.parse(translationData);
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

export async function updateTranslationData(taskId: string, data: TranslationData): Promise<void> {
  try {
    // Validate data before sending
    translationDataSchema.parse(data);
    
    const response = await apiClient.put(`/api/translation/${taskId}/data`, data, {
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (response.data?.error) {
      throw new ApiRequestError(
        'Error updating translation data',
        500,
        {
          code: ErrorCode.SERVER_ERROR,
          message: response.data.error
        }
      );
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new ApiRequestError(
        'Datos de traducción inválidos',
        400,
        { 
          code: ErrorCode.VALIDATION_ERROR,
          message: error.message 
        }
      );
    }
    throw error;
  }
}

export async function regeneratePdf(taskId: string): Promise<void> {
  // Note: The regenerate functionality is now part of the PUT /api/translation/{taskId}/data endpoint
  // This function may no longer be needed, but keeping for backward compatibility
  const response = await apiClient.put(`/api/translation/${taskId}/data`, {}, {
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  if (response.data?.error) {
    throw new ApiRequestError(
      'Error regenerating PDF',
      500,
      {
        code: ErrorCode.SERVER_ERROR,
        message: response.data.error
      }
    );
  }
}
