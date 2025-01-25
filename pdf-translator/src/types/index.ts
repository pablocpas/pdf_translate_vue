export interface Language {
  code: string;
  name: string;
  nativeName: string;
}

export interface UploadResponse {
  taskId: string;
}

export interface TranslationTask {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: {
    current: number;
    total: number;
    percent: number;
  } | null;
  error: string | null;
  originalFile: string;
  translatedFile: string | null;
}

export type ModelType = 'primalayout' | 'publaynet';
