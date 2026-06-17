<template>
  <div class="typewriter-header" :class="{ 'is-visible': visible }">
    <span class="typewriter-text">
      <span class="shimmer-text">{{ displayedText }}</span>
      <span class="cursor" :class="{ 'cursor-hidden': !cursorVisible }">|</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  text?: string
  speed?: number
  deleteSpeed?: number
  pauseAfter?: number
}>(), {
  text: '研墨文献 · 智能研读',
  speed: 65,
  deleteSpeed: 30,
  pauseAfter: 2500,
})

const displayedText = ref('')
const cursorVisible = ref(true)
const visible = ref(false)
let stepTimer: ReturnType<typeof setTimeout> | undefined
let cursorInterval: ReturnType<typeof setInterval> | undefined
let charIndex = 0
let isDeleting = false

onMounted(() => {
  setTimeout(() => {
    visible.value = true
    scheduleStep()
  }, 400)

  cursorInterval = setInterval(() => {
    cursorVisible.value = !cursorVisible.value
  }, 530)
})

onUnmounted(() => {
  if (stepTimer) clearTimeout(stepTimer)
  if (cursorInterval) clearInterval(cursorInterval)
})

function scheduleStep() {
  if (isDeleting) {
    if (charIndex > 0) {
      stepTimer = setTimeout(() => {
        displayedText.value = props.text.substring(0, charIndex - 1)
        charIndex--
        scheduleStep()
      }, props.deleteSpeed)
    } else {
      isDeleting = false
      scheduleStep()
    }
  } else {
    if (charIndex < props.text.length) {
      stepTimer = setTimeout(() => {
        displayedText.value += props.text[charIndex]
        charIndex++
        scheduleStep()
      }, props.speed)
    } else {
      stepTimer = setTimeout(() => {
        isDeleting = true
        scheduleStep()
      }, props.pauseAfter)
    }
  }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;1,500;1,600&family=Noto+Serif+SC:wght@500;600;700&display=swap');
</style>

<style scoped>
.typewriter-header {
  opacity: 0;
  transition: opacity 0.8s cubic-bezier(0.32, 0.72, 0, 1);
  pointer-events: none;
}

.typewriter-header.is-visible {
  opacity: 1;
}

.typewriter-text {
  font-family: 'Playfair Display', 'Noto Serif SC', 'Georgia', 'Songti SC', serif;
  font-size: 26px;
  font-weight: 600;
  font-style: italic;
  letter-spacing: 3px;
  white-space: nowrap;
  user-select: none;
  transform: translateX(-48px);
}

/* ─── Shimmer — glowing on dark background ───
     Vibrant warm jewel tones that pop against navy/teal.
     No text-stroke needed — dark bg provides natural contrast. */
.shimmer-text {
  background: linear-gradient(
    90deg,
    #fcd34d  0%,
    #60a5fa 22%,
    #2dd4bf 45%,
    #f472b6 65%,
    #fcd34d 85%
  );
  background-size: 280% auto;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shimmer 5s cubic-bezier(0.45, 0, 0.55, 1) infinite;
  filter: drop-shadow(0 0 18px rgba(252, 211, 77, 0.10));
}

@keyframes shimmer {
  0%   { background-position: 0% center; }
  100% { background-position: 280% center; }
}

/* ─── Cursor ─── */
.cursor {
  display: inline-block;
  font-family: 'Playfair Display', serif;
  font-weight: 200;
  font-style: normal;
  color: #fcd34d;
  margin-left: 2px;
  font-size: 24px;
  line-height: 1;
  opacity: 0.8;
  transition: opacity 0.1s;
}

.cursor.cursor-hidden {
  opacity: 0;
}

/* ─── Mobile: hidden, handled by parent ─── */
@media (max-width: 1024px) {
  .typewriter-header {
    display: none;
  }
}
</style>
