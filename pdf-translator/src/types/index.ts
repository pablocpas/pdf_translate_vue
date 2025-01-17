export interface Language {
  code: string;
  name: string;
  nativeName: string;
}

export interface UploadResponse {
  taskId: string;
}

export interface TranslationProgress {
  current: number;
  total: number;
  percent: number;
}

export interface TranslationTask {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  originalFile: string;
  translatedFile?: string;
  error?: string;
  createdAt?: string;
  updatedAt?: string;
  progress?: TranslationProgress;
}
