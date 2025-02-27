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
          {{ lang.nativeName }} ({{ lang.name }})
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
  // European Languages
  { code: 'de', name: 'German', nativeName: 'Deutsch' },                   // Alemania
  { code: 'es-ct', name: 'Catalan', nativeName: 'Català' },                // Cataluña
  { code: 'hr', name: 'Croatian', nativeName: 'Hrvatski' },                // Croacia
  { code: 'dk', name: 'Danish', nativeName: 'Dansk' },                     // Dinamarca
  { code: 'sk', name: 'Slovak', nativeName: 'Slovenčina' },                // Eslovaquia
  { code: 'si', name: 'Slovenian', nativeName: 'Slovenščina' },            // Eslovenia
  { code: 'es', name: 'Spanish', nativeName: 'Español' },                  // España
  { code: 'fi', name: 'Finnish', nativeName: 'Suomi' },                    // Finlandia
  { code: 'fr', name: 'French', nativeName: 'Français' },                  // Francia
  { code: 'nl', name: 'Dutch', nativeName: 'Nederlands' },                 // Países Bajos
  { code: 'hu', name: 'Hungarian', nativeName: 'Magyar' },                 // Hungría
  { code: 'gb', name: 'English', nativeName: 'English' },                  // Reino Unido
  { code: 'it', name: 'Italian', nativeName: 'Italiano' },                 // Italia
  { code: 'no', name: 'Norwegian', nativeName: 'Norsk' },                  // Noruega
  { code: 'pl', name: 'Polish', nativeName: 'Polski' },                    // Polonia
  { code: 'pt', name: 'Portuguese', nativeName: 'Português' },             // Portugal
  { code: 'ro', name: 'Romanian', nativeName: 'Română' },                  // Rumania
  { code: 'se', name: 'Swedish', nativeName: 'Svenska' },                  // Suecia
  { code: 'tr', name: 'Turkish', nativeName: 'Türkçe' },                   // Turquía
  { code: 'es-ga', name: 'Galician', nativeName: 'Galego' },               // Galicia
  { code: 'es-pv', name: 'Basque', nativeName: 'Euskara' },                // País Vasco

  // Cyrillic Languages
  { code: 'ru', name: 'Russian', nativeName: 'Русский' },                  // Rusia
  { code: 'ua', name: 'Ukrainian', nativeName: 'Українська' },             // Ucrania
  { code: 'bg', name: 'Bulgarian', nativeName: 'Български' },              // Bulgaria

  // East Asian Languages
  { code: 'cn', name: 'Chinese (Mandarin)', nativeName: '中文' },          // China
  { code: 'jp', name: 'Japanese', nativeName: '日本語' },                  // Japón
  { code: 'kr', name: 'Korean', nativeName: '한국어' },                    // Corea del Sur

  // Other Scripts
  { code: 'arab', name: 'Arabic', nativeName: 'العربية' },                 // Liga Árabe
  { code: 'il', name: 'Hebrew', nativeName: 'עברית' },                     // Israel
  { code: 'gr', name: 'Greek', nativeName: 'Ελληνικά' },                   // Grecia
  { code: 'in', name: 'Hindi', nativeName: 'हिन्दी' },                     // India
  { code: 'bd', name: 'Bengali', nativeName: 'বাংলা' },                    // Bangladesh
  { code: 'lk', name: 'Tamil', nativeName: 'தமிழ்' },                      // Sri Lanka
  { code: 'th', name: 'Thai', nativeName: 'ไทย' },                         // Tailandia
  { code: 'vn', name: 'Vietnamese', nativeName: 'Tiếng Việt' }             // Vietnam
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
