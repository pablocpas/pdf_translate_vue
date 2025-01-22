<template>
  <div class="form-group">
    <label class="form-label">
      Idioma destino <span class="required">*</span>
    </label>
    <div class="select-wrapper" :class="{ 'has-error': error && !modelValue }">
      <select 
        :value="modelValue"
        @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
        class="language-select"
      >
        <option value="" disabled selected>Selecciona un idioma</option>
        <option 
          v-for="lang in languages" 
          :key="lang.code" 
          :value="lang.code"
          class="language-option"
        >
          {{ getFlagEmoji(lang.code) }} {{ lang.nativeName }} ({{ lang.name }})
        </option>
      </select>
      <div class="select-arrow">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </div>
    </div>
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

const getFlagEmoji = (countryCode: string) => {
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
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

.select-wrapper {
  position: relative;
  width: 100%;
}

.language-select {
  width: 100%;
  padding: 0.875rem 1rem;
  font-size: 0.9375rem;
  line-height: 1.5;
  color: #1a1b1e;
  background: linear-gradient(to bottom, #ffffff, #f8f9fa);
  border: 2px solid #e9ecef;
  border-radius: 14px;
  appearance: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.language-select:hover {
  border-color: #74c0fc;
  background: linear-gradient(to bottom, #ffffff, #f1f3f5);
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
}

.language-select:focus {
  outline: none;
  border-color: #228be6;
  background: white;
  box-shadow: 0 0 0 3px rgba(34, 139, 230, 0.15);
  transform: translateY(-1px);
}

.select-arrow {
  position: absolute;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #228be6;
  pointer-events: none;
  transition: transform 0.2s ease;
}

.language-select:focus + .select-arrow {
  transform: translateY(-50%) rotate(180deg);
}

.has-error .language-select {
  border-color: #fa5252;
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}

.error-text {
  display: block;
  margin-top: 0.75rem;
  color: #fa5252;
  font-size: 0.8125rem;
  font-weight: 500;
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}

/* Estilos para las opciones del select */
.language-select option {
  padding: 12px;
  font-size: 0.9375rem;
  background-color: white;
  color: #1a1b1e;
}

.language-select option:checked {
  background: linear-gradient(to right, #228be6, #15aabf);
  color: white;
}

/* Estilos para el placeholder */
.language-select option[value=""] {
  color: #868e96;
  font-style: italic;
}

@keyframes shake {
  10%, 90% { transform: translateX(-1px); }
  20%, 80% { transform: translateX(2px); }
  30%, 50%, 70% { transform: translateX(-3px); }
  40%, 60% { transform: translateX(3px); }
}

/* Estilos específicos para Firefox */
@-moz-document url-prefix() {
  .language-select {
    text-indent: 0.01px;
    text-overflow: '';
    padding-right: 2.5rem;
  }
}

/* Estilos específicos para Safari */
@media not all and (min-resolution:.001dpcm) {
  @supports (-webkit-appearance:none) {
    .language-select {
      padding-right: 2.5rem;
    }
  }
}
</style>
