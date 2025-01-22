import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { TranslationTask } from '@/types';
import { z } from 'zod';

const MAX_HISTORY_SIZE = 10;

const translationProgressSchema = z.object({
  current: z.number(),
  total: z.number(),
  percent: z.number()
});

const translationTaskSchema = z.object({
  id: z.string().min(1, 'ID is required'),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  originalFile: z.string(),
  translatedFile: z.string().optional().nullable(),
  error: z.string().optional().nullable(),
  progress: translationProgressSchema.optional().nullable()
});

export const useTranslationStore = defineStore('translation', () => {

  // Persistence functions
  function loadFromStorage(key: string) {
    const stored = localStorage.getItem(`translation_${key}`);
    return stored ? JSON.parse(stored) : null;
  }

  // Main state
  const currentTask = ref<TranslationTask | null>(loadFromStorage('currentTask'));
  const taskHistory = ref<TranslationTask[]>(loadFromStorage('taskHistory') || []);
  const selectedModel = ref<string>(loadFromStorage('selectedModel') || 'claude3.5-haiku');

  function setSelectedModel(model: string): void {
    selectedModel.value = model;
    saveToStorage('selectedModel', model);
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
    currentTask.value?.status === 'pending' || 
    currentTask.value?.status === 'processing'
  );

  const hasError = computed(() => 
    currentTask.value?.status === 'failed'
  );

  const isCompleted = computed(() => 
    currentTask.value?.status === 'completed'
  );

  const lastCompletedTask = computed(() => 
    taskHistory.value.find(task => task.status === 'completed')
  );

  const modelIcons = computed(() => ({
    'gpt4o-mini': 'https://openrouter.ai/images/icons/OpenAI.svg',
    'claude3.5-haiku': 'https://openrouter.ai/images/icons/Anthropic.svg',
    'gemini-flash': 'https://openrouter.ai/images/icons/GoogleGemini.svg',
    'deepseek-v3': 'https://openrouter.ai/images/icons/DeepSeek.png'
  }));

  return {
    currentTask,
    taskHistory,
    selectedModel,
    modelIcons,
    setCurrentTask,
    clearCurrentTask,
    clearHistory,
    isTaskInProgress,
    hasError,
    isCompleted,
    lastCompletedTask,
    setSelectedModel
  };
});
