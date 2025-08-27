<template>
  <div class="configuration-panel">
    <div class="header-row">
      <label class="form-label">
        Configuración de Traducción
        <span class="tooltip-icon" title="Ajustes avanzados para optimizar la traducción según tus necesidades">?</span>
      </label>
      <button type="button" class="advanced-toggle" @click="showAdvanced = !showAdvanced">
        {{ showAdvanced ? 'Ocultar opciones avanzadas' : 'Mostrar opciones avanzadas' }}
      </button>
    </div>

    <!-- Language Model Selection -->
    <div class="config-section">
      <label class="section-label">Modelo de Lenguaje</label>
      <div class="model-grid">
        <div
          v-for="model in languageModels"
          :key="model.id"
          class="model-card"
          :class="{ 
            'model-selected': config.languageModel === model.id,
            'has-error': errors.languageModel 
          }"
          @click="handleLanguageModelSelect(model.id)"
        >
          <div class="model-icon-wrapper">
            <span class="model-icon">{{ model.icon }}</span>
          </div>
          <div class="model-info">
            <span class="model-name">
              {{ model.name }}
              <span v-if="model.id === 'openai/gpt-4o-mini'" class="recommended-badge">Recomendado</span>
            </span>
            <span class="model-description">{{ model.description }}</span>
          </div>
          <div class="check-icon" v-if="config.languageModel === model.id">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Advanced Options -->
    <div v-if="showAdvanced" class="advanced-options">
      <!-- Confidence Slider -->
      <div class="config-section">
        <label class="section-label">
          Confianza de Segmentación 
          <span class="confidence-value">{{ Math.round(config.confidence * 100) }}%</span>
        </label>
        <div class="slider-container">
          <input
            type="range"
            v-model.number="config.confidence"
            min="0.1"
            max="0.9"
            step="0.05"
            class="confidence-slider"
          />
          <div class="slider-labels">
            <span>Más elementos</span>
            <span>Más preciso</span>
          </div>
        </div>
        <p class="slider-description">
          Ajusta qué tan estricto debe ser el modelo al detectar elementos en el documento
        </p>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import type { LanguageModelType, TranslationConfig } from '@/types';

interface LanguageModel {
  id: LanguageModelType;
  name: string;
  description: string;
  icon: string;
}

interface ConfigErrors {
  languageModel?: string;
}

const props = withDefaults(defineProps<{
  modelValue: TranslationConfig;
  errors?: ConfigErrors;
}>(), {
  errors: () => ({})
});

const emit = defineEmits<{
  'update:modelValue': [value: TranslationConfig];
}>();

const showAdvanced = ref(false);

const config = reactive<TranslationConfig>({
  languageModel: props.modelValue.languageModel,
  confidence: props.modelValue.confidence
});

// Watch for changes in config and emit updates
watch(config, (newConfig) => {
  emit('update:modelValue', { ...newConfig });
}, { deep: true });

const languageModels: LanguageModel[] = [
  {
    id: 'openai/gpt-4o-mini',
    name: 'GPT-4o Mini',
    description: 'Equilibrio perfecto entre calidad y costo',
    icon: '⚡'
  },
  {
    id: 'openai/gpt-5-mini',
    name: 'GPT-5 Mini',
    description: 'Último modelo de OpenAI más eficiente',
    icon: '🚀'
  },
  {
    id: 'deepseek/deepseek-chat-v3.1',
    name: 'DeepSeek v3.1',
    description: 'Excelente para idiomas asiáticos',
    icon: '🧠'
  },
  {
    id: 'meta-llama/llama-3.3-70b-instruct',
    name: 'Llama 3.3 70B',
    description: 'Modelo open source de alta calidad',
    icon: '🦙'
  }
];

const handleLanguageModelSelect = (modelId: LanguageModelType) => {
  config.languageModel = modelId;
};
</script>

<style scoped>
.configuration-panel {
  margin-bottom: 1.25rem;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
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

.config-section {
  margin-bottom: 1.5rem;
}

.section-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
  color: #1a1b1e;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.confidence-value {
  color: #228be6;
  font-weight: 600;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
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
  gap: 0.75rem;
}

.model-card:hover {
  border-color: #74c0fc;
  background: #f8f9fa;
  transform: translateY(-1px);
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
  font-size: 20px;
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

.advanced-options {
  animation: slideDown 0.3s ease;
}

.slider-container {
  margin-bottom: 0.5rem;
}

.confidence-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e9ecef;
  outline: none;
  -webkit-appearance: none;
}

.confidence-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #228be6;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.confidence-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #228be6;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #868e96;
  margin-top: 0.25rem;
}

.slider-description {
  color: #868e96;
  font-size: 0.75rem;
  margin: 0;
  line-height: 1.4;
}

.mode-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.mode-option {
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.mode-option:hover {
  border-color: #74c0fc;
  background: #f8f9fa;
}

.mode-selected {
  border-color: #228be6;
  background: rgba(34, 139, 230, 0.05);
}

.mode-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.mode-info {
  flex: 1;
}

.mode-name {
  display: block;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.mode-description {
  display: block;
  color: #868e96;
  font-size: 0.75rem;
  line-height: 1.3;
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

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}

@media (max-width: 768px) {
  .model-grid {
    grid-template-columns: 1fr;
  }
  
  .mode-options {
    grid-template-columns: 1fr;
  }
  
  .model-card,
  .mode-option {
    padding: 0.875rem;
  }
}
</style>