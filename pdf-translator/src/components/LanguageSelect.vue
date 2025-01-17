<template>
  <div class="form-group">
    <label class="form-label">
      Idioma destino <span class="required">*</span>
    </label>
    <select
      :value="modelValue"
      class="select-input"
      :class="{ 'has-error': error }"
      @input="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Selecciona un idioma</option>
      <option
        v-for="lang in languages"
        :key="lang.code"
        :value="lang.code"
      >
        {{ lang.nativeName }}
      </option>
    </select>
    <span v-if="error" class="error-text">{{ error }}</span>
  </div>
</template>

<script setup lang="ts">
import type { Language } from '@/types';

const languages: Language[] = [
  { code: 'es', name: 'Spanish', nativeName: 'Español' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
  { code: 'de', name: 'German', nativeName: 'Deutsch' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português' },
];

defineProps<{
  modelValue: string;
  error?: string;
}>();

defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();
</script>

<style scoped>
.form-group {
  margin-bottom: 1.75rem;
}

.form-label {
  display: block;
  margin-bottom: 0.625rem;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.required {
  color: #fa5252;
  margin-left: 4px;
}

.select-input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  background: white;
  transition: all 0.2s ease;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.select-input:hover {
  border-color: #74c0fc;
}

.select-input:focus {
  outline: none;
  border-color: #228be6;
  box-shadow: 0 0 0 3px rgba(34, 139, 230, 0.15);
}

.has-error {
  border-color: #fa5252;
}

.error-text {
  display: block;
  margin-top: 0.5rem;
  color: #fa5252;
  font-size: 0.8125rem;
  font-weight: 500;
  animation: shake 0.5s ease-in-out;
  letter-spacing: -0.01em;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
</style>
