import { z } from 'zod';

// Error codes enum for better type safety
export enum ErrorCode {
  // Authentication errors
  UNAUTHORIZED = 'UNAUTHORIZED',
  TOKEN_EXPIRED = 'TOKEN_EXPIRED',
  
  // File errors
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  INVALID_FILE_TYPE = 'INVALID_FILE_TYPE',
  FILE_CORRUPTED = 'FILE_CORRUPTED',
  
  // Translation errors
  TRANSLATION_FAILED = 'TRANSLATION_FAILED',
  LANGUAGE_NOT_SUPPORTED = 'LANGUAGE_NOT_SUPPORTED',
  OCR_FAILED = 'OCR_FAILED',
  
  // Network errors
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT = 'TIMEOUT',
  SERVER_ERROR = 'SERVER_ERROR',
  
  // General errors
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

// User-friendly error messages
export const ErrorMessages: Record<ErrorCode, string> = {
  UNAUTHORIZED: 'Tu sesión ha expirado. Por favor, inicia sesión de nuevo.',
  TOKEN_EXPIRED: 'Tu sesión ha caducado. Por favor, inicia sesión de nuevo.',
  FILE_TOO_LARGE: 'El archivo es demasiado grande. El tamaño máximo permitido es 10MB.',
  INVALID_FILE_TYPE: 'Tipo de archivo no válido. Por favor, sube un archivo PDF.',
  FILE_CORRUPTED: 'El archivo PDF está dañado o no se puede leer.',
  TRANSLATION_FAILED: 'No se pudo traducir el documento. Por favor, inténtalo de nuevo.',
  LANGUAGE_NOT_SUPPORTED: 'El idioma seleccionado no está soportado actualmente.',
  OCR_FAILED: 'No se pudo extraer el texto del PDF. Asegúrate de que el documento contiene texto legible.',
  NETWORK_ERROR: 'Error de conexión. Por favor, verifica tu conexión a internet.',
  TIMEOUT: 'La operación ha tardado demasiado. Por favor, inténtalo de nuevo.',
  SERVER_ERROR: 'Error en el servidor. Por favor, inténtalo más tarde.',
  VALIDATION_ERROR: 'Los datos proporcionados no son válidos.',
  UNKNOWN_ERROR: 'Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo.'
};

export const ApiErrorSchema = z.object({
  message: z.string(),
  code: z.nativeEnum(ErrorCode),
  details: z.unknown().optional()
});

export type ApiError = z.infer<typeof ApiErrorSchema>;

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public error?: ApiError,
    public errorCode: ErrorCode = ErrorCode.UNKNOWN_ERROR
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }

  // Helper method to get user-friendly message
  getUserMessage(): string {
    if (this.error?.code) {
      return ErrorMessages[this.error.code];
    }
    return ErrorMessages[this.errorCode];
  }
}

export class NetworkError extends Error {
  constructor(message: string = ErrorMessages[ErrorCode.NETWORK_ERROR]) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class AuthenticationError extends Error {
  constructor(message: string = ErrorMessages[ErrorCode.UNAUTHORIZED]) {
    super(message);
    this.name = 'AuthenticationError';
  }
}
