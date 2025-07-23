import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { ModelType } from '@/types';
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
  const selectedModel = ref<ModelType>(loadFromStorage('selectedModel') || 'primalayout');

  function setSelectedModel(model: ModelType): void {
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

  return {
    currentTask,
    taskHistory,
    selectedModel,
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
