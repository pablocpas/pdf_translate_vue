export interface Language {
  code: string;
  name: string;
  nativeName: string;
}

// Re-exportar tipos de esquemas
export type { 
  UploadResponse, 
  TranslationTask, 
  TranslationProgress,
  TranslationText, 
  PageTranslation, 
  TranslationData 
} from './schemas';

// Modelos de traducción y configuración
export type LanguageModelType = 
  | 'openai/gpt-4o-mini' 
  | 'openai/gpt-5-mini' 
  | 'deepseek/deepseek-chat-v3.1' 
  | 'meta-llama/llama-3.3-70b-instruct';

export interface TranslationConfig {
  languageModel: LanguageModelType;
  confidence: number;  // Umbral de confianza 0.1-0.9
}
