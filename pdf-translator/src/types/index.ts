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

export interface TranslationData {
  pages: Array<{
    text_regions: Array<{
      id: number;
      original_text: string;
      translated_text: string;
      position: {
        x: number;
        y: number;
        width: number;
        height: number;
        coordinates: {
          x1: number;
          y1: number;
          x2: number;
          y2: number;
        };
      };
    }>;
    page_dimensions: {
      width: number;
      height: number;
    };
  }>;
}
