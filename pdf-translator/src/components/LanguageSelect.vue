<template>
  <div class="form-group">
    <label class="form-label">
      Idioma destino <span class="required">*</span>
    </label>
    <div class="language-grid">
      <div
        v-for="lang in languages"
        :key="lang.code"
        class="language-card"
        :class="{ 
          'language-selected': modelValue === lang.code,
          'has-error': error && !modelValue 
        }"
        @click="$emit('update:modelValue', lang.code)"
      >
        <div class="language-icon">{{ getFlagEmoji(lang.code) }}</div>
        <div class="language-info">
          <span class="language-name">{{ lang.nativeName }}</span>
          <span class="language-code">{{ lang.name }}</span>
        </div>
        <div class="check-icon" v-if="modelValue === lang.code">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
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

.language-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.language-card {
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

.language-card:hover {
  border-color: #74c0fc;
  background: #f8f9fa;
  transform: translateY(-2px);
}

.language-selected {
  border-color: #228be6;
  background: rgba(34, 139, 230, 0.05);
}

.language-selected:hover {
  border-color: #228be6;
  background: rgba(34, 139, 230, 0.08);
}

.has-error {
  border-color: #fa5252;
  animation: shake 0.5s ease-in-out;
}

.language-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.language-info {
  flex: 1;
  min-width: 0;
}

.language-name {
  display: block;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.language-code {
  display: block;
  color: #868e96;
  font-size: 0.8125rem;
}

.check-icon {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  color: #228be6;
  animation: scaleIn 0.2s ease;
}

.error-text {
  display: block;
  margin-top: 0.75rem;
  color: #fa5252;
  font-size: 0.8125rem;
  font-weight: 500;
  animation: shake 0.5s ease-in-out;
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

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

@media (max-width: 768px) {
  .language-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .language-grid {
    grid-template-columns: 1fr;
  }
  
  .language-card {
    padding: 1rem;
  }
  
  .language-name {
    font-size: 0.875rem;
  }
  
  .language-code {
    font-size: 0.75rem;
  }
}
</style>
