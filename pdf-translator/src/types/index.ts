export interface Language {
  code: string;
  name: string;
  nativeName: string;
}

// Re-export types from schemas to maintain backward compatibility
export type { 
  UploadResponse, 
  TranslationTask, 
  TranslationProgress,
  TranslationText, 
  PageTranslation, 
  TranslationData 
} from './schemas';

export type ModelType = 'primalayout' | 'publaynet';
