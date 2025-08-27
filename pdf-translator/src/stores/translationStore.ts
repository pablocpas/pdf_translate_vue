import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { TranslationConfig } from '@/types';
import { translationTaskSchema, type TranslationTask } from '@/types/schemas';

const MAX_HISTORY_SIZE = 10;

export const useTranslationStore = defineStore('translation', () => {
  // Persistence functions
  function loadFromStorage(key: string) {
    const stored = localStorage.getItem(`translation_${key}`);
    return stored ? JSON.parse(stored) : null;
  }

  // Main state
  const currentTask = ref<TranslationTask | null>(loadFromStorage('currentTask'));
  const taskHistory = ref<TranslationTask[]>(loadFromStorage('taskHistory') || []);
  const translationConfig = ref<TranslationConfig>(loadFromStorage('translationConfig') || {
    languageModel: 'openai/gpt-4o-mini',
    confidence: 0.45
  });

  function setTranslationConfig(config: TranslationConfig): void {
    translationConfig.value = config;
    saveToStorage('translationConfig', config);
  }

  function saveToStorage(key: string, value: any): void {
    localStorage.setItem(`translation_${key}`, JSON.stringify(value));
  }

  // Task management
  function setCurrentTask(task: TranslationTask): void {
    try {
      console.log('Setting current task:', task);

      const parsedTask = translationTaskSchema.safeParse(task);

      if (!parsedTask.success) {
        console.error('Validation errors:', parsedTask.error);
        throw new Error('Invalid translation task');
      }

      currentTask.value = parsedTask.data as TranslationTask;
      saveToStorage('currentTask', parsedTask.data);
      addToHistory(parsedTask.data as TranslationTask);
    } catch (error) {
      console.error('Error setting current task:', error);
      throw error;
    }
  }

  function clearCurrentTask(): void {
    currentTask.value = null;
    localStorage.removeItem('translation_currentTask');
  }

  function addToHistory(task: TranslationTask): void {
    const existingIndex = taskHistory.value.findIndex(t => t.id === task.id);
    if (existingIndex !== -1) {
      taskHistory.value[existingIndex] = task;
    } else {
      taskHistory.value.unshift(task);
      if (taskHistory.value.length > MAX_HISTORY_SIZE) {
        taskHistory.value.pop();
      }
    }
    saveToStorage('taskHistory', taskHistory.value);
  }

  function clearHistory(): void {
    taskHistory.value = [];
    localStorage.removeItem('translation_taskHistory');
  }

  // Computed properties
  const isTaskInProgress = computed(() => 
    currentTask.value?.status === 'PENDING' || 
    currentTask.value?.status === 'PROCESSING'
  );

  const hasError = computed(() => 
    currentTask.value?.status === 'FAILED'
  );

  const isCompleted = computed(() => 
    currentTask.value?.status === 'COMPLETED'
  );

  const lastCompletedTask = computed(() => 
    taskHistory.value.find(task => task.status === 'COMPLETED')
  );

  return {
    currentTask,
    taskHistory,
    translationConfig,
    setCurrentTask,
    clearCurrentTask,
    clearHistory,
    isTaskInProgress,
    hasError,
    isCompleted,
    lastCompletedTask,
    setTranslationConfig
  };
});
