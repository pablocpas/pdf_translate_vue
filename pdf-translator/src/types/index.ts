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
  translationDataFile?: string | null;
}

export type ModelType = 'primalayout' | 'publaynet';

export interface TranslationText {
  id: number;
  original_text: string;
  translated_text: string;
}

export interface PageTranslation {
  page_number: number;
  translations: TranslationText[];
}

export interface TranslationData {
  pages: PageTranslation[];
}
