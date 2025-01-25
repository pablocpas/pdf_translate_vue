<template>
  <div class="progress-circle">
    <svg class="progress" viewBox="0 0 100 100">
      <defs>
        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#228be6" />
          <stop offset="100%" stop-color="#15aabf" />
        </linearGradient>
      </defs>
      <circle class="progress-background" cx="50" cy="50" r="45"></circle>
      <circle 
        class="progress-bar" 
        cx="50" 
        cy="50" 
        r="45"
        :style="{
          strokeDashoffset: `${((100 - progress) / 100) * 283}px`
        }"
      ></circle>
    </svg>
    <span class="progress-text">{{ Math.round(progress) }}%</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  progress: number;
}>();
</script>

<style scoped>
.progress-circle {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 1.5rem;
}

.progress {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}

.progress-background {
  fill: none;
  stroke: #e9ecef;
  stroke-width: 8;
}

.progress-bar {
  fill: none;
  stroke: url(#gradient);
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 0.3s ease;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 1.5rem;
  font-weight: 700;
  color: #228be6;
}
</style>
