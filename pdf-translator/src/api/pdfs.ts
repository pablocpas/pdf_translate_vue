import { z } from 'zod';
import apiClient from './client';
import { ApiRequestError, ErrorCode } from '@/types/api';
import { 
  uploadResponseSchema, 
  translationTaskSchema, 
  translationDataSchema,
  type UploadResponse, 
  type TranslationTask, 
  type TranslationData 
} from '@/types/schemas';

export async function uploadPdf(formData: FormData): Promise<UploadResponse> {
  try {
    const response = await apiClient.post<UploadResponse>('/pdfs/translate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    const validatedData = uploadResponseSchema.parse(response.data);
    return validatedData;
  } catch (error: unknown) {
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
    } catch (validationError: unknown) {
      if (validationError instanceof z.ZodError) {
        console.error('Validation error details:', validationError.errors);
      }
      throw validationError;
    }
  } catch (error: unknown) {
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


export async function getTranslationData(taskId: string): Promise<TranslationData> {
  try {
    const response = await apiClient.get(`/pdfs/translation-data/${taskId}`);
    // Extraer datos de páginas
    const translationData = {
      pages: response.data.pages
    };
    const validatedData = translationDataSchema.parse(translationData);
    return validatedData;
  } catch (error: unknown) {
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
    // Validar datos antes de enviar
    translationDataSchema.parse(data);
    
    const response = await apiClient.put(`/pdfs/translation-data/${taskId}`, data, {
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
  } catch (error: unknown) {
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
  const response = await apiClient.post(`/pdfs/regenerate/${taskId}`);
  
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
