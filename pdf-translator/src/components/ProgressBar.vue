<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ title }}</h3>
          <button v-if="closeable" class="close-button" @click="$emit('close')">&times;</button>
        </div>
        
        <div class="progress-section">
          <!-- Upload Progress -->
          <div v-if="uploadProgress !== null" class="progress-container">
            <div class="progress-label">
              <span>Subiendo archivo</span>
              <span>{{ uploadProgress }}%</span>
            </div>
            <div class="progress-bar-container">
              <div class="progress-bar" :style="{ width: `${uploadProgress}%` }"></div>
            </div>
          </div>

          <!-- Translation Progress -->
          <div v-if="translationProgress !== null" class="progress-container">
            <div class="progress-label">
              <span>Traduciendo documento</span>
              <span>{{ translationProgress }}%</span>
            </div>
            <div class="progress-bar-container">
              <div class="progress-bar" :style="{ width: `${translationProgress}%` }"></div>
            </div>
          </div>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  show: boolean;
  title: string;
  uploadProgress: number | null;
  translationProgress: number | null;
  error?: string;
  closeable?: boolean;
}>();

defineEmits<{
  (e: 'close'): void;
}>();
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  animation: slideUp 0.3s ease-out;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #1a1b1e;
  font-weight: 600;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #868e96;
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
  transition: color 0.2s;
}

.close-button:hover {
  color: #495057;
}

.progress-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.progress-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  color: #495057;
  font-weight: 500;
}

.progress-bar-container {
  background: #e9ecef;
  border-radius: 8px;
  height: 8px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(45deg, #228be6, #15aabf);
  transition: width 0.3s ease;
  border-radius: 8px;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #fff5f5;
  border: 1px solid #ffc9c9;
  border-radius: 8px;
  color: #e03131;
  font-size: 0.875rem;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
