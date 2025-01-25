<template>
  <div class="form-group">
    <div class="header-row">
      <label class="form-label">
        Modelo de Segmentación
        <span class="tooltip-icon" title="Modelos de segmentación para diferentes tipos de documentos">?</span>
      </label>
      <button type="button" class="advanced-toggle" @click="showAdvanced = !showAdvanced">
        {{ showAdvanced ? 'Ocultar opciones avanzadas' : 'Mostrar opciones avanzadas' }}
      </button>
    </div>
    <div v-if="showAdvanced" class="model-grid">
      <div
        v-for="model in models"
        :key="model.id"
        class="model-card"
        :class="{ 
          'model-selected': modelValue === model.id,
          'has-error': error && !modelValue 
        }"
        @click="handleModelSelect(model.id)"
      >
        <div class="model-icon-wrapper">
          <span class="model-icon">{{ model.icon }}</span>
        </div>
        <div class="model-info">
          <span class="model-name">
            {{ model.name }}
            <span v-if="model.id === 'primalayout'" class="recommended-badge">Recomendado</span>
          </span>
          <span class="model-description">{{ model.description }}</span>
        </div>
        <div class="check-icon" v-if="modelValue === model.id">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
      </div>
    </div>
    <div v-else class="selected-model">
      <div class="model-card model-selected">
        <div class="model-icon-wrapper">
          <span class="model-icon">{{ modelIcons[modelValue] }}</span>
        </div>
        <div class="model-info">
          <span class="model-name">
            {{ modelNames[modelValue] }}
            <span v-if="modelValue === 'primalayout'" class="recommended-badge">Recomendado</span>
          </span>
          <span class="model-description">{{ modelDescriptions[modelValue] }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useTranslationStore } from '@/stores/translationStore';
import { ModelType } from '@/types';

interface Model {
  id: ModelType;
  name: string;
  description: string;
  icon: string;
}

const props = withDefaults(defineProps<{
  modelValue: ModelType;
  error?: string;
}>(), {
  error: undefined
});

const emit = defineEmits<{
  'update:modelValue': [value: ModelType];
}>();

const showAdvanced = ref(false);
const store = useTranslationStore();

const modelNames: Record<ModelType, string> = {
  'primalayout': 'PrimaLayout',
  'publaynet': 'PubLayNet'
} as const;

const modelDescriptions: Record<ModelType, string> = {
  'primalayout': 'Optimizado para documentos generales',
  'publaynet': 'Especializado en papers y documentos académicos'
} as const;

const modelIcons: Record<ModelType, string> = {
  'primalayout': '📃',
  'publaynet': '🎓'
} as const;

const models = computed<Model[]>(() => {
  return Object.entries(modelIcons).map(([id, icon]) => ({
    id: id as ModelType,
    name: modelNames[id as keyof typeof modelNames],
    description: modelDescriptions[id as keyof typeof modelDescriptions],
    icon
  }));
});

const handleModelSelect = (model: ModelType) => {
  store.setSelectedModel(model);
  emit('update:modelValue', model);
};
</script>

<style scoped>
.form-group {
  margin-bottom: 1.25rem;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.form-label {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.advanced-toggle {
  background: none;
  border: none;
  color: #228be6;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.advanced-toggle:hover {
  background: rgba(34, 139, 230, 0.1);
}

.tooltip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #e9ecef;
  color: #495057;
  font-size: 11px;
  margin-left: 6px;
  cursor: help;
  transition: all 0.2s ease;
}

.tooltip-icon:hover {
  background: #dee2e6;
  color: #228be6;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.selected-model {
  animation: fadeIn 0.3s ease;
}

.model-card {
  position: relative;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.model-card:hover {
  border-color: #74c0fc;
  background: #f8f9fa;
  transform: translateY(-2px);
}

.model-selected {
  border-color: #228be6;
  background: rgba(34, 139, 230, 0.05);
}

.model-selected:hover {
  border-color: #228be6;
  background: rgba(34, 139, 230, 0.08);
}

.model-icon-wrapper {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.model-icon {
  font-size: 24px;
  line-height: 1;
}

.model-info {
  flex: 1;
  min-width: 0;
}

.model-name {
  display: block;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.recommended-badge {
  display: inline-block;
  background: #37b24d;
  color: white;
  font-size: 0.6875rem;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  margin-left: 0.5rem;
  font-weight: 500;
  vertical-align: middle;
}

.model-description {
  display: block;
  color: #868e96;
  font-size: 0.75rem;
  line-height: 1.3;
}

.check-icon {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  color: #228be6;
  animation: scaleIn 0.2s ease;
}

@keyframes scaleIn {
  from {
    transform: scale(0);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@media (max-width: 640px) {
  .model-grid {
    grid-template-columns: 1fr;
  }
  
  .model-card {
    padding: 1rem;
  }
  
  .model-name {
    font-size: 0.875rem;
  }
  
  .model-description {
    font-size: 0.75rem;
  }
}
</style>
