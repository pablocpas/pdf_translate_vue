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

// Translation models and configuration types
export type LanguageModelType = 
  | 'openai/gpt-4o-mini' 
  | 'openai/gpt-5-mini' 
  | 'deepseek/deepseek-chat-v3.1' 
  | 'meta-llama/llama-3.3-70b-instruct';

export interface TranslationConfig {
  languageModel: LanguageModelType;
  confidence: number; // 0.1 to 0.9 for DocLayout-YOLO confidence threshold
}
