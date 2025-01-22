<template>
  <div class="form-group">
    <label class="form-label">
      Modelo de IA <span class="required">*</span>
      <span class="tooltip-icon" title="Modelos de IA proporcionados por OpenRouter">?</span>
    </label>
    <div class="model-grid">
      <div
        v-for="(icon, model) in modelIcons"
        :key="model"
        class="model-card"
        :class="{ 
          'model-selected': modelValue === model,
          'has-error': error && !modelValue 
        }"
        @click="handleModelSelect(model)"
      >
        <div class="model-icon-wrapper">
          <img :src="icon" :alt="modelNames[model]" class="model-icon" />
        </div>
        <div class="model-info">
          <span class="model-name">{{ modelNames[model] }}</span>
          <span class="model-description">{{ modelDescriptions[model] }}</span>
        </div>
        <div class="check-icon" v-if="modelValue === model">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTranslationStore } from '@/stores/translationStore';

defineProps<{
  modelValue: string;
  error?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const store = useTranslationStore();
const modelNames = {
  'gpt4o-mini': 'GPT-4o Mini',
  'claude3.5-haiku': 'Claude 3.5 Haiku',
  'gemini-flash': 'Gemini Flash',
  'deepseek-v3': 'DeepSeek v3'
};

const modelDescriptions = {
  'gpt4o-mini': 'Rápido y eficiente para textos cortos',
  'claude3.5-haiku': 'Excelente para documentos técnicos',
  'gemini-flash': 'Ideal para traducciones precisas',
  'deepseek-v3': 'Perfecto para documentos largos'
};

const modelIcons = computed(() => store.modelIcons);

const handleModelSelect = (model: string) => {
  store.setSelectedModel(model);
  emit('update:modelValue', model);
};
</script>

<style scoped>
.form-group {
  margin-bottom: 1.25rem;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.required {
  color: #fa5252;
  margin-left: 4px;
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
  width: 24px;
  height: 24px;
  object-fit: contain;
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
