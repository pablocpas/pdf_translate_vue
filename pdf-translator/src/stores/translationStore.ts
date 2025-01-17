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
  id: z.string().min(1, 'ID es requerido'),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  originalFile: z.string().min(1, 'Archivo original es requerido'),
  translatedFile: z.string().optional(),
  error: z.string().optional(),
  createdAt: z.string().datetime().optional(),
  updatedAt: z.string().datetime().optional(),
  progress: translationProgressSchema.optional()
});

export const useTranslationStore = defineStore('translation', () => {
  // Estado principal
  const currentTask = ref<TranslationTask | null>(loadFromStorage('currentTask'));
  const taskHistory = ref<TranslationTask[]>(loadFromStorage('taskHistory') || []);

  // Funciones de persistencia
  function loadFromStorage(key: string) {
    const stored = localStorage.getItem(`translation_${key}`);
    return stored ? JSON.parse(stored) : null;
  }

  function saveToStorage(key: string, value: any) {
    localStorage.setItem(`translation_${key}`, JSON.stringify(value));
  }

  // Gestión de tareas
  function setCurrentTask(task: TranslationTask) {
    try {
      console.log('Setting current task:', task); // Debug log
      
      const parsedTask = translationTaskSchema.safeParse({
        ...task,
        updatedAt: new Date().toISOString(),
        createdAt: task.createdAt || new Date().toISOString()
      });

      if (!parsedTask.success) {
        console.error('Errores de validación:', parsedTask.error);
        throw new Error('Tarea de traducción inválida');
      }

      // Asegurarse de que el progreso se mantiene si está presente
      if (task.progress) {
        console.log('Task progress:', task.progress); // Debug log
      }

      currentTask.value = parsedTask.data;
      saveToStorage('currentTask', parsedTask.data);
      addToHistory(parsedTask.data);
    } catch (error) {
      console.error('Error setting current task:', error);
      throw error;
    }
  }

  function clearCurrentTask() {
    currentTask.value = null;
    localStorage.removeItem('translation_currentTask');
  }

  function addToHistory(task: TranslationTask) {
    // Evitar duplicados
    const existingIndex = taskHistory.value.findIndex(t => t.id === task.id);
    if (existingIndex !== -1) {
      taskHistory.value[existingIndex] = task;
    } else {
      taskHistory.value.unshift(task);
      // Mantener un tamaño máximo del historial
      if (taskHistory.value.length > MAX_HISTORY_SIZE) {
        taskHistory.value.pop();
      }
    }
    saveToStorage('taskHistory', taskHistory.value);
  }

  function clearHistory() {
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
    // Estado
    currentTask,
    taskHistory,
    
    // Acciones
    setCurrentTask,
    clearCurrentTask,
    clearHistory,
    
    // Computed
    isTaskInProgress,
    hasError,
    isCompleted,
    lastCompletedTask
  };
});
